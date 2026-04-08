from abc import ABC, abstractmethod
import math


class DeliveryStrategy(ABC):
    @abstractmethod
    def should_deliver(self, day, current_date, total_stock, min_stock):
        pass
    
    @abstractmethod
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        pass


class PeriodicDelivery(DeliveryStrategy):
    """Поставки с фиксированной периодичностью (каждые N дней)"""
    
    def __init__(self, frequency):
        self.frequency = frequency
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        return (day % self.frequency == 0 and day > 0) and total_stock < min_stock
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        needed = min_stock - total_stock
        if needed <= 0:
            return 0
        if delivery_type == "box" and box_size > 0:
            boxes_needed = math.ceil(needed / box_size)
            return boxes_needed * box_size
        return needed


class DaysOfWeekDelivery(DeliveryStrategy):
    def __init__(self, delivery_days):
        self.delivery_days = delivery_days
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        return (current_date.weekday() in self.delivery_days) and total_stock < min_stock
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        needed = min_stock - total_stock
        if needed <= 0:
            return 0
        if delivery_type == "box" and box_size > 0:
            boxes_needed = math.ceil(needed / box_size)
            return boxes_needed * box_size
        return needed
