from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SimulationParams(BaseModel):
    """Общие параметры для всех симуляций"""
    
    # Базовые параметры
    days: int = 30
    min_stock: float = 300.0
    purchase_price: float = 220.0
    sale_price: float = 295.0
    start_date: datetime = datetime(2026, 2, 1)
    
    # Информация о продукте
    product_name: Optional[str] = None
    product_type: Optional[str] = "tomatoes"
    
    # Параметры спроса
    distribution: Optional[str] = "uniform"
    weekday_factors: Optional[List[float]] = [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]
    fixed_demand: Optional[List[float]] = None
    
    # Параметры равномерного спроса
    demand_min: Optional[float] = None
    demand_max: Optional[float] = None
    
    # Параметры порчи
    spoilage_type: Optional[str] = "linear"
    shelf_life_days: int = 30
    power_p: Optional[float] = 2.0
    logistic_k: Optional[float] = 15.0
    
    # Параметры поставок (общие)
    delivery_type: Optional[str] = "unit"
    box_size: Optional[int] = 0
    
    # Параметры поставок для молока
    milk_delivery_frequency: Optional[int] = 2
    milk_delivery_days: Optional[List[int]] = [0, 3]
    
    # Параметры поставок для помидоров
    tomatoes_delivery_frequency: Optional[int] = 3
    tomatoes_delivery_days: Optional[List[int]] = [0, 3]
    
    # Параметры для молока
    fifo_percent: Optional[float] = 75.0
    lifo_percent: Optional[float] = 25.0
    sigma_buyer: Optional[float] = 1.51
    utilization_price: Optional[float] = 5.0
    
    # Параметры для помидоров
    sigma_10: Optional[float] = 0.96
    sigma_50: Optional[float] = 1.59
    
    # Параметры доставки
    delivery_cost_type: Optional[str] = "fixed"
    delivery_fixed_cost: float = 0.0
    delivery_rate_cost: float = 0.0
    
    # Параметры расписания поставок
    schedule_type: Optional[str] = "frequency"
    delivery_frequency: Optional[int] = 2
    delivery_days: Optional[List[int]] = [0, 3]
    reorder_point: Optional[float] = None
    max_stock: Optional[float] = None
    
    # Поля для импорта данных (реальные даты из Excel)
    use_real_demand: bool = False
    real_demand_dates: Optional[List[str]] = None      # список дат в формате YYYY-MM-DD
    real_demand_values: Optional[List[float]] = None   # список значений спроса
    real_start_date: Optional[str] = None              # ISO формат даты начала

class DailyResult(BaseModel):
    """Результаты одного дня симуляции"""
    
    day: int
    date: str
    demand: float
    start_stock: float
    sales: float
    spoilage: float
    order: float
    revenue: float
    purchase_cost: float
    end_stock: Optional[float] = None
    unmet_demand: Optional[float] = None
    
    fifo_percent: Optional[float] = None
    lifo_percent: Optional[float] = None
    utilization_cost: Optional[float] = None
    
    batch_1_stock: Optional[float] = None
    batch_2_stock: Optional[float] = None
    batch_3_stock: Optional[float] = None
    batch_4_stock: Optional[float] = None
    batch_5_stock: Optional[float] = None
    
    stock_week1: Optional[float] = None
    stock_week2: Optional[float] = None
    stock_week3: Optional[float] = None
    
    fifo_sales: Optional[float] = None
    lifo_sales: Optional[float] = None


class SimulationResponse(BaseModel):
    """Полный ответ от API"""
    
    total_revenue: float
    total_cost: float
    total_purchase_cost: float       
    total_delivery_cost: float       
    total_utilization_cost: float    
    total_spoilage_kg: float
    total_spoilage_money: float
    profit: float
    avg_stock: float
    daily_history: List[DailyResult]
    demand_stats: dict
    spoilage_stats: dict
