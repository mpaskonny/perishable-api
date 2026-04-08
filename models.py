from pydantic import BaseModel
from typing import List, Optional, Any, Union
from datetime import datetime


class SimulationParams(BaseModel):
    """Общие параметры для всех симуляций"""
    days: int = 30
    min_stock: float = 300.0
    purchase_price: float = 220.0
    sale_price: float = 295.0
    
    # НОВЫЕ ПОЛЯ ДЛЯ V2
    product_type: Optional[str] = "milk"
    distribution: Optional[str] = "uniform"
    start_date: datetime = datetime(2026, 2, 1)

    # Для помидоров
    sigma_10: Optional[float] = 0.96
    sigma_50: Optional[float] = 1.59

    # Для молока
    fifo_percent: Optional[float] = 75.0
    lifo_percent: Optional[float] = 25.0
    sigma_buyer: Optional[float] = 1.51
    shelf_life_days: Optional[int] = 10
    utilization_price: Optional[float] = 5.0
    delivery_frequency: Optional[int] = 2
    delivery_days: Optional[List[int]] = [0, 3]
    delivery_type: Optional[str] = "unit"
    box_size: Optional[int] = 0

    # Коэффициенты спроса по дням недели
    weekday_factors: Optional[List[float]] = [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]

    fixed_demand: Optional[List[float]] = None


class DailyResult(BaseModel):
    """Результаты одного дня/недели симуляции"""
    day: int
    date: str
    demand: float
    start_stock: List[float]
    sales: List[float]
    spoilage: List[float]
    order: float
    revenue: float
    purchase_cost: float

    fifo_sales: Optional[float] = None
    lifo_sales: Optional[float] = None
    spoilage_breakdown: Optional[dict] = None


class SimulationResponse(BaseModel):
    """Полный ответ от API"""
    total_revenue: float
    total_cost: float
    total_spoilage_kg: float
    total_spoilage_money: float
    profit: float
    daily_history: List[DailyResult]
    demand_stats: dict
    spoilage_stats: dict
