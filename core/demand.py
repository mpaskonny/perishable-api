"""
demand.py - Стратегии генерации спроса

Поддерживает:
- Равномерное распределение (мин/макс)
- Нормальное распределение (среднее/сигма)
- Фиксированный список (для тестов)
- Реальные данные из Excel (с интерполяцией пропусков)
"""

from abc import ABC, abstractmethod
import random
import numpy as np
from datetime import date, datetime
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
    """Нормальное распределение спроса (колокол)"""
    
    def __init__(self, mean, sigma):
        self.mean = mean
        self.sigma = sigma
    
    def get_demand(self, date, weekday_factors=None):
        base_demand = np.random.normal(self.mean, self.sigma)
        base_demand = max(1, base_demand)  # спрос не может быть меньше 1
        if weekday_factors:
            base_demand *= weekday_factors[date.weekday()]
        return int(round(base_demand))


class FixedDemand(DemandStrategy):
    """Фиксированный спрос - для отладки и тестов"""
    
    def __init__(self, demand_list):
        self.demand_list = demand_list
        self.day = 0
    
    def get_demand(self, date=None, weekday_factors=None):
        if self.day < len(self.demand_list):
            demand = self.demand_list[self.day]
            self.day += 1
            return demand
        return 20  # значение по умолчанию


class RealDemand(DemandStrategy):
    """
    Спрос из реальных данных (без интерполяции)
    Если даты нет - берём базовый спрос
    """
    
    def __init__(self, demand_data: Dict[date, float], base_demand: float = 100.0):
        self.demand_data = demand_data
        self.base_demand = base_demand
    
    def get_demand(self, date, weekday_factors=None):
        demand = self.demand_data.get(date.date(), self.base_demand)
        if weekday_factors:
            demand *= weekday_factors[date.weekday()]
        return int(round(demand))


class RealDemandWithInterpolation(DemandStrategy):
    """
    Спрос из реальных данных с линейной интерполяцией пропущенных дней
    Это основной класс для импорта - заполняет пробелы в данных
    """
    
    def __init__(self, demand_data: Dict[datetime.date, float], base_demand: float = 100.0):
        self.demand_data = demand_data
        self.base_demand = base_demand
    
    def get_demand(self, date, weekday_factors=None):
        date_key = date.date()
        
        # Если есть точное значение - берём его
        if date_key in self.demand_data:
            demand = self.demand_data[date_key]
        else:
            # Нет данных - интерполируем
            demand = self._interpolate_demand(date_key)
        
        if weekday_factors:
            demand *= weekday_factors[date.weekday()]
        
        return int(round(demand))
    
    def _interpolate_demand(self, target_date):
        """Линейная интерполяция между ближайшими известными датами"""
        dates = sorted(self.demand_data.keys())
        
        # Ищем ближайшие даты слева и справа
        prev_date = None
        next_date = None
        
        for d in dates:
            if d < target_date:
                prev_date = d
            elif d > target_date:
                next_date = d
                break
        
        # Крайние случаи: до начала или после конца
        if prev_date is None and next_date is None:
            return self.base_demand
        elif prev_date is None:
            return self.demand_data[next_date]
        elif next_date is None:
            return self.demand_data[prev_date]
        
        # Линейная интерполяция
        prev_demand = self.demand_data[prev_date]
        next_demand = self.demand_data[next_date]
        
        days_diff = (next_date - prev_date).days
        days_from_prev = (target_date - prev_date).days
        
        if days_diff == 0:
            return prev_demand
        
        ratio = days_from_prev / days_diff
        return prev_demand + (next_demand - prev_demand) * ratio
