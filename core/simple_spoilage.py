import numpy as np
from core.spoilage import SpoilageStrategy
from core.spoilage_sigma_loader import get_spoilage_sigma_loader


class LinearSpoilage(SpoilageStrategy):
    """Линейная порча с вариативностью срока годности"""
    
    def __init__(self, shelf_life_days: int):
        self.base_shelf_life = shelf_life_days
        self.daily_rate = 100.0 / shelf_life_days
    
    def _get_actual_shelf_life(self) -> int:
        """Генерирует фактический срок годности по нормальному закону с сигмой из файла"""
        loader = get_spoilage_sigma_loader()
        sigma = loader.get_sigma(self.base_shelf_life)
        
        actual = int(round(np.random.normal(self.base_shelf_life, sigma)))
        return max(1, min(self.base_shelf_life * 2, actual))
    
    def calculate_spoilage(self, batch, current_date):
        if not hasattr(batch, 'actual_shelf_life'):
            batch.actual_shelf_life = self._get_actual_shelf_life()
        
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        if age_days >= batch.actual_shelf_life:
            spoiled = batch.quantity
            batch.quantity = 0
            return spoiled
        
        daily_percent = self.daily_rate
        spoiled = batch.quantity * (daily_percent / 100)
        batch.quantity -= spoiled
        return min(spoiled, batch.quantity + spoiled)


class PowerSpoilage(SpoilageStrategy):
    """Степенная (параболическая) порча с вариативностью срока годности"""
    
    def __init__(self, shelf_life_days: int, p: float = 2.0):
        self.base_shelf_life = shelf_life_days
        self.p = p
    
    def _get_actual_shelf_life(self) -> int:
        loader = get_spoilage_sigma_loader()
        sigma = loader.get_sigma(self.base_shelf_life)
        
        actual = int(round(np.random.normal(self.base_shelf_life, sigma)))
        return max(1, min(self.base_shelf_life * 2, actual))
    
    def _cumulative_rate(self, age_days: int, shelf_life: int) -> float:
        if age_days <= 0:
            return 0
        if age_days >= shelf_life:
            return 100.0
        return 100 * ((age_days / shelf_life) ** self.p)
    
    def calculate_spoilage(self, batch, current_date):
        if not hasattr(batch, 'actual_shelf_life'):
            batch.actual_shelf_life = self._get_actual_shelf_life()
        
        age_days = (current_date - batch.arrival_date).days
        shelf = batch.actual_shelf_life
        
        if age_days <= 0:
            return 0
        if age_days >= shelf:
            spoiled = batch.quantity
            batch.quantity = 0
            return spoiled
        
        cum_today = self._cumulative_rate(age_days, shelf)
        cum_yesterday = self._cumulative_rate(age_days - 1, shelf)
        daily_percent = cum_today - cum_yesterday
        daily_percent = max(0, min(100, daily_percent))
        
        spoiled = batch.quantity * (daily_percent / 100)
        batch.quantity -= spoiled
        return spoiled


class LogisticSpoilage(SpoilageStrategy):
    """Логистическая (S-образная) порча с вариативностью срока годности"""
    
    def __init__(self, shelf_life_days: int, k: float = 15.0):
        self.base_shelf_life = shelf_life_days
        self.k = k
    
    def _get_actual_shelf_life(self) -> int:
        loader = get_spoilage_sigma_loader()
        sigma = loader.get_sigma(self.base_shelf_life)
        
        actual = int(round(np.random.normal(self.base_shelf_life, sigma)))
        return max(1, min(self.base_shelf_life * 2, actual))
    
    def _cumulative_rate(self, age_days: int, shelf_life: int) -> float:
        if age_days <= 0:
            return 0
        if age_days >= shelf_life:
            return 100.0
        t = age_days / shelf_life
        return 100 / (1 + np.exp(-self.k * (t - 0.5)))
    
    def calculate_spoilage(self, batch, current_date):
        if not hasattr(batch, 'actual_shelf_life'):
            batch.actual_shelf_life = self._get_actual_shelf_life()
        
        age_days = (current_date - batch.arrival_date).days
        shelf = batch.actual_shelf_life
        
        if age_days <= 0:
            return 0
        if age_days >= shelf:
            spoiled = batch.quantity
            batch.quantity = 0
            return spoiled
        
        cum_today = self._cumulative_rate(age_days, shelf)
        cum_yesterday = self._cumulative_rate(age_days - 1, shelf)
        daily_percent = cum_today - cum_yesterday
        daily_percent = max(0, min(100, daily_percent))
        
        spoiled = batch.quantity * (daily_percent / 100)
        batch.quantity -= spoiled
        return spoiled
    