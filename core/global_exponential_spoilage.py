import numpy as np
from scipy.optimize import curve_fit
from core.spoilage import SpoilageStrategy
from typing import Dict, List


class GlobalExponentialSpoilage(SpoilageStrategy):
    """
    Глобальная экспоненциальная порча (одна кривая на весь срок)
    Без скачков между неделями
    """
    
    def __init__(self, weekly_rates: Dict[int, float], sigma: float = 0.5):
        """
        weekly_rates: {1: 1, 2: 30, 3: 90, 4: 100} - процент порчи за неделю
        """
        self.weekly_rates = weekly_rates
        self.sigma = sigma
        self.a, self.b, self.c = self._fit_curve()
        self.spoilage_records = {week: [] for week in weekly_rates.keys()}
        self._week_accumulator = {}
        self._week_counter = {}
    
    def _model(self, t, a, b, c):
        """
        Экспоненциальная модель: S(t) = a * (1 - exp(-b * t)) + c
        t - возраст в днях
        S(t) - накопленный процент порчи (0..100)
        """
        return a * (1 - np.exp(-b * t)) + c
    
    def _fit_curve(self):
        """Подбирает параметры a, b, c по точкам из БД"""
        weeks = sorted(self.weekly_rates.keys())
        days = np.array([w * 7 for w in weeks])
        targets = np.array([self.weekly_rates[w] for w in weeks])
        
        # Начальные приближения
        p0 = [100, 0.05, 0]
        
        # Ограничения: a >= 0, b >= 0, c >= 0
        bounds = ([0, 0, 0], [200, 1, 100])
        
        try:
            params, _ = curve_fit(self._model, days, targets, p0=p0, bounds=bounds, maxfev=5000)
            a, b, c = params
        except:
            # Если подбор не удался, используем значения по умолчанию
            a = 100
            b = 0.05
            c = 0
        
        return a, b, c
    
    def _get_cumulative_rate(self, age_days: int) -> float:
        """Накопленный процент порчи к указанному дню"""
        if age_days <= 0:
            return 0
        
        result = self._model(age_days, self.a, self.b, self.c)
        return min(100, max(0, result))
    
    def _get_daily_rate(self, age_days: int) -> float:
        """Процент порчи за день от начального количества"""
        if age_days <= 0:
            return 0
        
        cum_today = self._get_cumulative_rate(age_days)
        cum_yesterday = self._get_cumulative_rate(age_days - 1)
        
        daily = cum_today - cum_yesterday
        return max(0, min(100, daily))
    
    def calculate_spoilage(self, batch, current_date):
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        target_rate = self._get_daily_rate(age_days)
        
        # Стохастичность
        if self.sigma > 0 and target_rate > 0:
            actual_rate = np.random.normal(target_rate, target_rate * self.sigma / 100)
            actual_rate = max(0, min(100, actual_rate))
        else:
            actual_rate = target_rate
        
        # Статистика по неделям
        week = (age_days - 1) // 7 + 1
        week = min(week, max(self.weekly_rates.keys()))
        
        if week not in self._week_accumulator:
            self._week_accumulator[week] = 0
            self._week_counter[week] = 0
        
        self._week_accumulator[week] += actual_rate
        self._week_counter[week] += 1
        
        if self._week_counter[week] >= 7:
            weekly_total = self._week_accumulator[week]
            self.spoilage_records[week].append(weekly_total)
            self._week_accumulator[week] = 0
            self._week_counter[week] = 0
        
        # Порча от начального количества партии
        spoiled = batch.initial_quantity * (actual_rate / 100)
        batch.quantity -= spoiled
        
        return spoiled
    
    def get_statistics(self):
        stats = {}
        for week, rates in self.spoilage_records.items():
            if rates:
                stats[f'week{week}_rates'] = rates
                stats[f'week{week}_mean'] = sum(rates) / len(rates)
        return stats