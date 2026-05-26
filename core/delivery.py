from abc import ABC, abstractmethod
import math


class DeliveryStrategy(ABC):
    @abstractmethod
    def should_deliver(self, day, current_date, total_stock, min_stock):
        pass
    
    @abstractmethod
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        pass
    
    @abstractmethod
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        """Рассчитывает стоимость доставки"""
        pass


class PeriodicDelivery(DeliveryStrategy):
    """Поставки с фиксированной периодичностью"""
    
    def __init__(self, frequency, cost_type="fixed", fixed_cost=0.0, rate_cost=0.0):
        self.frequency = frequency
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
    
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
    
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        if self.cost_type == "fixed":
            return self.fixed_cost
        elif self.cost_type == "rate":
            return self.rate_cost * order_quantity
        else:  # combined
            return self.fixed_cost + self.rate_cost * order_quantity


class DaysOfWeekDelivery(DeliveryStrategy):
    """Поставки по конкретным дням недели"""
    
    def __init__(self, delivery_days, cost_type="fixed", fixed_cost=0.0, rate_cost=0.0):
        self.delivery_days = delivery_days
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
    
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
    
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        if self.cost_type == "fixed":
            return self.fixed_cost
        elif self.cost_type == "rate":
            return self.rate_cost * order_quantity
        else:  # combined
            return self.fixed_cost + self.rate_cost * order_quantity
