from abc import ABC, abstractmethod
import math
from typing import List


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

class SSPolicyDelivery(DeliveryStrategy):
    """(s, S)-стратегия управления запасами"""
    
    def __init__(self, reorder_point: float, max_stock: float, 
                 cost_type: str = "fixed", fixed_cost: float = 0.0, 
                 rate_cost: float = 0.0, delivery_type: str = "unit", 
                 box_size: int = 0):
        self.reorder_point = reorder_point    # s
        self.max_stock = max_stock            # S
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
        self.delivery_type = delivery_type
        self.box_size = box_size
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        """Проверяем, нужно ли делать заказ (остаток ниже точки заказа)"""
        return total_stock < self.reorder_point
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        """Рассчитываем размер заказа до уровня max_stock"""
        needed = self.max_stock - total_stock
        if needed <= 0:
            return 0
        
        # Учитываем тип поставки (штучно или коробками)
        actual_delivery_type = delivery_type if delivery_type else self.delivery_type
        actual_box_size = box_size if box_size else self.box_size
        
        if actual_delivery_type == "box" and actual_box_size > 0:
            boxes_needed = int(math.ceil(needed / actual_box_size))
            return boxes_needed * actual_box_size
        return needed
    
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        """Рассчитываем стоимость доставки"""
        if self.cost_type == "fixed":
            return self.fixed_cost
        elif self.cost_type == "rate":
            return self.rate_cost * order_quantity
        elif self.cost_type == "combined":
            return self.fixed_cost + self.rate_cost * order_quantity
        else:
            return 0.0

class FixedQuantityDelivery(DeliveryStrategy):
    """Стратегия с фиксированным объёмом поставки (R, Q)"""
    
    def __init__(self, frequency: int, fixed_quantity: float,
                 cost_type: str = "fixed", fixed_cost: float = 0.0, 
                 rate_cost: float = 0.0, delivery_days: List[int] = None):
        """
        frequency: периодичность поставок (дней)
        fixed_quantity: фиксированный объём заказа
        delivery_days: если указаны, то поставки по дням недели (игнорирует frequency)
        """
        self.frequency = frequency
        self.fixed_quantity = fixed_quantity
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
        self.delivery_days = delivery_days or []
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        should = False
        if self.delivery_days:
            should = current_date.weekday() in self.delivery_days
        else:
            should = day % self.frequency == 0 and day > 0
        return should
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        # Всегда заказываем фиксированное количество
        return self.fixed_quantity
    
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        if self.cost_type == "fixed":
            return self.fixed_cost
        elif self.cost_type == "rate":
            return self.rate_cost * order_quantity
        elif self.cost_type == "combined":
            return self.fixed_cost + self.rate_cost * order_quantity
        else:
            return 0.0

class SQuantityDelivery(DeliveryStrategy):
    """(s, Q)-стратегия управления запасами - точка заказа + фиксированный объём"""
    
    def __init__(self, reorder_point: float, fixed_quantity: float,
                 cost_type: str = "fixed", fixed_cost: float = 0.0, 
                 rate_cost: float = 0.0, delivery_type: str = "unit", 
                 box_size: int = 0):
        """
        reorder_point: точка заказа (s) - при остатке ниже этого уровня делаем заказ
        fixed_quantity: фиксированный объём заказа (Q)
        """
        self.reorder_point = reorder_point    # s
        self.fixed_quantity = fixed_quantity  # Q
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
        self.delivery_type = delivery_type
        self.box_size = box_size
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        """Проверяем, нужно ли делать заказ (остаток ниже точки заказа)"""
        return total_stock < self.reorder_point
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        """Рассчитываем размер заказа - всегда фиксированный объём Q"""
        # Проверяем, что заказ действительно нужен
        if total_stock >= self.reorder_point:
            return 0
        
        order_qty = self.fixed_quantity
        
        # Учитываем тип поставки (коробками)
        actual_delivery_type = delivery_type if delivery_type else self.delivery_type
        actual_box_size = box_size if box_size else self.box_size
        
        if actual_delivery_type == "box" and actual_box_size > 0:
            boxes_needed = int(math.ceil(order_qty / actual_box_size))
            return boxes_needed * actual_box_size
        return order_qty
    
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        """Рассчитываем стоимость доставки"""
        if self.cost_type == "fixed":
            return self.fixed_cost
        elif self.cost_type == "rate":
            return self.rate_cost * order_quantity
        elif self.cost_type == "combined":
            return self.fixed_cost + self.rate_cost * order_quantity
        else:
            return 0.0
