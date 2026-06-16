"""
simple_spoilage.py - Реализация трёх моделей порчи

1. Линейная - равномерное старение
2. Степенная (параболическая) - ускорение к концу срока
3. Логистическая (S-образная) - резкое ускорение в конце

Все модели поддерживают вариативность срока годности (нормальное распределение).
Сигмы для вариативности загружаются из Excel (spoilage_sigma.xlsx).
"""

import numpy as np
from core.spoilage import SpoilageStrategy
from core.spoilage_sigma_loader import get_spoilage_sigma_loader


class LinearSpoilage(SpoilageStrategy):
    """Линейная порча - каждый день портится фиксированный процент"""
    
    def __init__(self, shelf_life_days: int):
        self.base_shelf_life = shelf_life_days
        self.daily_rate = 100.0 / shelf_life_days  # % в день
    
    def _get_actual_shelf_life(self) -> int:
        """Генерирует фактический срок годности (нормальное распределение)"""
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
        
        # Если срок истёк - списываем всё
        if age_days >= batch.actual_shelf_life:
            spoiled = batch.quantity
            batch.quantity = 0
            return spoiled
        
        # Иначе - фиксированный процент от остатка
        daily_percent = self.daily_rate
        spoiled = batch.quantity * (daily_percent / 100)
        batch.quantity -= spoiled
        return min(spoiled, batch.quantity + spoiled)


class PowerSpoilage(SpoilageStrategy):
    """Степенная порча - ускорение к концу срока (парабола)"""
    
    def __init__(self, shelf_life_days: int, p: float = 2.0):
        self.base_shelf_life = shelf_life_days
        self.p = p  # степень кривизны (2 = парабола, >2 - резче)
    
    def _get_actual_shelf_life(self) -> int:
        loader = get_spoilage_sigma_loader()
        sigma = loader.get_sigma(self.base_shelf_life)
        
        actual = int(round(np.random.normal(self.base_shelf_life, sigma)))
        return max(1, min(self.base_shelf_life * 2, actual))
    
    def _cumulative_rate(self, age_days: int, shelf_life: int) -> float:
        """Накопленный процент порчи на текущий день"""
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
        
        # Дневной процент = разница накопленных процентов
        cum_today = self._cumulative_rate(age_days, shelf)
        cum_yesterday = self._cumulative_rate(age_days - 1, shelf)
        daily_percent = cum_today - cum_yesterday
        daily_percent = max(0, min(100, daily_percent))
        
        spoiled = batch.quantity * (daily_percent / 100)
        batch.quantity -= spoiled
        return spoiled


class LogisticSpoilage(SpoilageStrategy):
    """Логистическая порча - S-образная кривая (резкое ускорение в конце)"""
    
    def __init__(self, shelf_life_days: int, k: float = 15.0):
        self.base_shelf_life = shelf_life_days
        self.k = k  # крутизна (чем больше, тем резче переход)
    
    def _get_actual_shelf_life(self) -> int:
        loader = get_spoilage_sigma_loader()
        sigma = loader.get_sigma(self.base_shelf_life)
        
        actual = int(round(np.random.normal(self.base_shelf_life, sigma)))
        return max(1, min(self.base_shelf_life * 2, actual))
    
    def _cumulative_rate(self, age_days: int, shelf_life: int) -> float:
        """Накопленный процент порчи по логистической функции"""
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
