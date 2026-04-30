from datetime import datetime, timedelta
from core.product import Product, Batch
from core.daily_spoilage_from_weekly import DailySpoilageFromWeekly


class Tomatoes(Product):
    def __init__(self,
                 name: str,
                 purchase_price: float,
                 sale_price: float,
                 min_stock: float,
                 demand_strategy,
                 customer_strategy,
                 delivery_strategy,
                 weekly_rates: dict,      # ← читается из БД, может быть 2,3,4,6 недель
                 sigma: float = 0.5,
                 weekday_factors=None,
                 delivery_type: str = "unit",
                 box_size: int = 0):
        
        spoilage_strategy = DailySpoilageFromWeekly(
            weekly_rates=weekly_rates,
            sigma=sigma
        )
        
        super().__init__(name, purchase_price, sale_price, min_stock,
                         demand_strategy, spoilage_strategy, customer_strategy,
                         delivery_strategy, weekday_factors, 0.0,
                         delivery_type, box_size)
        
        self.weekly_rates = weekly_rates
        self.sigma = sigma
        self.initial_stock = min_stock
    
    def init_batches(self, start_date: datetime):
        self.batches = [Batch(start_date, self.initial_stock)]
    
    def _add_batch(self, current_date: datetime, quantity: float):
        self.batches.append(Batch(current_date, quantity))
    
    def _get_results(self):
        results = super()._get_results()
        spoilage_stats = self.spoilage.get_statistics()
        results['spoilage_stats'].update(spoilage_stats)
        return results
