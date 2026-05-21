import numpy as np
from core.spoilage import SpoilageStrategy
from typing import Dict, List


class DailySpoilageFromWeekly(SpoilageStrategy):
    """
    Преобразует недельные проценты порчи из БД в ежедневные
    с плавным экспоненциальным ростом и стохастичностью
    """
    
    def __init__(self, weekly_rates: Dict[int, float], sigma: float = 0.5):
        """
        weekly_rates: {1: 10.0, 2: 50.0, 3: 100.0} - процент порчи ЗА НЕДЕЛЮ
        sigma: коэффициент вариативности (отклонение от целевого значения)
        """
        self.weekly_rates = weekly_rates
        self.sigma = sigma
        self.daily_rates = self._compute_daily_rates()
        self.spoilage_records = {week: [] for week in weekly_rates.keys()}
    
    def _compute_daily_rates(self) -> Dict[int, List[float]]:
        """
        Дневные проценты: линейный рост от 0.5x до 1.5x от среднего
        Сумма за неделю точно равна weekly_rate
        """
        daily_rates = {}
        
        for week, weekly_rate in self.weekly_rates.items():
            days_in_week = 7
            avg_daily = weekly_rate / days_in_week
            
            # Линейный рост: день 1 = 0.5 * avg, день 7 = 1.5 * avg
            daily_rates[week] = []
            for day in range(1, days_in_week + 1):
                factor = 0.5 + (day - 1) * (1.0 / 6)
                daily_rates[week].append(avg_daily * factor)
        
        return daily_rates
    
    def _get_daily_rate(self, age_days: int) -> float:
        if age_days <= 0:
            return 0
        
        week = (age_days - 1) // 7 + 1
        day_in_week = (age_days - 1) % 7
        
        if week not in self.daily_rates:
            return 100.0
        
        if day_in_week < len(self.daily_rates[week]):
            rate = self.daily_rates[week][day_in_week]
            # Корректирующий коэффициент для дней 8-21 (2-я и 3-я недели)
            if 8 <= age_days <= 21:
                rate = rate * 1.5   # Увеличиваем на 50%
            return rate
        return self.daily_rates[week][-1]
    def calculate_spoilage(self, batch, current_date):
        """Рассчитывает порчу за ОДИН день"""
        age_days = (current_date - batch.arrival_date).days
        
        if age_days <= 0:
            return 0
        
        # Целевой процент порчи для этого возраста
        target_rate = self._get_daily_rate(age_days)
        
        # Добавляем стохастичность (нормальное распределение)
        if self.sigma > 0 and target_rate > 0:
            # Отклонение не может быть больше самого процента
            actual_rate = np.random.normal(target_rate, target_rate * self.sigma / 100)
            actual_rate = max(0, min(100, actual_rate))
        else:
            actual_rate = target_rate

        # Определяем неделю для статистики
        week = (age_days - 1) // 7 + 1
        week = min(week, max(self.weekly_rates.keys()))
        
        # Сохраняем недельный процент для статистики
        if week in self.spoilage_records:
            # Накопление за неделю (будет суммироваться в методе run)
            if not hasattr(self, '_week_accumulator'):
                self._week_accumulator = {}
                self._week_counter = {}
            
            if week not in self._week_accumulator:
                self._week_accumulator[week] = 0
                self._week_counter[week] = 0
            
            self._week_accumulator[week] += actual_rate
            self._week_counter[week] += 1
            
            # Если неделя закончилась (7 дней)
            if self._week_counter[week] >= 7:
                weekly_total = self._week_accumulator[week]
                self.spoilage_records[week].append(weekly_total)
                self._week_accumulator[week] = 0
                self._week_counter[week] = 0
        
        # Рассчитываем количество испорченного
        spoiled = batch.quantity * (actual_rate / 100)
        
        return spoiled
    
    def get_statistics(self):
        """Возвращает статистику по порче для каждой недели"""
        stats = {}
        for week, rates in self.spoilage_records.items():
            if rates:
                stats[f'week{week}_rates'] = rates
                stats[f'week{week}_mean'] = sum(rates) / len(rates)
        return stats
