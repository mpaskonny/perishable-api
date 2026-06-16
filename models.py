"""
models.py - Pydantic-модели для валидации данных API

Определяет структуру запросов и ответов FastAPI.
Pydantic автоматически проверяет типы и преобразует данные.

Основные модели:
- SimulationParams - параметры запроса (что присылает Streamlit)
- DailyResult - результат одного дня симуляции
- SimulationResponse - полный ответ (что возвращает API)
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class SimulationParams(BaseModel):
    """
    Параметры запроса на симуляцию.
    Streamlit отправляет JSON с этими полями, FastAPI валидирует их.
    
    Большинство полей имеют значения по умолчанию,
    поэтому можно отправлять только изменяемые параметры.
    """
    
    # ========== Базовые параметры симуляции ==========
    days: int = 30                      # количество дней симуляции
    min_stock: float = 300.0            # целевой уровень запаса (для R,S) или S (для s,S)
    purchase_price: float = 220.0       # цена закупки (руб)
    sale_price: float = 295.0           # цена продажи (руб)
    start_date: datetime = datetime(2026, 2, 1)   # дата начала
    
    # ========== Информация о продукте ==========
    product_name: Optional[str] = None          # название товара из БД
    product_type: Optional[str] = "tomatoes"    # 'milk' или 'tomatoes' (для обратной совместимости)
    
    # ========== Параметры спроса ==========
    distribution: Optional[str] = "uniform"     # 'uniform' или 'normal'
    weekday_factors: Optional[List[float]] = [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]  # Пн-Вс
    fixed_demand: Optional[List[float]] = None  # фиксированный список (для тестов)
    
    # Для равномерного распределения
    demand_min: Optional[float] = None          # минимальный спрос
    demand_max: Optional[float] = None          # максимальный спрос
    
    # ========== Параметры порчи ==========
    spoilage_type: Optional[str] = "linear"     # 'linear', 'power', 'logistic'
    shelf_life_days: int = 30                   # срок годности в днях
    power_p: Optional[float] = 2.0              # степень для степенной порчи
    logistic_k: Optional[float] = 15.0          # крутизна для логистической
    
    # ========== Параметры поставок ==========
    delivery_type: Optional[str] = "unit"       # 'unit' (штучно) или 'box' (коробками)
    box_size: Optional[int] = 0                 # размер коробки (если box)
    fixed_quantity: Optional[float] = None      # фиксированный объём Q (для R,Q и s,Q)
    
    # Для обратной совместимости (раньше были отдельно для молока и помидоров)
    milk_delivery_frequency: Optional[int] = 2
    milk_delivery_days: Optional[List[int]] = [0, 3]
    tomatoes_delivery_frequency: Optional[int] = 3
    tomatoes_delivery_days: Optional[List[int]] = [0, 3]
    
    # ========== Параметры для строгих товаров (молоко) ==========
    fifo_percent: Optional[float] = 75.0        # процент FIFO покупателей
    lifo_percent: Optional[float] = 25.0        # процент LIFO (обычно 100 - fifo)
    sigma_buyer: Optional[float] = 1.51         # теоретическая сигма для FIFO
    utilization_price: Optional[float] = 5.0    # стоимость утилизации (руб/кг)
    
    # ========== Параметры для помидоров (обратная совместимость) ==========
    sigma_10: Optional[float] = 0.96
    sigma_50: Optional[float] = 1.59
    
    # ========== Параметры доставки (стоимость) ==========
    delivery_cost_type: Optional[str] = "fixed"     # 'none', 'fixed', 'rate', 'combined'
    delivery_fixed_cost: float = 0.0                # фиксированная стоимость за поставку
    delivery_rate_cost: float = 0.0                 # тариф за кг/шт
    
    # ========== Стратегия управления запасами ==========
    strategy_type: Optional[str] = "r_s"            # 'r_s', 'r_q', 's_s', 's_q', 'custom'
    
    # ========== Расписание поставок ==========
    schedule_type: Optional[str] = "frequency"      # 'frequency' или 'days'
    delivery_frequency: Optional[int] = 2           # периодичность в днях (для frequency)
    delivery_days: Optional[List[int]] = [0, 3]     # дни недели (0=Пн, 6=Вс) для days
    reorder_point: Optional[float] = None           # точка заказа s (для s,S и s,Q)
    max_stock: Optional[float] = None               # максимальный запас S (для s,S)
    
    # ========== Импорт реальных данных из Excel ==========
    use_real_demand: bool = False                   # использовать реальные данные?
    real_demand_dates: Optional[List[str]] = None   # даты (YYYY-MM-DD)
    real_demand_values: Optional[List[float]] = None # значения спроса
    real_start_date: Optional[str] = None           # реальная дата начала


class DailyResult(BaseModel):
    """
    Результаты одного дня симуляции.
    Используется внутри SimulationResponse.
    
    Поля могут быть None для разных типов товаров:
    - для молока: fifo_percent, lifo_percent, batch_*_stock
    - для помидоров: stock_week1-3
    """
    
    # Базовые поля (есть всегда)
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
    
    # Для строгих товаров (молоко)
    fifo_percent: Optional[float] = None
    lifo_percent: Optional[float] = None
    utilization_cost: Optional[float] = None
    
    # Остатки по партиям (первые 5 партий)
    batch_1_stock: Optional[float] = None
    batch_2_stock: Optional[float] = None
    batch_3_stock: Optional[float] = None
    batch_4_stock: Optional[float] = None
    batch_5_stock: Optional[float] = None
    
    # Для товаров с постепенной порчей (овощи)
    stock_week1: Optional[float] = None      # остаток 0-7 дней
    stock_week2: Optional[float] = None      # остаток 8-14 дней
    stock_week3: Optional[float] = None      # остаток 15+ дней
    
    # Продажи по типам (для молока)
    fifo_sales: Optional[float] = None
    lifo_sales: Optional[float] = None


class SimulationResponse(BaseModel):
    """
    Полный ответ API после симуляции.
    Содержит итоговые метрики и историю по дням.
    """
    
    # Итоговые метрики
    total_revenue: float                    # общая выручка (руб)
    total_cost: float                       # общие затраты (руб)
    total_purchase_cost: float              # затраты на закупку (руб)
    total_delivery_cost: float              # затраты на доставку (руб)
    total_utilization_cost: float           # затраты на утилизацию (руб)
    total_spoilage_kg: float                # потери от порчи (кг/шт)
    total_spoilage_money: float             # потери в деньгах (руб)
    profit: float                           # чистая прибыль (руб)
    avg_stock: float                        # средний остаток за период
    
    # История по дням
    daily_history: List[DailyResult]
    
    # Дополнительная статистика
    demand_stats: dict                      # среднее/мин/макс спроса
    spoilage_stats: dict                    # статистика порчи/FIFO
