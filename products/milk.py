from datetime import datetime, timedelta
from core.product import Product, Batch
from core.spoilage import StrictExpirySpoilage


class Milk(Product):
    """Класс для молока (строгий срок годности)"""
    
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
        """Инициализация начальных партий молока"""
        self.batches = [
            Batch(start_date - timedelta(days=5), 100, start_date + timedelta(days=5)),
            Batch(start_date - timedelta(days=2), 60, start_date + timedelta(days=8))
        ]
    
    def _add_batch(self, current_date: datetime, quantity: float):
        """Добавление новой партии молока"""
        expiry_date = current_date + timedelta(days=self.shelf_life_days)
        self.batches.append(Batch(current_date, quantity, expiry_date))
