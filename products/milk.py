from datetime import datetime, timedelta
from core.product import Product, Batch
from core.spoilage import StrictExpirySpoilage


class Milk(Product):
    def __init__(self, 
                 name: str,
                 purchase_price: float,
                 sale_price: float,
                 min_stock: float,
                 demand_strategy,
                 customer_strategy,
                 delivery_strategy,
                 shelf_life_days: int,
                 utilization_price: float = 5.0,
                 weekday_factors=None):
        
        spoilage_strategy = StrictExpirySpoilage()
        
        super().__init__(name, purchase_price, sale_price, min_stock,
                         demand_strategy, spoilage_strategy, customer_strategy,
                         delivery_strategy, weekday_factors, utilization_price)
        
        self.shelf_life_days = shelf_life_days
    
    def init_batches(self, start_date: datetime):
        self.batches = [
        Batch(datetime(2026, 1, 26), 100, datetime(2026, 2, 5)),
        Batch(datetime(2026, 1, 29), 60, datetime(2026, 2, 8))
    ]
    
    def _add_batch(self, current_date: datetime, quantity: float):
        expiry_date = current_date + timedelta(days=self.shelf_life_days)
        self.batches.append(Batch(current_date, quantity, expiry_date))
