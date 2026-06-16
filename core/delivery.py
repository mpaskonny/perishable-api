"""
delivery.py - Стратегии поставок

Реализует 4 стратегии управления запасами:
- (R, S): периодическая до целевого уровня
- (R, Q): периодическая с фикс. объёмом
- (s, S): двухуровневая (точка заказа)
- (s, Q): двухуровневая с фикс. объёмом

Плюс возможность заказывать коробками (box_size) и настраивать стоимость доставки.
"""

from abc import ABC, abstractmethod
import math
from typing import List


class DeliveryStrategy(ABC):
    """Базовый класс для всех стратегий поставок"""
    
    @abstractmethod
    def should_deliver(self, day, current_date, total_stock, min_stock):
        """Проверяет, нужно ли делать заказ сегодня"""
        pass
    
    @abstractmethod
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        """Рассчитывает размер заказа"""
        pass
    
    @abstractmethod
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        """Рассчитывает стоимость доставки (фикс/тариф/комби)"""
        pass


class PeriodicDelivery(DeliveryStrategy):
    """Поставки с фиксированной периодичностью (R, S)"""
    
    def __init__(self, frequency, cost_type="fixed", fixed_cost=0.0, rate_cost=0.0):
        self.frequency = frequency      # раз в N дней
        self.cost_type = cost_type      # fixed / rate / combined
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        # Заказ делаем, если день кратен частоте И остаток ниже целевого уровня
        return (day % self.frequency == 0 and day > 0) and total_stock < min_stock
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        needed = min_stock - total_stock
        if needed <= 0:
            return 0
        # Если заказываем коробками - округляем вверх до размера коробки
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
    """Поставки по конкретным дням недели (тоже R,S, но с гибким расписанием)"""
    
    def __init__(self, delivery_days, cost_type="fixed", fixed_cost=0.0, rate_cost=0.0):
        self.delivery_days = delivery_days  # список дней, например [0,3] для Пн и Чт
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        # Проверяем, сегодня ли день поставки
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
        else:
            return self.fixed_cost + self.rate_cost * order_quantity


class SSPolicyDelivery(DeliveryStrategy):
    """(s, S)-стратегия: заказ при остатке ниже s, пополняем до S"""
    
    def __init__(self, reorder_point: float, max_stock: float, 
                 cost_type: str = "fixed", fixed_cost: float = 0.0, 
                 rate_cost: float = 0.0, delivery_type: str = "unit", 
                 box_size: int = 0):
        self.reorder_point = reorder_point    # s - точка заказа
        self.max_stock = max_stock            # S - максимальный запас
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
        self.delivery_type = delivery_type
        self.box_size = box_size
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        # Заказ, когда остаток упал ниже порога
        return total_stock < self.reorder_point
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        needed = self.max_stock - total_stock
        if needed <= 0:
            return 0
        
        actual_delivery_type = delivery_type if delivery_type else self.delivery_type
        actual_box_size = box_size if box_size else self.box_size
        
        if actual_delivery_type == "box" and actual_box_size > 0:
            boxes_needed = int(math.ceil(needed / actual_box_size))
            return boxes_needed * actual_box_size
        return needed
    
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        if self.cost_type == "fixed":
            return self.fixed_cost
        elif self.cost_type == "rate":
            return self.rate_cost * order_quantity
        elif self.cost_type == "combined":
            return self.fixed_cost + self.rate_cost * order_quantity
        else:
            return 0.0


class FixedQuantityDelivery(DeliveryStrategy):
    """(R, Q)-стратегия: заказ по расписанию, всегда фиксированный объём"""
    
    def __init__(self, frequency: int, fixed_quantity: float,
                 cost_type: str = "fixed", fixed_cost: float = 0.0, 
                 rate_cost: float = 0.0, delivery_days: List[int] = None):
        self.frequency = frequency          # раз в N дней
        self.fixed_quantity = fixed_quantity  # Q - фиксированный объём
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
        self.delivery_days = delivery_days or []  # если указаны дни - игнорируем frequency
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        should = False
        if self.delivery_days:
            should = current_date.weekday() in self.delivery_days
        else:
            should = day % self.frequency == 0 and day > 0
        return should
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        # Всегда заказываем одно и то же количество
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
    """(s, Q)-стратегия: заказ при остатке ниже s, всегда фиксированный объём Q"""
    
    def __init__(self, reorder_point: float, fixed_quantity: float,
                 cost_type: str = "fixed", fixed_cost: float = 0.0, 
                 rate_cost: float = 0.0, delivery_type: str = "unit", 
                 box_size: int = 0):
        self.reorder_point = reorder_point    # s - точка заказа
        self.fixed_quantity = fixed_quantity  # Q - фиксированный объём
        self.cost_type = cost_type
        self.fixed_cost = fixed_cost
        self.rate_cost = rate_cost
        self.delivery_type = delivery_type
        self.box_size = box_size
    
    def should_deliver(self, day, current_date, total_stock, min_stock):
        return total_stock < self.reorder_point
    
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        # Если остаток ещё не ниже порога - не заказываем
        if total_stock >= self.reorder_point:
            return 0
        
        order_qty = self.fixed_quantity
        
        actual_delivery_type = delivery_type if delivery_type else self.delivery_type
        actual_box_size = box_size if box_size else self.box_size
        
        if actual_delivery_type == "box" and actual_box_size > 0:
            boxes_needed = int(math.ceil(order_qty / actual_box_size))
            return boxes_needed * actual_box_size
        return order_qty
    
    def calculate_delivery_cost(self, order_quantity: float) -> float:
        if self.cost_type == "fixed":
            return self.fixed_cost
        elif self.cost_type == "rate":
            return self.rate_cost * order_quantity
        elif self.cost_type == "combined":
            return self.fixed_cost + self.rate_cost * order_quantity
        else:
            return 0.0
