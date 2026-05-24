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


class PowerSpoilage(SpoilageStrategy):
    """
    Степенная (параболическая) порча.
    Товар долго остаётся свежим, затем быстро портится в конце срока.
    Формула: S(t) = 100 * (t/T)^p
    где t — возраст в днях, T — срок годности, p — степень кривизны
    """
    
    def __init__(self, shelf_life_days: int, p: float = 2.0):
        """
        shelf_life_days: срок годности в днях
        p: степень кривизны (1.5-4.0, чем больше, тем резче рост в конце)
        """
        self.shelf_life_days = shelf_life_days
        self.p = p
    
    def _cumulative_rate(self, age_days: int) -> float:
        """Накопленный процент порчи к возрасту age_days"""
        if age_days <= 0:
            return 0
        if age_days >= self.shelf_life_days:
            return 100.0
        
        t = age_days / self.shelf_life_days
        return 100 * (t ** self.p)
    
    def calculate_spoilage(self, batch, current_date):
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        cum_today = self._cumulative_rate(age_days)
        cum_yesterday = self._cumulative_rate(age_days - 1)
        daily_percent = cum_today - cum_yesterday
        daily_percent = max(0, min(100, daily_percent))
        
        spoiled = batch.quantity * (daily_percent / 100)
        return min(spoiled, batch.quantity)


class LogisticSpoilage(SpoilageStrategy):
    """
    Логистическая (S-образная) порча.
    В начале товар почти не портится, затем резко портится в конце срока.
    Формула: S(t) = 100 / (1 + e^(-k * (t - 0.5)))
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
