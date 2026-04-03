import random
import math
from datetime import datetime
from models import SimulationParams, DailyResult, SimulationResponse


def calculate_std_dev(values):
    """Рассчитывает стандартное отклонение для списка значений"""
    if len(values) <= 1:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def run_tomatoes_uniform(params: SimulationParams):
    """Помидоры с равномерным распределением спроса"""

    MIN_STOCK = params.min_stock
    PURCHASE_PRICE = params.purchase_price
    SALE_PRICE = params.sale_price
    total_weeks = params.days

    stock = [MIN_STOCK, 0.0, 0.0]
    total_purchase_cost = MIN_STOCK * PURCHASE_PRICE
    total_revenue = 0.0
    total_spoilage_kg = 0.0
    total_spoilage_money = 0.0

    history = []
    spoilage_rates_10 = []
    spoilage_rates_50 = []
    demand_values = []

    for week in range(1, total_weeks + 1):
        # 1. СПРОС (равномерный) - БЕЗ коэффициентов по дням
        current_demand = random.uniform(150, 200)
        demand_values.append(current_demand)

        initial_stock = stock.copy()

        total_stock = sum(stock)
        after_sales = [0.0, 0.0, 0.0]
        revenue = 0.0
        week_sales = [0.0, 0.0, 0.0]

        if total_stock > 0:
            remaining_demand = current_demand
            temp_stock = stock.copy()

            for age in range(3):
                if temp_stock[age] > 0 and remaining_demand > 0:
                    share = temp_stock[age] / total_stock
                    sold = current_demand * share
                    sold = min(sold, temp_stock[age], remaining_demand)

                    week_sales[age] = sold
                    temp_stock[age] -= sold
                    remaining_demand -= sold
                    revenue += sold * SALE_PRICE

            if remaining_demand > 0:
                for age in range(3):
                    if temp_stock[age] > 0 and remaining_demand > 0:
                        take = min(temp_stock[age], remaining_demand)
                        week_sales[age] += take
                        temp_stock[age] -= take
                        remaining_demand -= take
                        revenue += take * SALE_PRICE
                        if remaining_demand <= 0:
                            break

            after_sales = temp_stock.copy()

        new_stock = [0.0, 0.0, 0.0]
        week_spoilage_kg = 0
        week_spoilage_money = 0

        if after_sales[2] > 0:
            week_spoilage_kg += after_sales[2]
            week_spoilage_money += after_sales[2] * PURCHASE_PRICE

        if after_sales[1] > 0:
            rate_50 = random.uniform(40, 60)
            spoiled = after_sales[1] * (rate_50 / 100)
            new_stock[2] += after_sales[1] - spoiled
            week_spoilage_kg += spoiled
            week_spoilage_money += spoiled * PURCHASE_PRICE
            spoilage_rates_50.append(rate_50)

        if after_sales[0] > 0:
            rate_10 = random.uniform(5, 15)
            spoiled = after_sales[0] * (rate_10 / 100)
            new_stock[1] += after_sales[0] - spoiled
            week_spoilage_kg += spoiled
            week_spoilage_money += spoiled * PURCHASE_PRICE
            spoilage_rates_10.append(rate_10)

        stock = new_stock.copy()
        total_revenue += revenue
        total_spoilage_kg += week_spoilage_kg
        total_spoilage_money += week_spoilage_money

        order = 0
        purchase_cost = 0
        if sum(stock) < MIN_STOCK:
            needed = MIN_STOCK - sum(stock)

            if params.delivery_type == "box" and params.box_size > 0:
                boxes_needed = math.ceil(needed / params.box_size)
                order = boxes_needed * params.box_size
            else:
                order = needed

            stock[0] = order
            total_purchase_cost += order * PURCHASE_PRICE
            purchase_cost = order * PURCHASE_PRICE

        history.append(DailyResult(
            day=week,
            date=f"Неделя {week}",
            demand=float(current_demand),
            start_stock=initial_stock,
            sales=week_sales,
            spoilage=[float(week_spoilage_kg), 0.0, 0.0],
            order=float(order),
            revenue=float(revenue),
            purchase_cost=float(purchase_cost)
        ))

    demand_stats = {
        'mean': sum(demand_values) / len(demand_values),
        'min': min(demand_values),
        'max': max(demand_values)
    }

    spoilage_stats = {
        'week10_mean': sum(spoilage_rates_10) / len(spoilage_rates_10) if spoilage_rates_10 else 0,
        'week10_rates': spoilage_rates_10,
        'week10_std': calculate_std_dev(spoilage_rates_10) if spoilage_rates_10 else 0,
        'week10_min': min(spoilage_rates_10) if spoilage_rates_10 else 0,
        'week10_max': max(spoilage_rates_10) if spoilage_rates_10 else 0,
        'week10_count': len(spoilage_rates_10),

        'week50_mean': sum(spoilage_rates_50) / len(spoilage_rates_50) if spoilage_rates_50 else 0,
        'week50_rates': spoilage_rates_50,
        'week50_std': calculate_std_dev(spoilage_rates_50) if spoilage_rates_50 else 0,
        'week50_min': min(spoilage_rates_50) if spoilage_rates_50 else 0,
        'week50_max': max(spoilage_rates_50) if spoilage_rates_50 else 0,
        'week50_count': len(spoilage_rates_50),
    }

    return SimulationResponse(
        total_revenue=total_revenue,
        total_cost=total_purchase_cost,
        total_spoilage_kg=total_spoilage_kg,
        total_spoilage_money=total_spoilage_money,
        profit=total_revenue - total_purchase_cost,
        daily_history=history,
        demand_stats=demand_stats,
        spoilage_stats=spoilage_stats
    )