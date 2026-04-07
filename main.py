from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import SimulationParams, SimulationResponse, DailyResult
from core.demand import UniformDemand, NormalDemand, FixedDemand
from core.customer import FixedCustomerStrategy, NormalCustomerStrategy
from core.delivery import PeriodicDelivery, DaysOfWeekDelivery
from products.milk import Milk
from products.tomatoes import Tomatoes

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
    
    # Стратегия спроса
    if params.fixed_demand:
        demand_strategy = FixedDemand(params.fixed_demand)
        customer_strategy = FixedCustomerStrategy()
    elif params.distribution == "uniform":
        if params.product_type == "milk":
            demand_strategy = UniformDemand(20, 30)
        else:
            demand_strategy = UniformDemand(150, 200)
        customer_strategy = FixedCustomerStrategy()
    else:
        if params.product_type == "milk":
            demand_strategy = NormalDemand(25, 1.41)
        else:
            demand_strategy = NormalDemand(175, 14.91)
        customer_strategy = NormalCustomerStrategy(params.sigma_buyer)
    
    # Стратегия поставок
    if params.product_type == "milk":
        if params.delivery_frequency > 0:
            delivery_strategy = PeriodicDelivery(params.delivery_frequency)
        else:
            delivery_strategy = DaysOfWeekDelivery(params.delivery_days)
    else:  # tomatoes
        delivery_strategy = PeriodicDelivery(1)
    
    weekday_factors = params.weekday_factors if params.product_type == "milk" else None
    
    if params.product_type == "milk":
        return Milk(
            name="Молоко",
            purchase_price=params.purchase_price,
            sale_price=params.sale_price,
            min_stock=params.min_stock,
            demand_strategy=demand_strategy,
            customer_strategy=customer_strategy,
            delivery_strategy=delivery_strategy,
            shelf_life_days=params.shelf_life_days,
            utilization_price=params.utilization_price,
            weekday_factors=weekday_factors
        )
    else:
        return Tomatoes(
            name="Помидоры",
            purchase_price=params.purchase_price,
            sale_price=params.sale_price,
            min_stock=params.min_stock,
            demand_strategy=demand_strategy,
            customer_strategy=customer_strategy,
            delivery_strategy=delivery_strategy,
            week_rates={1: 10.0, 2: 50.0, 3: 100.0},
            week_sigmas={1: params.sigma_10, 2: params.sigma_50},
            weekday_factors=weekday_factors
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
            daily_results.append(DailyResult(
                day=h['day'],
                date=h['date'],
                demand=float(h['demand']),
                start_stock=[float(h['start_stock'])],
                sales=[float(h['fifo_sales']), float(h['lifo_sales']), 0.0],
                spoilage=[float(h['spoilage_kg']), 0.0, 0.0],
                order=float(h['order']),
                revenue=float(h['revenue']),
                purchase_cost=float(h['purchase_cost'])
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
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
