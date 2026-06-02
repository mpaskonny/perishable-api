"""
Тест для диагностики проблем с поставками по дням недели
Запуск: python test_delivery_debug.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from core.demand import UniformDemand
from core.customer import FixedCustomerStrategy
from core.delivery import PeriodicDelivery, DaysOfWeekDelivery, FixedQuantityDelivery, SSPolicyDelivery, SQuantityDelivery
from core.simple_spoilage import LinearSpoilage
from core.product import Product


def print_separator(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_delivery_strategy(strategy_name, delivery_strategy, schedule_desc, days=14):
    """Тестирует конкретную стратегию поставок"""
    print(f"\n📦 Тестируем: {strategy_name}")
    print(f"   Расписание: {schedule_desc}")
    
    try:
        product = Product(
            name="Тестовый товар",
            purchase_price=100.0,
            sale_price=150.0,
            min_stock=200.0,
            demand_strategy=UniformDemand(80, 120),
            spoilage_strategy=LinearSpoilage(30),
            customer_strategy=FixedCustomerStrategy(),
            delivery_strategy=delivery_strategy,
            shelf_life_days=30,
            is_strict=False,
            weekday_factors=[1.0] * 7,
            utilization_price=0.0,
            delivery_type="unit",
            box_size=0
        )
        
        start_date = datetime(2026, 2, 1)
        results = product.run(days=days, start_date=start_date,
                              fifo_percent=100.0, lifo_percent=0.0)
        
        # Анализируем дни с поставками
        delivery_days = []
        for day in results['daily_history']:
            if day.get('order', 0) > 0:
                date_obj = datetime.strptime(day['date'], '%d.%m.%Y')
                weekday_name = date_obj.strftime('%A')
                delivery_days.append({
                    'day': day['day'],
                    'date': day['date'],
                    'weekday': weekday_name,
                    'order': day['order']
                })
        
        print(f"\n   📊 Результаты за {days} дней:")
        print(f"   Всего поставок: {len(delivery_days)}")
        
        if delivery_days:
            print(f"\n   📅 Дни с поставками:")
            for d in delivery_days:
                print(f"      День {d['day']:2d} ({d['date']}, {d['weekday']}): заказ {d['order']:.0f} ед")
        else:
            print(f"\n   ⚠️ НЕТ НИ ОДНОЙ ПОСТАВКИ за {days} дней!")
            
        # Дополнительная диагностика
        total_stock = sum(b.quantity for b in product.batches)
        print(f"\n   📦 Итоговый остаток на складе: {total_stock:.1f} ед")
        
        return len(delivery_days) > 0
        
    except Exception as e:
        print(f"   ❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print_separator("ДИАГНОСТИКА СТРАТЕГИЙ ПОСТАВОК")
    print("\nЦель: проверить, какие стратегии работают, а какие нет")
    print("Ожидание: поставки должны происходить по расписанию или при снижении остатка")
    
    # ===== ТЕСТ 1: PeriodicDelivery (каждые 3 дня) =====
    print_separator("ТЕСТ 1: PeriodicDelivery (периодичность)")
    delivery1 = PeriodicDelivery(frequency=3, cost_type="fixed", fixed_cost=100.0)
    test_delivery_strategy(
        "PeriodicDelivery", 
        delivery1, 
        "каждые 3 дня (дни 3,6,9,12...)", 
        days=14
    )
    
    # ===== ТЕСТ 2: DaysOfWeekDelivery (понедельник и четверг) =====
    print_separator("ТЕСТ 2: DaysOfWeekDelivery (дни недели)")
    delivery2 = DaysOfWeekDelivery(delivery_days=[0, 3], cost_type="fixed", fixed_cost=100.0)
    test_delivery_strategy(
        "DaysOfWeekDelivery", 
        delivery2, 
        "понедельник (0) и четверг (3)", 
        days=14
    )
    
    # ===== ТЕСТ 3: PeriodicDelivery + условие total_stock < min_stock =====
    print_separator("ТЕСТ 3: PeriodicDelivery с условием (только при остатке ниже min_stock)")
    print("   min_stock=200, начальный остаток=200, спрос 80-120 ед/день")
    delivery3 = PeriodicDelivery(frequency=2, cost_type="fixed", fixed_cost=100.0)
    test_delivery_strategy(
        "PeriodicDelivery с условием", 
        delivery3, 
        "каждые 2 дня, но только если остаток < 200", 
        days=10
    )
    
    # ===== ТЕСТ 4: DaysOfWeekDelivery + высокий min_stock =====
    print_separator("ТЕСТ 4: DaysOfWeekDelivery с высоким min_stock")
    print("   min_stock=500 (заведомо выше начального), поставки должны быть всегда")
    
    # Создаём продукт вручную для этого теста
    try:
        product = Product(
            name="Тестовый товар",
            purchase_price=100.0,
            sale_price=150.0,
            min_stock=500.0,  # Высокий порог
            demand_strategy=UniformDemand(80, 120),
            spoilage_strategy=LinearSpoilage(30),
            customer_strategy=FixedCustomerStrategy(),
            delivery_strategy=DaysOfWeekDelivery(delivery_days=[0, 2, 4], cost_type="fixed", fixed_cost=100.0),
            shelf_life_days=30,
            is_strict=False,
            weekday_factors=[1.0] * 7,
            utilization_price=0.0,
            delivery_type="unit",
            box_size=0
        )
        
        start_date = datetime(2026, 2, 1)
        results = product.run(days=10, start_date=start_date,
                              fifo_percent=100.0, lifo_percent=0.0)
        
        delivery_days = [d for d in results['daily_history'] if d.get('order', 0) > 0]
        
        print(f"\n   📊 Результаты:")
        print(f"   Всего поставок: {len(delivery_days)}")
        print(f"   Ожидалось: поставки в понедельник(0), среду(2), пятницу(4)")
        
        if delivery_days:
            print(f"\n   📅 Фактические дни с поставками:")
            for d in delivery_days[:10]:
                date_obj = datetime.strptime(d['date'], '%d.%m.%Y')
                print(f"      День {d['day']:2d} ({d['date']}, {date_obj.strftime('%A')})")
        else:
            print(f"\n   ⚠️ ПОСТАВОК НЕТ! Проверьте условие total_stock < min_stock")
            
    except Exception as e:
        print(f"   ❌ ОШИБКА: {e}")
    
    # ===== ТЕСТ 5: Что происходит в методе should_deliver =====
    print_separator("ТЕСТ 5: Пошаговая проверка should_deliver")
    
    from datetime import datetime
    
    delivery = DaysOfWeekDelivery(delivery_days=[0, 3])  # Пн и Чт
    
    test_dates = [
        datetime(2026, 2, 1),  # Воскресенье (6)
        datetime(2026, 2, 2),  # Понедельник (0)
        datetime(2026, 2, 3),  # Вторник (1)
        datetime(2026, 2, 4),  # Среда (2)
        datetime(2026, 2, 5),  # Четверг (3)
        datetime(2026, 2, 6),  # Пятница (4)
    ]
    
    print("   Проверка DaysOfWeekDelivery.should_deliver():")
    print("   delivery_days = [0, 3] (понедельник и четверг)")
    print()
    
    for dt in test_dates:
        weekday_num = dt.weekday()
        weekday_name = dt.strftime('%A')
        should = delivery.should_deliver(
            day=dt.day, 
            current_date=dt, 
            total_stock=100,  # ниже min_stock
            min_stock=200
        )
        status = "✅ ДОЛЖНА БЫТЬ" if should else "❌ НЕТ"
        print(f"   {dt.strftime('%Y-%m-%d')} ({weekday_name}, номер {weekday_num}): {status}")
    
    # ===== ВЫВОДЫ =====
    print_separator("ДИАГНОСТИЧЕСКИЕ ВЫВОДЫ")
    print("""
    Если в тесте 2 и тесте 4 поставок НЕТ, проблема в:
      1. Передаче delivery_days из настроек в main.py
      2. Использовании DaysOfWeekDelivery вместо PeriodicDelivery
      3. Условии total_stock < min_stock (слишком низкий порог)
    
    Если в тесте 5 should_deliver возвращает True, но поставок всё равно нет:
      Проблема в calculate_order() или в run() симуляции
    
    Проверьте в main.py:
      - Импортирован ли DaysOfWeekDelivery
      - Создаётся ли он при schedule_type == "days"
      - Передаются ли delivery_days правильно
    """)


if __name__ == "__main__":
    main()