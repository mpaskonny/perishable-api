from datetime import datetime, timedelta
from core.product import Product, Batch
from core.smooth_spoilage import SmoothDailySpoilage


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
                 box_size: int = 0,
                 interpolation: str = "exponential"):
        
        spoilage_strategy = SmoothDailySpoilage(
            weekly_rates=week_rates,
            weekly_sigmas=week_sigmas,
            interpolation=interpolation
        )
        
        super().__init__(name, purchase_price, sale_price, min_stock,
                         demand_strategy, spoilage_strategy, customer_strategy,
                         delivery_strategy, weekday_factors, 0.0,
                         delivery_type, box_size)
        
        self.week_rates = week_rates
        self.week_sigmas = week_sigmas
        self.initial_stock = min_stock
    
    def init_batches(self, start_date: datetime):
        self.batches = [
            Batch(start_date, self.initial_stock)
        ]
    
    def _add_batch(self, current_date: datetime, quantity: float):
        self.batches.append(Batch(current_date, quantity))
    
    def _get_results(self):
        results = super()._get_results()
        spoilage_stats = self.spoilage.get_statistics()
        results['spoilage_stats'].update(spoilage_stats)
        return results
