from datetime import datetime, timedelta
import random
from core.product import Product, Batch
from core.probabilistic_spoilage import ProbabilisticWeeklySpoilage

class Tomatoes(Product):
    def __init__(self,
                 name: str,
                 purchase_price: float,
                 sale_price: float,
                 min_stock: float,
                 demand_strategy,
                 customer_strategy,
                 delivery_strategy,
                 week_rates: dict,
                 week_sigmas: dict,
                 weekday_factors=None,
                 delivery_type: str = "unit",
                 box_size: int = 0):
        
        spoilage_strategy = ProbabilisticWeeklySpoilage(week_rates, week_sigmas)
        
        super().__init__(name, purchase_price, sale_price, min_stock,
                         demand_strategy, spoilage_strategy, customer_strategy,
                         delivery_strategy, weekday_factors, 0.0,
                         delivery_type, box_size)
        
        self.week_rates = week_rates
        self.week_sigmas = week_sigmas
        self.week10_rates = []
        self.week50_rates = []

    
    def init_batches(self, start_date: datetime):
        """Инициализация начальных партий"""
        self.batches = [
            Batch(start_date - timedelta(days=2), 150),
            Batch(start_date - timedelta(days=1), 150)
        ]
    
    def _add_batch(self, current_date: datetime, quantity: float):
        """Добавление новой партии"""
        self.batches.append(Batch(current_date, quantity))
    
    
    def _get_results(self):
        """Расширяем результаты статистикой порчи"""
        results = super()._get_results()
        
        # Добавляем статистику из стратегии порчи
        spoilage_stats = self.spoilage.get_statistics()
        results['spoilage_stats'].update(spoilage_stats)
        
        return results

    def _process_spoilage(self, current_date: datetime):
        """Временная отладочная версия"""
        print(f"\n[DEBUG] Processing spoilage for {current_date}")
        print(f"[DEBUG] Batches before: {[(b.arrival_date, b.quantity) for b in self.batches]}")
        
        spoiled_kg = 0.0
        spoiled_money = 0.0
        
        age_groups = {0: 0.0, 1: 0.0, 2: 0.0}
        
        for batch in self.batches:
            age_weeks = (current_date - batch.arrival_date).days // 7
            print(f"[DEBUG] Batch age: {age_weeks} weeks, quantity: {batch.quantity}")
            if age_weeks >= 2:
                age_groups[2] += batch.quantity
            else:
                age_groups[age_weeks] += batch.quantity
        
        print(f"[DEBUG] Age groups: {age_groups}")
        
        self.batches = []
        
        # Старше 2 недель - 100% порча
        if age_groups[2] > 0:
            print(f"[DEBUG] Spoiling 2+ weeks: {age_groups[2]} kg")
            spoiled_kg += age_groups[2]
            spoiled_money += age_groups[2] * self.purchase_price
        
        # 2-я неделя (возраст 1 неделя) - 50% порча
        if age_groups[1] > 0:
            rate = 50.0
            sigma = self.week_sigmas.get(2, 1.59)
            
            if sigma > 0:
                r = [random.random() for _ in range(12)]
                deviation = sum(r) - 6
                actual_rate = sigma * deviation + rate
                actual_rate = max(0, min(100, actual_rate))
            else:
                actual_rate = rate
            
            spoiled = age_groups[1] * (actual_rate / 100)
            remaining = age_groups[1] - spoiled
            
            print(f"[DEBUG] Week 2: rate={actual_rate:.2f}%, spoiled={spoiled:.2f}, remaining={remaining:.2f}")
            
            spoiled_kg += spoiled
            spoiled_money += spoiled * self.purchase_price
            
            self.week50_rates.append(actual_rate)
            
            if remaining > 0:
                self.batches.append(Batch(current_date, remaining))
        
        # 1-я неделя (возраст 0 недель) - 10% порча
        if age_groups[0] > 0:
            rate = 10.0
            sigma = self.week_sigmas.get(1, 0.96)
            
            if sigma > 0:
                r = [random.random() for _ in range(12)]
                deviation = sum(r) - 6
                actual_rate = sigma * deviation + rate
                actual_rate = max(0, min(100, actual_rate))
            else:
                actual_rate = rate
            
            spoiled = age_groups[0] * (actual_rate / 100)
            remaining = age_groups[0] - spoiled
            
            print(f"[DEBUG] Week 1: rate={actual_rate:.2f}%, spoiled={spoiled:.2f}, remaining={remaining:.2f}")
            
            spoiled_kg += spoiled
            spoiled_money += spoiled * self.purchase_price
            
            self.week10_rates.append(actual_rate)
            
            if remaining > 0:
                self.batches.append(Batch(current_date, remaining))
        
        print(f"[DEBUG] Total spoiled today: {spoiled_kg}")
        print(f"[DEBUG] Batches after: {[(b.arrival_date, b.quantity) for b in self.batches]}")
        
        return spoiled_kg, spoiled_money
