import numpy as np
from core.spoilage import SpoilageStrategy
from typing import Dict


class SmoothDailySpoilage(SpoilageStrategy):
    """
    Плавная подневная порча с экспоненциальной интерполяцией
    """
    
    def __init__(self, weekly_rates: Dict[int, float], weekly_sigmas: Dict[int, float], 
                 max_days: int = 42, interpolation: str = "exponential"):
        self.weekly_rates = weekly_rates
        self.weekly_sigmas = weekly_sigmas
        self.interpolation = interpolation
        self.spoilage_records = {1: [], 2: [], 3: []}
    
    def _get_daily_rate(self, age_days: int) -> float:
        if age_days <= 0:
            return 0
        
        week = (age_days - 1) // 7 + 1
        week = min(week, max(self.weekly_rates.keys()))
        
        weekly_rate = self.weekly_rates.get(week, 100.0)
        base_daily = weekly_rate / 7
        
        day_in_week = (age_days - 1) % 7 + 1
        factor = 0.3 + (day_in_week - 1) * 0.233
        daily_rate = base_daily * factor
        
        sigma = self.weekly_sigmas.get(week, 0.0) / 7
        
        if sigma > 0:
            actual_rate = np.random.normal(daily_rate, sigma)
            actual_rate = max(0, min(100, actual_rate))
        else:
            actual_rate = daily_rate
        
        return actual_rate
    
    def calculate_spoilage(self, batch, current_date):
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        daily_percent = self._get_daily_rate(age_days)
        
        week = (age_days - 1) // 7 + 1
        week = min(week, 3)
        
        weekly_equivalent = daily_percent * 7
        
        if week in self.spoilage_records:
            self.spoilage_records[week].append(weekly_equivalent)
        
        spoiled = batch.quantity * (daily_percent / 100)
        return spoiled
    
    def get_statistics(self):
        stats = {}
        for week, rates in self.spoilage_records.items():
            if rates:
                stats[f'week{week}_rates'] = rates
                stats[f'week{week}_mean'] = sum(rates) / len(rates)
        return stats
