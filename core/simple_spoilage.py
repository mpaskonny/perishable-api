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
        
        daily_percent = self.daily_rate
        spoiled = batch.quantity * (daily_percent / 100)
        
        return min(spoiled, batch.quantity)


class ExponentialSpoilage(SpoilageStrategy):
    """
    Экспоненциальная порча: быстрое старение в начале, замедление в конце
    Формула: S(t) = 100 * (1 - exp(-k * t)) / (1 - exp(-k))
    где t = возраст / срок_годности
    """
    
    def __init__(self, shelf_life_days: int, k: float = 0.15):
        """
        shelf_life_days: срок годности в днях
        k: коэффициент крутизны (0.05-0.5, чем больше, тем быстрее порча)
        """
        self.shelf_life_days = shelf_life_days
        self.k = k
        self.norm = 1 - np.exp(-k)
    
    def _cumulative_rate(self, t: float) -> float:
        """
        Накопленный процент порчи к моменту t (0..1)
        """
        if t <= 0:
            return 0
        if t >= 1:
            return 100.0
        
        return 100 * (1 - np.exp(-self.k * t)) / self.norm
    
    def calculate_spoilage(self, batch, current_date):
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        t = age_days / self.shelf_life_days
        t_prev = (age_days - 1) / self.shelf_life_days
        
        cum_today = self._cumulative_rate(t)
        cum_yesterday = self._cumulative_rate(t_prev)
        daily_percent = cum_today - cum_yesterday
        
        daily_percent = max(0, min(100, daily_percent))
        
        spoiled = batch.quantity * (daily_percent / 100)
        return min(spoiled, batch.quantity)


class LogisticSpoilage(SpoilageStrategy):
    """
    Логистическая (S-образная) порча.
    В начале товар почти не портится, затем резко портится в конце срока.
    Формула: S(t) = 100 / (1 + exp(-k * (t - 0.5)))
    где t = возраст / срок_годности
    """
    
    def __init__(self, shelf_life_days: int, k: float = 15.0):
        """
        shelf_life_days: срок годности в днях
        k: коэффициент крутизны (5-30, чем больше, тем резче переход)
        """
        self.shelf_life_days = shelf_life_days
        self.k = k
    
    def _cumulative_rate(self, t: float) -> float:
        """
        Накопленный процент порчи к моменту t (0..1)
        """
        if t <= 0:
            return 0
        if t >= 1:
            return 100.0
        
        return 100 / (1 + np.exp(-self.k * (t - 0.5)))
    
    def calculate_spoilage(self, batch, current_date):
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        t = age_days / self.shelf_life_days
        t_prev = (age_days - 1) / self.shelf_life_days
        
        cum_today = self._cumulative_rate(t)
        cum_yesterday = self._cumulative_rate(t_prev)
        daily_percent = cum_today - cum_yesterday
        
        daily_percent = max(0, min(100, daily_percent))
        
        spoiled = batch.quantity * (daily_percent / 100)
        return min(spoiled, batch.quantity)
