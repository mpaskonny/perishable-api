import random
import math
from datetime import datetime, timedelta
from models import SimulationParams, DailyResult, SimulationResponse


def calculate_std_dev(values):
    """Рассчитывает стандартное отклонение для списка значений"""
    if len(values) <= 1:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def run_milk_uniform(params: SimulationParams):
    """Молоко с равномерным распределением спроса и настраиваемым расписанием поставок"""

    # Используем параметры из params
    MIN_STOCK = params.min_stock
    PURCHASE_PRICE = params.purchase_price
    SALE_PRICE = params.sale_price
    SHELF_LIFE_DAYS = params.shelf_life_days
    UTILIZATION_PRICE = params.utilization_price
    FIFO_PERCENT = params.fifo_percent
    LIFO_PERCENT = params.lifo_percent
    total_days = params.days

    start_date = datetime(2026, 2, 1)

    batches = [
        [datetime(2026, 1, 26), 100, datetime(2026, 1, 26) + timedelta(days=SHELF_LIFE_DAYS)],
        [datetime(2026, 1, 29), 60, datetime(2026, 1, 29) + timedelta(days=SHELF_LIFE_DAYS)]
    ]

    total_purchase_cost = 300 * PURCHASE_PRICE
    total_revenue = 0
    total_spoilage_kg = 0
    total_spoilage_money = 0
    total_utilization_cost = 0

    history = []
    fifo_rates = []
    lifo_rates = []
    demand_values = []

    # Коэффициенты спроса по дням недели из params
    weekday_factors = params.weekday_factors if hasattr(params, 'weekday_factors') else [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]

    for day in range(1, total_days + 1):
        current_date = start_date + timedelta(days=day - 1)
        weekday = current_date.weekday()
        weekday_names = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]

        # Проценты покупателей фиксированные
        fifo_percent = FIFO_PERCENT
        lifo_percent = LIFO_PERCENT

        fifo_rates.append(fifo_percent)
        lifo_rates.append(lifo_percent)

        # СПРОС (равномерный) с учетом дня недели
        base_demand = random.randint(20, 30)
        daily_demand = int(round(base_demand * weekday_factors[weekday]))
        daily_demand = max(1, daily_demand)
        demand_values.append(daily_demand)

        day_data = {
            'day': day,
            'date': current_date.strftime('%d.%m'),
            'weekday': weekday_names[weekday],
            'demand': daily_demand,
            'start_stock': sum(b[1] for b in batches),
            'sales': 0,
            'spoilage': 0,
            'utilization_cost': 0,
            'orders': [],
            'revenue': 0,
            'spoilage_money': 0,
            'fifo_sales': 0,
            'lifo_sales': 0
        }

        print(f"\n--- ДЕНЬ {day} ({current_date.strftime('%d.%m')}, {weekday_names[weekday]}) ---")
        print(f"  Базовый спрос: {base_demand}, коэффициент: {weekday_factors[weekday]}, итого: {daily_demand}")

        # 1. ПРОВЕРКА ПРОСРОЧКИ И УТИЛИЗАЦИЯ
        valid_batches = []
        day_spoilage = 0
        day_utilization = 0

        for batch in batches:
            if batch[2] > current_date:
                valid_batches.append(batch)
            else:
                day_spoilage += batch[1]
                total_spoilage_kg += batch[1]
                spoilage_money = batch[1] * PURCHASE_PRICE
                total_spoilage_money += spoilage_money
                util_cost = batch[1] * UTILIZATION_PRICE
                day_utilization += util_cost
                total_utilization_cost += util_cost

                print(f"  ПРОСРОЧЕНО: партия от {batch[0].strftime('%d.%m')} - {batch[1]} пакетов")
                print(f"     Убыток: {spoilage_money} руб + утилизация {util_cost} руб")

        batches = valid_batches
        day_data['spoilage'] = day_spoilage
        day_data['spoilage_money'] = day_spoilage * PURCHASE_PRICE
        day_data['utilization_cost'] = day_utilization

        # 2. ПОСТАВКИ с настраиваемым расписанием
        total_stock = sum(b[1] for b in batches)

        order = 0
        make_delivery = False

        # Определяем, нужно ли делать поставку сегодня
        if params.delivery_frequency > 0:
            # Поставки по периодичности
            if day % params.delivery_frequency == 0 and day > 0:
                make_delivery = True
        elif params.delivery_days:
            # Поставки по конкретным дням недели
            if weekday in params.delivery_days:
                make_delivery = True

        if make_delivery:
            if total_stock < MIN_STOCK:
                needed = MIN_STOCK - total_stock

                if params.delivery_type == "box" and params.box_size > 0:
                    # Поставка коробками: заказ кратен размеру коробки
                    boxes_needed = math.ceil(needed / params.box_size)
                    order = boxes_needed * params.box_size
                    print(
                        f"  РАСЧЕТ: нужно {needed:.0f} пакетов → {boxes_needed} коробок по {params.box_size} = {order} пакетов")
                else:
                    # Штучная поставка
                    order = needed

                expiry_date = current_date + timedelta(days=SHELF_LIFE_DAYS)
                batches.append([current_date, order, expiry_date])
                total_purchase_cost += order * PURCHASE_PRICE
                day_data['orders'].append([current_date.strftime('%d.%m'), order])

                if params.delivery_frequency > 0:
                    schedule_text = f"каждые {params.delivery_frequency} дн"
                else:
                    day_names = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
                    schedule_text = f"по {', '.join([day_names[d] for d in params.delivery_days])}"

                delivery_type_text = "коробками" if params.delivery_type == "box" else "штучно"
                print(
                    f"  ПОСТАВКА ({schedule_text}, {delivery_type_text}): {order} пакетов (срок до {expiry_date.strftime('%d.%m')})")
                total_stock += order

        # 3. ПРОДАЖИ
        if total_stock > 0 and daily_demand > 0:
            remaining_demand = daily_demand

            fifo_batches = sorted(batches, key=lambda x: x[2])
            lifo_batches = sorted(batches, key=lambda x: x[2], reverse=True)

            print(f"  ПРОДАЖИ (спрос {daily_demand} пакетов):")

            fifo_count = int(daily_demand * FIFO_PERCENT / 100)
            lifo_count = daily_demand - fifo_count

            print(f"    FIFO ({FIFO_PERCENT}%): {fifo_count} покупателей")
            print(f"    LIFO ({LIFO_PERCENT}%): {lifo_count} покупателей")

            # FIFO продажи
            fifo_sold = 0
            for batch in fifo_batches:
                if fifo_count <= 0:
                    break
                if batch[1] > 0:
                    take = min(batch[1], fifo_count)
                    batch[1] -= take
                    fifo_count -= take
                    fifo_sold += take
                    remaining_demand -= take
                    print(f"    FIFO: {take} пакетов из партии {batch[0].strftime('%d.%m')}")

            day_data['fifo_sales'] = fifo_sold

            # LIFO продажи
            lifo_sold = 0
            for batch in lifo_batches:
                if lifo_count <= 0:
                    break
                if batch[1] > 0:
                    take = min(batch[1], lifo_count)
                    batch[1] -= take
                    lifo_count -= take
                    lifo_sold += take
                    remaining_demand -= take
                    print(f"    LIFO: {take} пакетов из партии {batch[0].strftime('%d.%m')}")

            day_data['lifo_sales'] = lifo_sold

            total_sold = fifo_sold + lifo_sold
            day_data['sales'] = total_sold
            day_data['revenue'] = total_sold * SALE_PRICE

            if remaining_demand > 0:
                print(f"    Не хватило {remaining_demand} пакетов")

        else:
            print(f"  ПРОДАЖИ: Нет товара (спрос {daily_demand} пакетов)")

        # Удаляем пустые партии
        batches = [b for b in batches if b[1] > 0]

        # Итоги дня
        day_data['end_stock'] = sum(b[1] for b in batches)
        day_data['batches'] = [b.copy() for b in batches]
        day_data['order'] = order
        day_data['purchase_cost'] = order * PURCHASE_PRICE if order else 0.0
        history.append(day_data)

        total_revenue += day_data['revenue']

        print(f"\n  ИТОГИ ДНЯ:")
        print(f"    Продано всего: {day_data['sales']} пакетов на {day_data['revenue']} руб")
        print(f"      FIFO: {day_data['fifo_sales']} пакетов")
        print(f"      LIFO: {day_data['lifo_sales']} пакетов")
        print(f"    Списано просрочки: {day_data['spoilage']} пакетов")
        print(f"    Затраты на утилизацию: {day_data['utilization_cost']} руб")
        print(f"    Остаток: {day_data['end_stock']} пакетов")

        if day_data['end_stock'] > 0:
            print("    Партии в остатке:")
            for b in batches:
                days_left = (b[2] - current_date).days
                print(
                    f"      - от {b[0].strftime('%d.%m')}: {b[1]} пакетов (списание {b[2].strftime('%d.%m')}, осталось {days_left} дн)")

    # Статистика спроса
    demand_stats = {
        'mean': sum(demand_values) / len(demand_values),
        'min': min(demand_values),
        'max': max(demand_values)
    }

    # Статистика покупателей
    spoilage_stats = {
        'fifo_mean': sum(fifo_rates) / len(fifo_rates),
        'fifo_rates': fifo_rates,
        'fifo_std': calculate_std_dev(fifo_rates),
        'fifo_min': min(fifo_rates),
        'fifo_max': max(fifo_rates),
        'fifo_count': len(fifo_rates),

        'lifo_mean': sum(lifo_rates) / len(lifo_rates),
        'lifo_rates': lifo_rates,
        'lifo_std': calculate_std_dev(lifo_rates),
        'lifo_min': min(lifo_rates),
        'lifo_max': max(lifo_rates),
        'lifo_count': len(lifo_rates),
    }

    # Преобразуем историю в объекты DailyResult
    daily_results = []
    for h in history:
        daily_results.append(DailyResult(
            day=h['day'],
            date=h['date'],
            demand=float(h['demand']),
            start_stock=[float(x) for x in h['start_stock']] if isinstance(h['start_stock'], list) else [
                float(h['start_stock'])],
            sales=[float(x) for x in h['sales']] if isinstance(h['sales'], list) else [float(h['sales'])],
            spoilage=[float(x) for x in h['spoilage']] if isinstance(h['spoilage'], list) else [float(h['spoilage'])],
            order=float(h['order']),
            revenue=float(h['revenue']),
            purchase_cost=float(h.get('purchase_cost', 0.0))
        ))

    return SimulationResponse(
        total_revenue=total_revenue,
        total_cost=total_purchase_cost + total_utilization_cost,
        total_spoilage_kg=total_spoilage_kg,
        total_spoilage_money=total_spoilage_money,
        profit=total_revenue - total_purchase_cost - total_utilization_cost,
        daily_history=daily_results,
        demand_stats=demand_stats,
        spoilage_stats=spoilage_stats
    )