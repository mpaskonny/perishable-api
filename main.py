from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SimulationParams, SimulationResponse, DailyResult
from core.demand import UniformDemand, NormalDemand, FixedDemand, RealDemand, RealDemandWithInterpolation
from core.customer import FixedCustomerStrategy, NormalCustomerStrategy, NormalCustomerStrategyFromExcel
from core.delivery import PeriodicDelivery, DaysOfWeekDelivery
from core.spoilage import StrictExpirySpoilage
from core.simple_spoilage import LinearSpoilage, PowerSpoilage, LogisticSpoilage
from core.product import Product
from database.db_manager import DatabaseManager
from datetime import datetime
from core.sigma_loader import get_sigma_loader
from core.fifo_sigma_loader import get_fifo_sigma_loader
from core.data_loader import DemandDataLoader


# ========== КОНСТАНТЫ ==========
# Молоко - параметры спроса
MILK_UNIFORM_MIN = 20
MILK_UNIFORM_MAX = 30
MILK_NORMAL_MEAN = 25
MILK_NORMAL_SIGMA = 1.41

# Помидоры - параметры спроса
TOMATOES_UNIFORM_MIN = 150
TOMATOES_UNIFORM_MAX = 200
TOMATOES_NORMAL_MEAN = 175
TOMATOES_NORMAL_SIGMA = 14.91

# Параметры экспоненциальной порчи по умолчанию
DEFAULT_POWER_P = 2.0
DEFAULT_LOGISTIC_K = 15.0

# Коэффициенты дней недели по умолчанию
DEFAULT_WEEKDAY_FACTORS = [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]

# Параметры утилизации
DEFAULT_UTILIZATION_PRICE = 5.0


