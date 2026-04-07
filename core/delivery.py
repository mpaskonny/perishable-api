from abc import ABC, abstractmethod
import math


class DeliveryStrategy(ABC):
    """Абстрактная стратегия поставок"""
    
    @abstractmethod
    def should_deliver(self, day, current_date, total_stock, min_stock):
        """Определяет, нужно ли делать поставку сегодня"""
        pass
    
    @abstractmethod
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        """Рассчитывает размер заказа"""
        pass


class PeriodicDelivery(DeliveryStrategy):
    """Поставки с фиксированной периодичностью (каждые N дней)"""
    
    def __init__(self, frequency):
        self.frequency = frequency
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        return day % self.frequency == 0 and day > 0
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        needed = min_stock - total_stock
        if needed <= 0:
            return 0
        if delivery_type == "box" and box_size > 0:
            boxes_needed = math.ceil(needed / box_size)
            return boxes_needed * box_size
        return needed


class DaysOfWeekDelivery(DeliveryStrategy):
    """Поставки в конкретные дни недели"""
    
    def __init__(self, delivery_days):
        """
        delivery_days: список дней недели (0=пн, 6=вс)
        """
        self.delivery_days = delivery_days
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        return current_date.weekday() in self.delivery_days
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        needed = min_stock - total_stock
        if needed <= 0:
            return 0
        if delivery_type == "box" and box_size > 0:
            boxes_needed = math.ceil(needed / box_size)
            return boxes_needed * box_size
        return needed
