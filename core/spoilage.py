"""
spoilage.py - Базовый класс для стратегий порчи

Содержит абстрактный класс SpoilageStrategy и реализацию
для строгих товаров (мгновенная порча после expiry_date).
Конкретные модели порчи (линейная, степенная, логистическая)
вынесены в simple_spoilage.py.
"""

from abc import ABC, abstractmethod


class SpoilageStrategy(ABC):
    """Абстрактная стратегия порчи"""
    
    @abstractmethod
    def calculate_spoilage(self, batch, current_date):
        """
        Рассчитывает количество испорченного товара за день.
        batch - объект партии с полями arrival_date, quantity, expiry_date
        current_date - текущая дата
        """
        pass


class StrictExpirySpoilage(SpoilageStrategy):
    """Стратегия для товаров со строгим сроком годности (молоко, йогурты).
       Порча наступает мгновенно после истечения срока годности."""
    
    def calculate_spoilage(self, batch, current_date):
        # Если у партии есть срок годности и он наступил - списываем всё
        if batch.expiry_date and batch.expiry_date <= current_date:
            return batch.quantity
        return 0
