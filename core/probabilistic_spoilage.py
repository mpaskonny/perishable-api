import random
import numpy as np
from core.spoilage import SpoilageStrategy
from typing import Dict


class ProbabilisticWeeklySpoilage(SpoilageStrategy):
    """
    Вероятностная порча по неделям с нормальным распределением
    """
    
    def __init__(self, weekly_rates: Dict[int, float], weekly_sigmas: Dict[int, float]):
        """
        weekly_rates: {1: 10.0, 2: 50.0, 3: 100.0} - базовый процент порчи для каждой недели
        weekly_sigmas: {1: 0.96, 2: 1.59} - сигма для нормального распределения
        """
        self.weekly_rates = weekly_rates
        self.weekly_sigmas = weekly_sigmas
        self.spoilage_records = {}  # Для сбора статистики по каждой неделе
    
    def calculate_spoilage(self, batch, current_date):
        """
        Рассчитывает порчу для партии на текущую дату
        """
        weeks_old = (current_date - batch.arrival_date).days // 7
        
        # Если товар свежий (меньше недели) - не портится
        if weeks_old <= 0:
            return 0
        
        # Получаем базовый процент порчи для этого возраста
        base_rate = self.weekly_rates.get(weeks_old, 100.0)
        
        # Получаем сигму для этого возраста
        sigma = self.weekly_sigmas.get(weeks_old, 0.0)
        
        # Генерируем фактический процент с нормальным распределением
        if sigma > 0:
            # Используем numpy для более точного нормального распределения
            actual_rate = np.random.normal(base_rate, sigma)
            actual_rate = max(0, min(100, actual_rate))  # Ограничиваем 0-100%
        else:
            actual_rate = base_rate
        
        # Сохраняем для статистики
        if weeks_old not in self.spoilage_records:
            self.spoilage_records[weeks_old] = []
        self.spoilage_records[weeks_old].append(actual_rate)
        
        # Рассчитываем количество испорченного товара
        spoiled = batch.quantity * (actual_rate / 100)
        
        return spoiled
    
    def get_statistics(self):
        """Возвращает статистику по порче для каждой недели"""
        stats = {}
        for week, rates in self.spoilage_records.items():
            stats[f'week{week}_rates'] = rates
            stats[f'week{week}_mean'] = sum(rates) / len(rates) if rates else 0
        return stats
