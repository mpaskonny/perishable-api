from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SimulationParams, SimulationResponse, DailyResult
from core.demand import UniformDemand, NormalDemand, FixedDemand
from core.customer import FixedCustomerStrategy, NormalCustomerStrategy
from core.delivery import PeriodicDelivery, DaysOfWeekDelivery
from core.spoilage import StrictExpirySpoilage
from core.simple_spoilage import LinearSpoilage, ExponentialSpoilage, LogisticSpoilage
from core.product import Product
from database.db_manager import DatabaseManager
from datetime import datetime
from core.sigma_loader import get_sigma_loader


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

# Молоко - параметры покупателей
MILK_CUSTOMER_SIGMA = 1.51

# Параметры экспоненциальной порчи по умолчанию
DEFAULT_EXPONENTIAL_K = 15.0

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
    
    # ========== 1. СТРАТЕГИЯ СПРОСА (из настроек симуляции) ==========
    if params.fixed_demand:
        demand_strategy = FixedDemand(params.fixed_demand)
        customer_strategy = FixedCustomerStrategy()
    elif params.distribution == "uniform":
        # Равномерный спрос: от 0.5x до 1.5x от базового
        demand_strategy = UniformDemand(base_demand * 0.5, base_demand * 1.5)
        customer_strategy = FixedCustomerStrategy()
    else:  # normal
        # Нормальный спрос: средний = базовый, sigma = 15% от среднего
        sigma_loader = get_sigma_loader()
        empirical_sigma = sigma_loader.get_sigma(base_demand)

        demand_strategy = NormalDemand(base_demand, empirical_sigma)
        if category_id == 1:  # strict (молоко)
            sigma_buyer = params.sigma_buyer if params.sigma_buyer is not None else MILK_CUSTOMER_SIGMA
            customer_strategy = NormalCustomerStrategy(sigma_buyer)
        else:
            customer_strategy = FixedCustomerStrategy()
    
    # ========== 2. СТРАТЕГИЯ ПОСТАВОК ==========
    if category_id == 1:  # strict (молоко)
        if params.milk_delivery_frequency and params.milk_delivery_frequency > 0:
            delivery_strategy = PeriodicDelivery(params.milk_delivery_frequency)
        else:
            delivery_days = params.milk_delivery_days if params.milk_delivery_days is not None else []
            delivery_strategy = DaysOfWeekDelivery(delivery_days)
    else:  # gradual products
        if params.tomatoes_delivery_frequency and params.tomatoes_delivery_frequency > 0:
            delivery_strategy = PeriodicDelivery(params.tomatoes_delivery_frequency)
        else:
            delivery_days = params.tomatoes_delivery_days if params.tomatoes_delivery_days is not None else []
            delivery_strategy = DaysOfWeekDelivery(delivery_days)
    
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
        elif params.spoilage_type == "exponential":
            k = params.exponential_k if params.exponential_k else 0.15
            spoilage_strategy = ExponentialSpoilage(params.shelf_life_days, k)
        else:  # logistic
            k = params.logistic_k if hasattr(params, 'logistic_k') and params.logistic_k else 15.0
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
            "Экспоненциальная порча - ускоряющееся старение"
        ]
    }


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(params: SimulationParams):
    """
    Универсальная симуляция управления запасами
    
    Поддерживает:
    - Разные типы порчи (strict/linear/exponential)
    - Разные законы спроса (uniform/normal)
    - Разные стратегии поставок (periodic/days_of_week)
    - FIFO/LIFO для строгих продуктов
    """
    try:
        # Создаём продукт с нужными стратегиями
        product = create_product(params)
        
        # Запускаем симуляцию
        results = product.run(
            days=params.days, 
            start_date=params.start_date, 
            fifo_percent=params.fifo_percent or 100.0,  # Для gradual продуктов FIFO не используется
            lifo_percent=params.lifo_percent or 0.0
        )
        
        # Преобразуем историю в формат DailyResult
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
            else:  # gradual products (tomatoes, etc.)
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
        
        # Формируем ответ
        return SimulationResponse(
            total_revenue=results['total_revenue'],
            total_cost=results['total_cost'],
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
