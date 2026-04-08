from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SimulationParams, SimulationResponse, DailyResult
from core.demand import UniformDemand, NormalDemand, FixedDemand
from core.customer import FixedCustomerStrategy, NormalCustomerStrategy
from core.delivery import PeriodicDelivery, DaysOfWeekDelivery
from products.milk import Milk
from products.tomatoes import Tomatoes


# ========== КОНСТАНТЫ ==========
MILK_UNIFORM_MIN = 20
MILK_UNIFORM_MAX = 30
MILK_NORMAL_MEAN = 25
MILK_NORMAL_SIGMA = 1.41

TOMATOES_UNIFORM_MIN = 150
TOMATOES_UNIFORM_MAX = 200
TOMATOES_NORMAL_MEAN = 175
TOMATOES_NORMAL_SIGMA = 14.91

MILK_CUSTOMER_SIGMA = 1.51

TOMATOES_WEEK1_RATE = 10.0
TOMATOES_WEEK2_RATE = 50.0
TOMATOES_WEEK3_RATE = 100.0
TOMATOES_WEEK1_SIGMA = 0.96
TOMATOES_WEEK2_SIGMA = 1.59

DEFAULT_WEEKDAY_FACTORS = [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]

DEFAULT_SHELF_LIFE_DAYS = 10
DEFAULT_UTILIZATION_PRICE = 5.0

# ========== ПРИЛОЖЕНИЕ ==========
app = FastAPI(
    title="Симулятор продуктов с ограниченным сроком годности",
    description="Универсальный API для симуляции",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_product(params: SimulationParams):
    """Фабрика для создания продукта"""
    
    if params.fixed_demand:
        demand_strategy = FixedDemand(params.fixed_demand)
        customer_strategy = FixedCustomerStrategy()
    elif params.distribution == "uniform":
        if params.product_type == "milk":
            demand_strategy = UniformDemand(MILK_UNIFORM_MIN, MILK_UNIFORM_MAX)
        else:
            demand_strategy = UniformDemand(TOMATOES_UNIFORM_MIN, TOMATOES_UNIFORM_MAX)
        customer_strategy = FixedCustomerStrategy()
    else:
        if params.product_type == "milk":
            demand_strategy = NormalDemand(MILK_NORMAL_MEAN, MILK_NORMAL_SIGMA)
            sigma_buyer = params.sigma_buyer if params.sigma_buyer is not None else MILK_CUSTOMER_SIGMA
            customer_strategy = NormalCustomerStrategy(sigma_buyer)
        else:
            demand_strategy = NormalDemand(TOMATOES_NORMAL_MEAN, TOMATOES_NORMAL_SIGMA)
            customer_strategy = FixedCustomerStrategy()
    
    weekday_factors = params.weekday_factors if params.weekday_factors else DEFAULT_WEEKDAY_FACTORS
    
    if params.product_type == "milk":
        if params.milk_delivery_frequency and params.milk_delivery_frequency > 0:
            delivery_strategy = PeriodicDelivery(params.milk_delivery_frequency)
        else:
            delivery_days = params.milk_delivery_days if params.milk_delivery_days is not None else []
            delivery_strategy = DaysOfWeekDelivery(delivery_days)
        
        return Milk(
            name="Молоко",
            purchase_price=params.purchase_price,
            sale_price=params.sale_price,
            min_stock=params.min_stock,
            demand_strategy=demand_strategy,
            customer_strategy=customer_strategy,
            delivery_strategy=delivery_strategy,
            shelf_life_days=params.shelf_life_days or DEFAULT_SHELF_LIFE_DAYS,
            utilization_price=params.utilization_price or DEFAULT_UTILIZATION_PRICE,
            weekday_factors=weekday_factors,
            delivery_type=params.delivery_type or "unit",
            box_size=params.box_size or 0
        )
    else:
        if params.tomatoes_delivery_frequency and params.tomatoes_delivery_frequency > 0:
            delivery_strategy = PeriodicDelivery(params.tomatoes_delivery_frequency)
        else:
            delivery_days = params.tomatoes_delivery_days if params.tomatoes_delivery_days is not None else []
            delivery_strategy = DaysOfWeekDelivery(delivery_days)
        
        return Tomatoes(
            name="Помидоры",
            purchase_price=params.purchase_price,
            sale_price=params.sale_price,
            min_stock=params.min_stock,
            demand_strategy=demand_strategy,
            customer_strategy=customer_strategy,
            delivery_strategy=delivery_strategy,
            week_rates={
                1: TOMATOES_WEEK1_RATE, 
                2: TOMATOES_WEEK2_RATE, 
                3: TOMATOES_WEEK3_RATE
            },
            week_sigmas={
                1: params.sigma_10 or TOMATOES_WEEK1_SIGMA, 
                2: params.sigma_50 or TOMATOES_WEEK2_SIGMA
            },
            weekday_factors=weekday_factors,
            delivery_type=params.delivery_type or "unit",
            box_size=params.box_size or 0,
            interpolation='exponential'
        )


@app.get("/")
async def root():
    return {
        "message": "API симулятора продуктов",
        "endpoints": ["/simulate", "/docs"]
    }


@app.post("/simulate", response_model=SimulationResponse)
async def simulate(params: SimulationParams):
    """Универсальная симуляция"""
    try:
        product = create_product(params)
        results = product.run(params.days, params.start_date, params.fifo_percent, params.lifo_percent)
        
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
                    stock_week1=None,
                    stock_week2=None,
                    stock_week3=None
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
                    fifo_sales=0.0,
                    lifo_sales=0.0,
                    stock_week1=float(h.get('stock_week1', 0)),
                    stock_week2=float(h.get('stock_week2', 0)),
                    stock_week3=float(h.get('stock_week3', 0))
                ))
        
        return SimulationResponse(
            total_revenue=results['total_revenue'],
            total_cost=results['total_cost'],
            total_spoilage_kg=results['total_spoilage_kg'],
            total_spoilage_money=results['total_spoilage_money'],
            profit=results['profit'],
            daily_history=daily_results,
            demand_stats=results['demand_stats'],
            spoilage_stats=results['spoilage_stats']
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
