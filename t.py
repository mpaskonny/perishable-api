"""
test_diagnostic.py
Диагностика работы с партиями
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.simple_spoilage import LinearSpoilage
from core.product import Product, Batch
from core.demand import FixedDemand
from core.customer import FixedCustomerStrategy


class ManualDeliveryStrategy:
    def should_deliver(self, day, current_date, total_stock, min_stock):
        return False
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        return 0


def test_batch_tracking():
    """Тест отслеживания партий"""
    
    print("="*60)
    print("🔍 ДИАГНОСТИКА ОТСЛЕЖИВАНИЯ ПАРТИЙ")
    print("="*60)
    
    # Параметры
    shelf_life = 30
    daily_demand = 20
    
    # Создаём стратегии
    demand_strategy = FixedDemand([daily_demand] * 20)
    spoilage_strategy = LinearSpoilage(shelf_life)
    
    # Создаём продукт
    start_date = datetime(2026, 1, 1)
    product = Product(
        name="Тест",
        purchase_price=100,
        sale_price=150,
        min_stock=0,
        demand_strategy=demand_strategy,
        spoilage_strategy=spoilage_strategy,
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=ManualDeliveryStrategy(),
        shelf_life_days=shelf_life,
        is_strict=False,
        weekday_factors=[1.0] * 7,
        utilization_price=0.0,
        delivery_type="unit",
        box_size=0
    )
    
    # Ручное добавление партий
    product.batches = [
        Batch(start_date, 100),           # Партия 1: 100 кг
        Batch(start_date + timedelta(days=5), 80),   # Партия 2: 80 кг
        Batch(start_date + timedelta(days=10), 60)   # Партия 3: 60 кг
    ]
    
    print(f"\n📦 СОЗДАНО ПАРТИЙ: {len(product.batches)}")
    for i, batch in enumerate(product.batches, 1):
        print(f"   Партия {i}: {batch.quantity} кг, дата {batch.arrival_date.strftime('%d.%m')}")
    
    print(f"\n💰 Начальные затраты: {sum(b.quantity for b in product.batches) * 100} руб")
    
    # Запускаем симуляцию на 15 дней
    print(f"\n🚀 ЗАПУСК СИМУЛЯЦИИ НА 15 ДНЕЙ...")
    results = product.run(15, start_date, 100, 0)
    
    # Проверяем историю
    print(f"\n📊 ПРОВЕРКА ИСТОРИИ (первые 3 дня):")
    for i, day in enumerate(results['daily_history'][:3]):
        print(f"\nДень {day['day']}:")
        print(f"   Продажи: {day['sales']} кг")
        print(f"   Порча: {day['spoilage_kg']} кг")
        print(f"   Остаток на конец дня: {day['end_stock']} кг")
        print(f"   batch_1_stock: {day.get('batch_1_stock', 'НЕТ')}")
        print(f"   batch_2_stock: {day.get('batch_2_stock', 'НЕТ')}")
        print(f"   batch_3_stock: {day.get('batch_3_stock', 'НЕТ')}")
    
    # Проверяем итоги
    print(f"\n📊 ИТОГИ:")
    print(f"   Всего продано: {sum(d['sales'] for d in results['daily_history'])} кг")
    print(f"   Всего потеряно: {results['total_spoilage_kg']} кг")
    print(f"   Прибыль: {results['profit']} руб")
    
    # Проверяем, есть ли batch_stocks в истории
    print(f"\n🔍 КЛЮЧИ В ПЕРВОМ ДНЕ:")
    keys = results['daily_history'][0].keys()
    batch_keys = [k for k in keys if 'batch' in k]
    if batch_keys:
        print(f"   ✅ Найдены ключи партий: {batch_keys}")
    else:
        print(f"   ❌ Ключи партий НЕ НАЙДЕНЫ!")
        print(f"   Доступные ключи: {list(keys)[:10]}...")
    
    # Проверяем, работают ли продажи
    total_sales = sum(d['sales'] for d in results['daily_history'])
    if total_sales > 0:
        print(f"\n✅ Продажи работают: продано {total_sales} кг")
    else:
        print(f"\n❌ Продажи НЕ РАБОТАЮТ! Спрос есть, но продажи = 0")
        
        # Проверяем спрос
        print(f"\n🔍 ДИАГНОСТИКА СПРОСА:")
        print(f"   Спрос в первый день: {results['daily_history'][0]['demand']}")
        print(f"   Стратегия спроса: {type(product.demand).__name__}")
        
        # Проверяем batches в объекте
        print(f"\n🔍 СОСТОЯНИЕ ПАРТИЙ ПОСЛЕ СИМУЛЯЦИИ:")
        for i, batch in enumerate(product.batches, 1):
            print(f"   Партия {i}: {batch.quantity} кг")
    
    return results


if __name__ == "__main__":
    test_batch_tracking()