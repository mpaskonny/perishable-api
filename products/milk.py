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
                 weekday_factors=None,
                 delivery_type: str = "unit",
                 box_size: int = 0):
        
        spoilage_strategy = StrictExpirySpoilage()
        
        super().__init__(name, purchase_price, sale_price, min_stock,
                         demand_strategy, spoilage_strategy, customer_strategy,
                         delivery_strategy, weekday_factors, utilization_price,
                         delivery_type, box_size)
        
        self.shelf_life_days = shelf_life_days
    
    def init_batches(self, start_date: datetime):
        """
        Инициализация начальных партий молока
        Создаем партии с разным сроком годности
        """
        self.batches = []
        
        # Партия 1: поступила за 5 дней до старта, срок 10 дней
        batch1_arrival = start_date - timedelta(days=5)
        batch1_expiry = batch1_arrival + timedelta(days=self.shelf_life_days)
        self.batches.append(Batch(batch1_arrival, 100, batch1_expiry))
        
        # Партия 2: поступила за 2 дня до старта, срок 10 дней
        batch2_arrival = start_date - timedelta(days=2)
        batch2_expiry = batch2_arrival + timedelta(days=self.shelf_life_days)
        self.batches.append(Batch(batch2_arrival, 60, batch2_expiry))
    
    def _add_batch(self, current_date: datetime, quantity: float):
        expiry_date = current_date + timedelta(days=self.shelf_life_days)
        self.batches.append(Batch(current_date, quantity, expiry_date))
