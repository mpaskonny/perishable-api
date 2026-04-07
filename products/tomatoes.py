from datetime import datetime, timedelta
import random
from core.product import Product, Batch
from core.spoilage import WeeklySpoilage


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
                 weekday_factors=None):
        
        spoilage_strategy = WeeklySpoilage(week_rates, week_sigmas)
        
        super().__init__(name, purchase_price, sale_price, min_stock,
                         demand_strategy, spoilage_strategy, customer_strategy,
                         delivery_strategy, weekday_factors)
        
        self.week_rates = week_rates
        self.week_sigmas = week_sigmas
        self.week10_rates = []
        self.week50_rates = []
    
    def init_batches(self, start_date: datetime):
        self.batches = [
            Batch(start_date - timedelta(days=2), 150),
            Batch(start_date - timedelta(days=1), 150)
        ]
    
    def _add_batch(self, current_date: datetime, quantity: float):
        self.batches.append(Batch(current_date, quantity))
    
    def _process_spoilage(self, current_date: datetime):
        spoiled_kg = 0.0
        spoiled_money = 0.0
        
        age_groups = {0: 0.0, 1: 0.0, 2: 0.0}
        
        for batch in self.batches:
            age_weeks = (current_date - batch.arrival_date).days // 7
            if age_weeks >= 2:
                age_groups[2] += batch.quantity
            else:
                age_groups[age_weeks] += batch.quantity
        
        self.batches = []
        
        if age_groups[2] > 0:
            spoiled_kg += age_groups[2]
            spoiled_money += age_groups[2] * self.purchase_price
        
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
            
            spoiled_kg += spoiled
            spoiled_money += spoiled * self.purchase_price
            
            self.week50_rates.append(actual_rate)
            
            if remaining > 0:
                self.batches.append(Batch(current_date, remaining))
        
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
            
            spoiled_kg += spoiled
            spoiled_money += spoiled * self.purchase_price
            
            self.week10_rates.append(actual_rate)
            
            if remaining > 0:
                self.batches.append(Batch(current_date, remaining))
        
        if self.utilization_price > 0:
            self.total_utilization_cost += spoiled_kg * self.utilization_price
        
        return spoiled_kg, spoiled_money
    
    def _get_results(self):
        results = super()._get_results()
        results['spoilage_stats']['week10_rates'] = self.week10_rates
        results['spoilage_stats']['week10_mean'] = sum(self.week10_rates) / len(self.week10_rates) if self.week10_rates else 0
        results['spoilage_stats']['week50_rates'] = self.week50_rates
        results['spoilage_stats']['week50_mean'] = sum(self.week50_rates) / len(self.week50_rates) if self.week50_rates else 0
        return results