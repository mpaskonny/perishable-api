import numpy as np
from core.spoilage import SpoilageStrategy

class LinearSpoilage(SpoilageStrategy):
    """Линейная порча: каждый день портится фиксированный процент"""
    
    def __init__(self, shelf_life_days: int):
        self.shelf_life_days = shelf_life_days
        self.daily_rate = 100.0 / shelf_life_days
    
    def calculate_spoilage(self, batch, current_date):
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        # Линейный расчёт
        daily_percent = self.daily_rate
        spoiled = batch.quantity * (daily_percent / 100)
        
        return min(spoiled, batch.quantity)


class ExponentialSpoilage(SpoilageStrategy):
    """Экспоненциальная порча: плавный рост от 0% до 100% к концу срока"""
    
    def __init__(self, shelf_life_days: int, k: float = 0.1):
        """
        k — коэффициент формы кривой
        Чем больше k, тем быстрее порча в конце срока
        """
        self.shelf_life_days = shelf_life_days
        self.k = k
        
        # Нормировочный коэффициент
        self.norm = 1 - np.exp(-k)
    
    def _cumulative_rate(self, t: float) -> float:
        """
        Накопленный процент порчи к моменту t (0..1 от срока)
        t = age_days / shelf_life_days
        """
        if t <= 0:
            return 0
        if t >= 1:
            return 100.0
        
        # Нормированная экспонента
        return 100 * (1 - np.exp(-self.k * t)) / self.norm
    
    def calculate_spoilage(self, batch, current_date):
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        # Нормированное время (0..1)
        t = age_days / self.shelf_life_days
        t_prev = (age_days - 1) / self.shelf_life_days
        
        # Процент порчи за этот день
        cum_today = self._cumulative_rate(t)
        cum_yesterday = self._cumulative_rate(t_prev)
        daily_percent = cum_today - cum_yesterday
        
        # Применяем к текущему остатку
        spoiled = batch.quantity * (daily_percent / 100)
        
        return min(spoiled, batch.quantity)
