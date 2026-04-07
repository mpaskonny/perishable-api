from abc import ABC, abstractmethod
import random


class SpoilageStrategy(ABC):
    """Абстрактная стратегия порчи"""
    
    @abstractmethod
    def calculate_spoilage(self, batch, current_date):
        """Возвращает количество испорченного товара"""
        pass


class StrictExpirySpoilage(SpoilageStrategy):
    """Строгий срок годности (для молока)"""
    
    def calculate_spoilage(self, batch, current_date):
        if batch.expiry_date and batch.expiry_date <= current_date:
            return batch.quantity
        return 0


class WeeklySpoilage(SpoilageStrategy):
    """Недельная порча с процентами (для помидоров)"""
    
    def __init__(self, week_rates, week_sigmas):
        """
        week_rates: dict {1: 10.0, 2: 50.0, 3: 100.0}
        week_sigmas: dict {1: 0.96, 2: 1.59}
        """
        self.week_rates = week_rates
        self.week_sigmas = week_sigmas
    
    def calculate_spoilage(self, batch, current_date):
        age_weeks = (current_date - batch.arrival_date).days // 7
        if age_weeks <= 0:
            return 0
        
        rate = self.week_rates.get(age_weeks, 100.0)
        sigma = self.week_sigmas.get(age_weeks, 0.0)
        
        if sigma > 0:
            r = [random.random() for _ in range(12)]
            deviation = sum(r) - 6
            actual_rate = sigma * deviation + rate
            actual_rate = max(0, min(100, actual_rate))
        else:
            actual_rate = rate
        
        return batch.quantity * (actual_rate / 100)
