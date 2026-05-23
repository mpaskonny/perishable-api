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
    product_type: Optional[str] = "tomatoes"  # "milk" или "tomatoes" (или любой gradual)
    
    # Параметры спроса
    distribution: Optional[str] = "uniform"  # "uniform" или "normal"
    weekday_factors: Optional[List[float]] = [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]
    fixed_demand: Optional[List[float]] = None
    
    # Параметры порчи
    spoilage_type: Optional[str] = "linear"  # "linear", "exponential", "logistic"
    shelf_life_days: int = 30
    exponential_k: Optional[float] = 0.15   # для экспоненциальной порчи
    logistic_k: Optional[float] = 15.0      # для логистической порчи
    
    # Параметры поставок (общие)
    delivery_type: Optional[str] = "unit"  # "unit" или "box"
    box_size: Optional[int] = 0
    
    # Параметры поставок для молока
    milk_delivery_frequency: Optional[int] = 2
    milk_delivery_days: Optional[List[int]] = [0, 3]
    
    # Параметры поставок для помидоров
    tomatoes_delivery_frequency: Optional[int] = 3
    tomatoes_delivery_days: Optional[List[int]] = [0, 3]
    
    # Параметры для молока (строгая порча + FIFO/LIFO)
    fifo_percent: Optional[float] = 75.0
    lifo_percent: Optional[float] = 25.0
    sigma_buyer: Optional[float] = 1.51
    utilization_price: Optional[float] = 5.0
    
    # Параметры для помидоров (постепенная порча)
    sigma_10: Optional[float] = 0.96  # устарело, оставлено для совместимости
    sigma_50: Optional[float] = 1.59  # устарело, оставлено для совместимости


class DailyResult(BaseModel):
    """Результаты одного дня симуляции"""
    
    # Обязательные поля для всех продуктов
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
    
    # Для молока (строгая порча)
    fifo_percent: Optional[float] = None
    lifo_percent: Optional[float] = None
    utilization_cost: Optional[float] = None
    
    # Для молока (остатки по партиям)
    batch_1_stock: Optional[float] = None
    batch_2_stock: Optional[float] = None
    batch_3_stock: Optional[float] = None
    batch_4_stock: Optional[float] = None
    batch_5_stock: Optional[float] = None
    
    # Для помидоров (постепенная порча)
    stock_week1: Optional[float] = None
    stock_week2: Optional[float] = None
    stock_week3: Optional[float] = None
    
    # Устаревшие поля (оставлены для совместимости)
    fifo_sales: Optional[float] = None
    lifo_sales: Optional[float] = None


class SimulationResponse(BaseModel):
    """Полный ответ от API"""
    
    total_revenue: float
    total_cost: float
    total_spoilage_kg: float
    total_spoilage_money: float
    profit: float
    avg_stock: float
    daily_history: List[DailyResult]
    demand_stats: dict
    spoilage_stats: dict
