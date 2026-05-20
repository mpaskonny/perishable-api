import numpy as np
from core.spoilage import SpoilageStrategy
from typing import Dict, List


class ExponentialSpoilage(SpoilageStrategy):
    """
    Кусочно-экспоненциальная порча
    Между каждой парой недельных точек строит свою экспоненту
    """
    
    def __init__(self, weekly_rates: Dict[int, float], sigma: float = 0.5):
        """
        weekly_rates: {1: 10, 2: 50, 3: 100} - процент порчи за неделю
        """
        self.weekly_rates = weekly_rates
        self.sigma = sigma
        self.segments = self._build_segments()
        self.spoilage_records = {week: [] for week in weekly_rates.keys()}
        self._week_accumulator = {}
        self._week_counter = {}
    
    def _build_segments(self):
        """Строит экспоненциальные сегменты с ускоряющимся ростом"""
        weeks = sorted(self.weekly_rates.keys())
        segments = {}
        
        for i in range(len(weeks) - 1):
            week1 = weeks[i]
            week2 = weeks[i + 1]
            
            rate1 = self.weekly_rates[week1]
            rate2 = self.weekly_rates[week2]
            
            days1 = week1 * 7
            days2 = week2 * 7
            
            # Нужно найти такой k, чтобы cumulative(days2) = rate2
            # cumulative(t) = rate1 + a * (exp(k * (t - days1)) - 1)
            # При t = days2: rate2 = rate1 + a * (exp(k * 7) - 1)
            
            # Выбираем k (чем больше k, тем быстрее ускорение)
            k = 0.15  # базовый коэффициент ускорения
            a = (rate2 - rate1) / (np.exp(k * 7) - 1)
            
            segments[week1] = {
                'start_day': days1,
                'end_day': days2,
                'start_rate': rate1,
                'end_rate': rate2,
                'k': k,
                'a': a
            }
        
        return segments

    def _get_cumulative_rate(self, age_days: int) -> float:
        """Накопленный процент порчи (ускоряющийся рост)"""
        if age_days <= 0:
            return 0
        
        weeks = sorted(self.weekly_rates.keys())
        
        if age_days >= weeks[-1] * 7:
            return 100.0
        
        for week, seg in self.segments.items():
            if seg['start_day'] <= age_days <= seg['end_day']:
                t = age_days - seg['start_day']
                increase = seg['a'] * (np.exp(seg['k'] * t) - 1)
                return seg['start_rate'] + increase
        
        return 0
    
    def _get_daily_rate(self, age_days: int) -> float:
        """Возвращает процент порчи за день от начального количества"""
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