# ========== ПРИЛОЖЕНИЕ ==========
app = FastAPI(
    title="Симулятор продуктов с ограниченным сроком годности",
    description="Универсальный API для симуляции управления запасами",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_product(params: SimulationParams) -> Product:
    """
    Фабрика для создания продукта с нужными стратегиями
    """
    # Получаем базовые параметры продукта из БД
    db = DatabaseManager()
    product_data = db.get_product_by_name(params.product_name)
    
    if not product_data:
        raise HTTPException(status_code=404, detail=f"Продукт '{params.product_name}' не найден в БД")
    
    category_id = product_data.get('id_category')
    base_demand = product_data.get('base_demand', 100)
    
    # ========== 1. СТРАТЕГИЯ СПРОСА ==========
    if params.use_real_demand and params.real_demand_dates and params.real_demand_values:
        # Реальный спрос с реальными датами из Excel
        try:
            demand_data = {}
            for date_str, demand in zip(params.real_demand_dates, params.real_demand_values):
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                demand_data[date] = demand
            
            demand_strategy = RealDemandWithInterpolation(demand_data, base_demand)
            customer_strategy = FixedCustomerStrategy()
            
            # Обновляем start_date на реальную дату начала из файла
            if params.real_start_date:
                params.start_date = datetime.fromisoformat(params.real_start_date)
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ошибка обработки данных: {str(e)}")

    elif params.fixed_demand:
        demand_strategy = FixedDemand(params.fixed_demand)
        customer_strategy = FixedCustomerStrategy()
        
    elif params.distribution == "uniform":
        # Равномерный спрос: если границы заданы пользователем — используем их
        if params.demand_min is not None and params.demand_max is not None:
            demand_min = params.demand_min
            demand_max = params.demand_max
        else:
            # Иначе автоматически от 0.5x до 1.5x
            demand_min = base_demand * 0.5
            demand_max = base_demand * 1.5
        
        demand_strategy = UniformDemand(demand_min, demand_max)
        customer_strategy = FixedCustomerStrategy()
        
    else:  # normal
        # Нормальный спрос: средний = базовый, сигма из Excel
        sigma_loader = get_sigma_loader()
        empirical_sigma = sigma_loader.get_sigma(base_demand)
        
        demand_strategy = NormalDemand(base_demand, empirical_sigma)
        
        if category_id == 1:  # strict (молоко)
            fifo_loader = get_fifo_sigma_loader()
            sigma_fifo, sigma_lifo = fifo_loader.get_sigmas(int(params.fifo_percent or 75))
            customer_strategy = NormalCustomerStrategyFromExcel(sigma_fifo, sigma_lifo)
        else:
            customer_strategy = FixedCustomerStrategy()
    
    # ========== 2. СТРАТЕГИЯ ПОСТАВОК ==========
    
    # Обработка параметров доставки
    if params.delivery_cost_type == "none":
        cost_type = "fixed"
        fixed_cost = 0.0
        rate_cost = 0.0
    else:
        cost_type = params.delivery_cost_type
        fixed_cost = params.delivery_fixed_cost
        rate_cost = params.delivery_rate_cost

    # ===== ВЫБОР СПОСОБА ПОСТАВКИ И СТРАТЕГИИ =====
    # Определяем расписание (периодичность или дни недели)
    if params.schedule_type == "frequency":
        delivery_frequency = params.delivery_frequency or 2
        delivery_days = []
    else:
        delivery_frequency = 0
        delivery_days = params.delivery_days or [0, 3]

    # Выбираем стратегию в зависимости от способа поставки
    if params.delivery_type == "fixed":
        # Фиксированный объём поставки (R, Q)
        from core.delivery import FixedQuantityDelivery
        delivery_strategy = FixedQuantityDelivery(
            frequency=delivery_frequency,
            fixed_quantity=params.fixed_quantity,
            cost_type=cost_type,
            fixed_cost=fixed_cost,
            rate_cost=rate_cost,
            delivery_days=delivery_days if delivery_days else None
        )
    elif params.schedule_type == "ss_policy":
        # (s, S)-стратегия
        from core.delivery import SSPolicyDelivery
        delivery_strategy = SSPolicyDelivery(
            reorder_point=params.reorder_point,
            max_stock=params.max_stock,
            cost_type=cost_type,
            fixed_cost=fixed_cost,
            rate_cost=rate_cost,
            delivery_type=params.delivery_type or "unit",
            box_size=params.box_size or 0
        )
    else:
        # Периодические поставки (до целевого уровня)
        if category_id == 1:  # strict (молоко)
            freq = params.milk_delivery_frequency or delivery_frequency or 2
            delivery_strategy = PeriodicDelivery(
                freq,
                cost_type=cost_type,
                fixed_cost=fixed_cost,
                rate_cost=rate_cost
            )
        else:
            freq = params.tomatoes_delivery_frequency or delivery_frequency or 2
            delivery_strategy = PeriodicDelivery(
                freq,
                cost_type=cost_type,
                fixed_cost=fixed_cost,
                rate_cost=rate_cost
            )
    
    # ========== 3. СТРАТЕГИЯ ПОРЧИ ==========
    if category_id == 1:  # strict (молоко)
        spoilage_strategy = StrictExpirySpoilage()
        is_strict = True
        utilization_price = params.utilization_price or DEFAULT_UTILIZATION_PRICE
    else:  # gradual
        is_strict = False
        utilization_price = 0.0
        
        if params.spoilage_type == "linear":
            spoilage_strategy = LinearSpoilage(params.shelf_life_days)
        elif params.spoilage_type == "power":
            p = params.power_p if params.power_p else DEFAULT_POWER_P
            spoilage_strategy = PowerSpoilage(params.shelf_life_days, p)
        else:  # logistic
            k = params.logistic_k if params.logistic_k else DEFAULT_LOGISTIC_K
            spoilage_strategy = LogisticSpoilage(params.shelf_life_days, k)
    
    # ========== 4. КОЭФФИЦИЕНТЫ ДНЕЙ НЕДЕЛИ ==========
    weekday_factors = params.weekday_factors if params.weekday_factors else DEFAULT_WEEKDAY_FACTORS
    
    # ========== 5. СОЗДАНИЕ ПРОДУКТА ==========
    product = Product(
        name=product_data['name'],
        purchase_price=params.purchase_price or product_data['purchase_price'],
        sale_price=params.sale_price or product_data['sale_price'],
        min_stock=params.min_stock,
        demand_strategy=demand_strategy,
        spoilage_strategy=spoilage_strategy,
        customer_strategy=customer_strategy,
        delivery_strategy=delivery_strategy,
        shelf_life_days=params.shelf_life_days or product_data.get('shelf_life_days', 30),
        is_strict=is_strict,
        weekday_factors=weekday_factors,
        utilization_price=utilization_price,
        delivery_type=params.delivery_type or "unit",
        box_size=params.box_size or 0
    )
    
    return product


@app.get("/")
async def root():
    return {
        "message": "API симулятора управления запасами",
        "version": "3.0.0",
        "endpoints": ["/simulate", "/docs"],
        "features": [
            "Строгая порча (молоко) - мгновенное списание после expiry_date",
            "Линейная порча - равномерное старение",
            "Степенная порча - ускорение к концу срока",
            "Логистическая порча - S-образная"
        ]
    }


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(params: SimulationParams):
    """
    Универсальная симуляция управления запасами
    """
    try:
        product = create_product(params)
        
        results = product.run(
            days=params.days, 
            start_date=params.start_date, 
            fifo_percent=params.fifo_percent or 100.0,
            lifo_percent=params.lifo_percent or 0.0
        )
        
        daily_results = []
        for h in results['daily_history']:
            if params.product_type == "milk":
                daily_results.append(DailyResult(
                    day=h['day'],
                    date=h['date'],
                    demand=float(h['demand']),
                    start_stock=float(h['start_stock']),
                    sales=float(h['sales']),
                    spoilage=float(h['spoilage_kg']),
                    order=float(h['order']),
                    revenue=float(h['revenue']),
                    purchase_cost=float(h['purchase_cost']),
                    end_stock=float(h.get('end_stock', 0)),
                    fifo_percent=float(h.get('fifo_percent', 0)) if h.get('fifo_percent') else None,
                    lifo_percent=float(h.get('lifo_percent', 0)) if h.get('lifo_percent') else None,
                    utilization_cost=float(h.get('utilization_cost', 0)) if h.get('utilization_cost') else None,
                    batch_1_stock=float(h.get('batch_1_stock', 0)) if h.get('batch_1_stock') else None,
                    batch_2_stock=float(h.get('batch_2_stock', 0)) if h.get('batch_2_stock') else None,
                    batch_3_stock=float(h.get('batch_3_stock', 0)) if h.get('batch_3_stock') else None,
                    batch_4_stock=float(h.get('batch_4_stock', 0)) if h.get('batch_4_stock') else None,
                    batch_5_stock=float(h.get('batch_5_stock', 0)) if h.get('batch_5_stock') else None,
                    unmet_demand=float(h.get('unmet_demand', 0))
                ))
            else:
                daily_results.append(DailyResult(
                    day=h['day'],
                    date=h['date'],
                    demand=float(h['demand']),
                    start_stock=float(h['start_stock']),
                    sales=float(h['sales']),
                    spoilage=float(round(h['spoilage_kg'], 2)),
                    order=float(round(h['order'], 2)),
                    revenue=float(h['revenue']),
                    purchase_cost=float(h['purchase_cost']),
                    end_stock=float(h.get('end_stock', 0)),
                    unmet_demand=float(h.get('unmet_demand', 0)),
                    stock_week1=float(h.get('stock_week1', 0)),
                    stock_week2=float(h.get('stock_week2', 0)),
                    stock_week3=float(h.get('stock_week3', 0))
                ))
        
        return SimulationResponse(
            total_revenue=results['total_revenue'],
            total_cost=results['total_cost'],
            total_purchase_cost=results.get('total_purchase_cost', 0),      
            total_delivery_cost=results.get('total_delivery_cost', 0),      
            total_utilization_cost=results.get('total_utilization_cost', 0), 
            total_spoilage_kg=results['total_spoilage_kg'],
            total_spoilage_money=results['total_spoilage_money'],
            profit=results['profit'],
            avg_stock=results['avg_stock'],
            daily_history=daily_results,
            demand_stats=results['demand_stats'],
            spoilage_stats=results.get('spoilage_stats', {})
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
