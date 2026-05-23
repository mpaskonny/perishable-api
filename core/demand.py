from abc import ABC, abstractmethod
import random
import numpy as np
from datetime import date
from typing import Dict


class DemandStrategy(ABC):
    """Абстрактная стратегия спроса"""
    
    @abstractmethod
    def get_demand(self, date, weekday_factors=None):
        pass


class UniformDemand(DemandStrategy):
    """Равномерное распределение спроса"""
    
    def __init__(self, min_demand, max_demand):
        self.min_demand = min_demand
        self.max_demand = max_demand
    
    def get_demand(self, date, weekday_factors=None):
        base_demand = random.uniform(self.min_demand, self.max_demand)
        if weekday_factors:
            base_demand *= weekday_factors[date.weekday()]
        return int(round(base_demand))


class NormalDemand(DemandStrategy):
    """Нормальное распределение спроса"""
    
    def __init__(self, mean, sigma):
        self.mean = mean
        self.sigma = sigma
    
    def get_demand(self, date, weekday_factors=None):
        base_demand = np.random.normal(self.mean, self.sigma)
        base_demand = max(1, base_demand)
        if weekday_factors:
            base_demand *= weekday_factors[date.weekday()]
        return int(round(base_demand))


class FixedDemand(DemandStrategy):
    """Фиксированный спрос (список значений по дням)"""
    
    def __init__(self, demand_list):
        self.demand_list = demand_list
        self.day = 0
    
    def get_demand(self, date=None, weekday_factors=None):
        if self.day < len(self.demand_list):
            demand = self.demand_list[self.day]
            self.day += 1
            return demand
        return 20


class RealDemand(DemandStrategy):
    """
    Стратегия спроса на основе реальных данных из Excel.
    Если для даты нет данных, используется базовое значение.
    """
    
    def __init__(self, demand_data: Dict[date, float], base_demand: float = 100.0):
        """
        Args:
            demand_data: словарь {дата: спрос}
            base_demand: значение по умолчанию, если для даты нет данных
        """
        self.demand_data = demand_data
        self.base_demand = base_demand
    
    def get_demand(self, date, weekday_factors=None):
        # Ищем спрос на конкретную дату
        demand = self.demand_data.get(date.date(), self.base_demand)
        
        # Применяем коэффициенты дня недели (если есть)
        if weekday_factors:
            demand *= weekday_factors[date.weekday()]
        
        return int(round(demand))
