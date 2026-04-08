from abc import ABC, abstractmethod
import random
import numpy as np


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
    def __init__(self, demand_list):
        self.demand_list = demand_list
        self.day = 0
    
    def get_demand(self, date=None, weekday_factors=None):
        if self.day < len(self.demand_list):
            demand = self.demand_list[self.day]
            self.day += 1
            return demand
        return 20
