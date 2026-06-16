"""
customer.py - Стратегии поведения покупателей

Определяет, как распределяется спрос между FIFO и LIFO покупателями.
Для нормального закона спроса используется случайное отклонение 
(метод 12 случайных чисел для аппроксимации нормального распределения).
Для загрузки сигм из Excel отдельный класс.
"""

from abc import ABC, abstractmethod
import random


class CustomerStrategy(ABC):
    """Абстрактная стратегия поведения покупателей"""
    
    @abstractmethod
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        """
        Возвращает (fifo_количество, lifo_количество)
        total_demand - общий спрос за день
        fifo_percent - заданный процент FIFO
        lifo_percent - обычно = 100 - fifo_percent
        """
        pass


class FixedCustomerStrategy(CustomerStrategy):
    """Фиксированное распределение - без случайных отклонений.
       Используется для равномерного закона спроса."""
    
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        # Прямой расчёт: сколько единиц уйдёт по FIFO, сколько по LIFO
        fifo_count = int(total_demand * fifo_percent / 100)
        lifo_count = total_demand - fifo_count
        return fifo_count, lifo_count


class NormalCustomerStrategy(CustomerStrategy):
    """Нормальное распределение с теоретической сигмой.
       Используется, когда нет эмпирических данных из Excel."""
    
    def __init__(self, sigma):
        self.sigma = sigma
    
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        # Метод 12 случайных чисел для генерации нормального распределения
        # (центральная предельная теорема: сумма 12 равномерных даёт нормальное)
        r = [random.random() for _ in range(12)]
        deviation = sum(r) - 6  # приводим к мат. ожиданию 0
        
        # Добавляем случайное отклонение к заданному проценту FIFO
        actual_fifo = self.sigma * deviation + fifo_percent
        actual_fifo = max(0, min(100, actual_fifo))  # не выходим за 0-100%
        
        fifo_count = int(total_demand * actual_fifo / 100)
        lifo_count = total_demand - fifo_count
        return fifo_count, lifo_count


class NormalCustomerStrategyFromExcel(CustomerStrategy):
    """Нормальное распределение с сигмами, загруженными из Excel.
       Самый реалистичный вариант - сигмы получены из реальных данных.
       sigma_fifo - для отклонения процента FIFO
       sigma_lifo - для отклонения процента LIFO (зеркально)"""
    
    def __init__(self, sigma_fifo: float, sigma_lifo: float):
        self.sigma_fifo = sigma_fifo
        self.sigma_lifo = sigma_lifo
    
    def get_sales_distribution(self, total_demand, fifo_percent, lifo_percent):
        # Генерируем фактический процент FIFO с отклонением
        r = [random.random() for _ in range(12)]
        deviation = sum(r) - 6
        actual_fifo = self.sigma_fifo * deviation + fifo_percent
        actual_fifo = max(0, min(100, actual_fifo))
        
        fifo_count = int(round(total_demand * actual_fifo / 100))
        lifo_count = total_demand - fifo_count
        
        # Страховка от отрицательных значений (редко, но бывает при округлении)
        if fifo_count < 0:
            fifo_count = 0
            lifo_count = total_demand
        if lifo_count < 0:
            lifo_count = 0
            fifo_count = total_demand
        
        return fifo_count, lifo_count
