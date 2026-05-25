from abc import ABC, abstractmethod
import random


class CustomerStrategy(ABC):
    """Абстрактная стратегия поведения покупателей"""
    
    @abstractmethod
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        pass


class FixedCustomerStrategy(CustomerStrategy):
    """Фиксированное распределение (для равномерного закона)"""
    
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        fifo_count = int(total_demand * fifo_percent / 100)
        lifo_count = total_demand - fifo_count
        return fifo_count, lifo_count


class NormalCustomerStrategy(CustomerStrategy):
    """Нормальное распределение с сигмой (для нормального закона)"""
    
    def __init__(self, sigma):
        self.sigma = sigma
    
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        r = [random.random() for _ in range(12)]
        deviation = sum(r) - 6
        actual_fifo = self.sigma * deviation + fifo_percent
        actual_fifo = max(0, min(100, actual_fifo))
        
        fifo_count = int(total_demand * actual_fifo / 100)
        lifo_count = total_demand - fifo_count
        return fifo_count, lifo_count


class NormalCustomerStrategyFromExcel(CustomerStrategy):
    """Нормальное распределение с сигмой из Excel"""
    
    def __init__(self, sigma_fifo: float, sigma_lifo: float):
        self.sigma_fifo = sigma_fifo
        self.sigma_lifo = sigma_lifo
    
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        # Генерируем фактический процент FIFO
        r = [random.random() for _ in range(12)]
        deviation = sum(r) - 6
        actual_fifo = self.sigma_fifo * deviation + fifo_percent
        actual_fifo = max(0, min(100, actual_fifo))
        
        fifo_count = int(round(total_demand * actual_fifo / 100))
        lifo_count = total_demand - fifo_count
        
        # Корректировка, чтобы не было отрицательных значений
        if fifo_count < 0:
            fifo_count = 0
            lifo_count = total_demand
        if lifo_count < 0:
            lifo_count = 0
            fifo_count = total_demand
        
        return fifo_count, lifo_count
