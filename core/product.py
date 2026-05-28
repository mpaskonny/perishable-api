from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any


class Batch:
    """Партия товара"""
    def __init__(self, arrival_date: datetime, quantity: float, expiry_date: datetime = None):
        self.arrival_date = arrival_date
        self.quantity = quantity
        self.initial_quantity = quantity
        self.expiry_date = expiry_date


class Product(ABC):
    """Базовый класс продукта с универсальной логикой"""
    
    def __init__(self, 
                 name: str,
                 purchase_price: float,
                 sale_price: float,
                 min_stock: float,
                 demand_strategy,
                 spoilage_strategy,
                 customer_strategy,
                 delivery_strategy,
                 shelf_life_days: int,
                 is_strict: bool = False,
                 weekday_factors: List[float] = None,
                 utilization_price: float = 0.0,
                 delivery_type: str = "unit",
                 box_size: int = 0):
        
        self.name = name
        self.purchase_price = purchase_price
        self.sale_price = sale_price
        self.min_stock = min_stock
        self.shelf_life_days = shelf_life_days
        self.is_strict = is_strict
        self.utilization_price = utilization_price
        
        self.demand = demand_strategy
        self.spoilage = spoilage_strategy
        self.customer = customer_strategy
        self.delivery = delivery_strategy
        
        self.weekday_factors = weekday_factors or [1.0] * 7
        self.delivery_type = delivery_type
        self.box_size = box_size
        
        self.batches: List[Batch] = []
        self.history = []
        
        self.total_revenue = 0.0
        self.total_purchase_cost = 0.0
        self.total_delivery_cost = 0.0
        self.total_spoilage_kg = 0.0
        self.total_spoilage_money = 0.0
        self.total_utilization_cost = 0.0
        
        self.fifo_rates = []
        self.lifo_rates = []
    
    def init_batches(self, start_date: datetime):
        """Инициализирует начальные партии на складе"""
        if self.is_strict:
            self.batches = [
                Batch(start_date - timedelta(days=5), self.min_stock * 0.5,
                      start_date + timedelta(days=self.shelf_life_days - 5)),
                Batch(start_date - timedelta(days=2), self.min_stock * 0.5,
                      start_date + timedelta(days=self.shelf_life_days - 2))
            ]
        else:
            self.batches = [Batch(start_date, self.min_stock)]
    
    def _process_sales(self, demand: float, current_date: datetime, 
                       fifo_percent: float, lifo_percent: float):
        """Обрабатывает продажи с учётом FIFO/LIFO"""
        if not self.batches or demand <= 0:
            return 0, 0, 0, 0, demand
        
        total_stock = sum(b.quantity for b in self.batches)
        if total_stock == 0:
            return 0, 0, 0, 0, demand
        
        if not self.is_strict:
            ratio = min(1.0, demand / total_stock)
            total_sold = 0
            for batch in self.batches:
                sell = batch.quantity * ratio
                batch.quantity -= sell
                total_sold += sell
            
            revenue = total_sold * self.sale_price
            self.total_revenue += revenue
            return total_sold, revenue, 0, 0, max(0, demand - total_sold)
        
        fifo_wanted, lifo_wanted = self.customer.get_sales_distribution(
            demand, fifo_percent, lifo_percent
        )
        
        working_batches = [Batch(b.arrival_date, b.quantity, b.expiry_date) for b in self.batches]
        
        fifo_actual = 0
        lifo_actual = 0
        
        for batch in sorted(working_batches, key=lambda b: b.arrival_date):
            if fifo_actual >= fifo_wanted:
                break
            take = min(batch.quantity, fifo_wanted - fifo_actual)
            batch.quantity -= take
            fifo_actual += take
        
        remaining_for_lifo = min(lifo_wanted, demand - fifo_actual)
        for batch in sorted(working_batches, key=lambda b: b.arrival_date, reverse=True):
            if lifo_actual >= remaining_for_lifo:
                break
            if batch.quantity > 0:
                take = min(batch.quantity, remaining_for_lifo - lifo_actual)
                batch.quantity -= take
                lifo_actual += take
        
        total_sold = fifo_actual + lifo_actual
        unmet_demand = demand - total_sold
        
        if total_sold > 0:
            self.fifo_rates.append(fifo_actual / total_sold * 100)
            self.lifo_rates.append(lifo_actual / total_sold * 100)
        
        self.batches = working_batches
        
        revenue = total_sold * self.sale_price
        self.total_revenue += revenue
        
        return total_sold, revenue, fifo_actual, lifo_actual, unmet_demand
    
    def _process_spoilage(self, current_date: datetime):
        """Обрабатывает порчу товара"""
        spoiled_kg = 0.0
        spoiled_money = 0.0
        
        for batch in self.batches:
            if batch.quantity > 0:
                spoiled = self.spoilage.calculate_spoilage(batch, current_date)
                if spoiled > 0:
                    spoiled = min(spoiled, batch.quantity)
                    batch.quantity -= spoiled
                    spoiled_kg += spoiled
                    spoiled_money += spoiled * self.purchase_price
                    
                    if self.utilization_price > 0:
                        self.total_utilization_cost += spoiled * self.utilization_price
        
        return spoiled_kg, spoiled_money
    
    def _process_delivery(self, day: int, current_date: datetime):
        """Обрабатывает поставку товара"""
        total_stock = sum(b.quantity for b in self.batches)
        
        if self.delivery.should_deliver(day, current_date, total_stock, self.min_stock):
            if total_stock < self.min_stock:
                order = self.delivery.calculate_order(
                    total_stock, 
                    self.min_stock, 
                    self.delivery_type,  
                    self.box_size        
                )
                if order > 0:
                    self._add_batch(current_date, order)
                    self.total_purchase_cost += order * self.purchase_price
                    
                    delivery_cost = self.delivery.calculate_delivery_cost(order)
                    self.total_delivery_cost += delivery_cost
                    
                    return order
        return 0
    
    def _add_batch(self, current_date: datetime, quantity: float):
        """Добавляет новую партию на склад"""
        if self.is_strict:
            expiry_date = current_date + timedelta(days=self.shelf_life_days)
            self.batches.append(Batch(current_date, quantity, expiry_date))
        else:
            self.batches.append(Batch(current_date, quantity))
    
    def _get_age_groups(self, current_date: datetime):
        """Группирует остатки по возрасту"""
        age_groups = {0: 0.0, 1: 0.0, 2: 0.0}
        
        for batch in self.batches:
            age_days = (current_date - batch.arrival_date).days
            if age_days <= 7:
                age_groups[0] += batch.quantity
            elif age_days <= 14:
                age_groups[1] += batch.quantity
            else:
                age_groups[2] += batch.quantity
        
        return age_groups
    
    def _record_day(self, day: int, current_date: datetime, demand: float,
                    sold: float, revenue: float, spoiled_kg: float,
                    spoiled_money: float, order: float, fifo_sold: float, 
                    lifo_sold: float, purchase_cost: float, unmet_demand: float = 0.0):
        """Записывает результаты дня в историю"""
        end_stock = sum(b.quantity for b in self.batches)
        start_stock = end_stock + sold + spoiled_kg
        age_groups = self._get_age_groups(current_date)
        
        batch_stocks = {}
        for i, batch in enumerate(sorted(self.batches, key=lambda b: b.arrival_date), 1):
            if i <= 5:
                batch_stocks[f'batch_{i}_stock'] = round(batch.quantity, 2)
        
        fifo_percent_actual = None
        lifo_percent_actual = None
        if fifo_sold + lifo_sold > 0:
            fifo_percent_actual = round(fifo_sold / (fifo_sold + lifo_sold) * 100, 2)
            lifo_percent_actual = round(lifo_sold / (fifo_sold + lifo_sold) * 100, 2)
        
        utilization_cost = round(spoiled_kg * self.utilization_price, 2) if self.utilization_price > 0 else 0.0
        
        self.history.append({
            'day': day,
            'date': current_date.strftime('%d.%m.%Y'),
            'demand': round(demand, 2),
            'start_stock': round(start_stock, 2),
            'sales': round(sold, 2),
            'spoilage_kg': round(spoiled_kg, 2),
            'spoilage_money': round(spoiled_money, 2),
            'order': round(order, 2),
            'revenue': round(revenue, 2),
            'fifo_sales': round(fifo_sold, 2),
            'lifo_sales': round(lifo_sold, 2),
            'purchase_cost': round(purchase_cost, 2),
            'unmet_demand': round(unmet_demand, 2),
            'end_stock': round(end_stock, 2),
            'stock_week1': round(age_groups[0], 2),
            'stock_week2': round(age_groups[1], 2),
            'stock_week3': round(age_groups[2], 2),
            'fifo_percent': fifo_percent_actual,
            'lifo_percent': lifo_percent_actual,
            'utilization_cost': utilization_cost,
            **batch_stocks
        })
    
    def run(self, days: int, start_date: datetime, 
            fifo_percent: float, lifo_percent: float) -> Dict[str, Any]:
        """Запускает симуляцию на указанное количество дней"""
        
        self.init_batches(start_date)
        self.history = []
        self.fifo_rates = []
        self.lifo_rates = []
        self.total_revenue = 0.0
        
        initial_cost = sum(b.quantity for b in self.batches) * self.purchase_price
        self.total_purchase_cost = initial_cost
        self.total_delivery_cost = 0.0
        self.total_spoilage_kg = 0.0
        self.total_spoilage_money = 0.0
        self.total_utilization_cost = 0.0
        
        for day in range(1, days + 1):
            current_date = start_date + timedelta(days=day - 1)
            demand = self.demand.get_demand(current_date, self.weekday_factors)
            
            order = self._process_delivery(day, current_date)
            purchase_cost = order * self.purchase_price if order else 0.0
            
            sold, revenue, fifo_sold, lifo_sold, unmet_demand = self._process_sales(
                demand, current_date, fifo_percent, lifo_percent
            )
            
            spoiled_kg, spoiled_money = self._process_spoilage(current_date)
            
            self.total_spoilage_kg += spoiled_kg
            self.total_spoilage_money += spoiled_money
            
            self.batches = [b for b in self.batches if b.quantity > 0]
            
            self._record_day(day, current_date, demand, sold, revenue, 
                           spoiled_kg, spoiled_money, order, fifo_sold, 
                           lifo_sold, purchase_cost, unmet_demand)
        
        return self._get_results()
    
    def _get_results(self) -> Dict[str, Any]:
        """Собирает и возвращает итоговые результаты симуляции"""
        buyer_stats = {}
        if self.fifo_rates:
            buyer_stats['fifo_mean'] = sum(self.fifo_rates) / len(self.fifo_rates)
            buyer_stats['fifo_rates'] = self.fifo_rates
            buyer_stats['lifo_mean'] = sum(self.lifo_rates) / len(self.lifo_rates)
            buyer_stats['lifo_rates'] = self.lifo_rates
        
        daily_start_stocks = [day['start_stock'] for day in self.history]
        avg_stock = sum(daily_start_stocks) / len(daily_start_stocks) if daily_start_stocks else 0.0
        max_stock = max(daily_start_stocks) if daily_start_stocks else 0.0
        min_stock = min(daily_start_stocks) if daily_start_stocks else 0.0
        
        return {
            'total_revenue': self.total_revenue,
            'total_cost': self.total_purchase_cost + self.total_delivery_cost + self.total_utilization_cost,
            'total_purchase_cost': self.total_purchase_cost,
            'total_delivery_cost': self.total_delivery_cost,
            'total_utilization_cost': self.total_utilization_cost,
            'total_spoilage_kg': self.total_spoilage_kg,
            'total_spoilage_money': self.total_spoilage_money,
            'profit': self.total_revenue - self.total_purchase_cost - self.total_delivery_cost - self.total_utilization_cost,
            'avg_stock': avg_stock,
            'max_stock': max_stock,
            'min_stock': min_stock,
            'daily_history': self.history,
            'demand_stats': {
                'mean': sum(h['demand'] for h in self.history) / len(self.history),
                'min': min(h['demand'] for h in self.history),
                'max': max(h['demand'] for h in self.history)
            },
            'spoilage_stats': buyer_stats
        }
