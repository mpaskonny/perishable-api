"""
test_proportional_sales.py
Тест: для товаров с неявным сроком годности продажа идёт пропорционально из всех партий
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.simple_spoilage import LinearSpoilage, ExponentialSpoilage
from core.product import Product, Batch
from core.demand import FixedDemand
from core.customer import FixedCustomerStrategy


class ManualDeliveryStrategy:
    def should_deliver(self, day, current_date, total_stock, min_stock):
        return False
    def calculate_order(self, total_stock, min_stock, delivery_type, box_size):
        return 0


def test_proportional_sales_gradual():
    """
    ТЕСТ 1: Для gradual продуктов продажа должна быть пропорциональной
    (из каждой партии продаётся одинаковый процент)
    """
    
    print("\n" + "="*80)
    print("📊 ТЕСТ 1: ПРОПОРЦИОНАЛЬНАЯ ПРОДАЖА (GRADUAL ПРОДУКТ)")
    print("="*80)
    
    # Параметры
    shelf_life = 30
    daily_demand = 100  # Спрос 100 кг в день
    
    # Создаём стратегии
    demand_strategy = FixedDemand([daily_demand])
    spoilage_strategy = LinearSpoilage(shelf_life)
    
    # Создаём продукт
    start_date = datetime(2026, 1, 1)
    product = Product(
        name="Помидоры",
        purchase_price=100,
        sale_price=150,
        min_stock=0,
        demand_strategy=demand_strategy,
        spoilage_strategy=spoilage_strategy,
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=ManualDeliveryStrategy(),
        shelf_life_days=shelf_life,
        is_strict=False,  # ← GRADUAL продукт!
        weekday_factors=[1.0] * 7,
        utilization_price=0.0,
        delivery_type="unit",
        box_size=0
    )
    
    # Подменяем init_batches
    product.init_batches = lambda start_date: None
    
    # Три партии разного размера
    product.batches = [
        Batch(start_date, 100),   # Партия 1: 100 кг
        Batch(start_date, 200),   # Партия 2: 200 кг
        Batch(start_date, 300)    # Партия 3: 300 кг
    ]
    
    # Сохраняем копии для проверки
    original_batches = [b.quantity for b in product.batches]
    
    print(f"\n📦 Начальные партии:")
    for i, batch in enumerate(product.batches, 1):
        print(f"   Партия {i}: {batch.quantity} кг")
    
    print(f"\n📈 Спрос: {daily_demand} кг")
    print(f"📋 Ожидание: при пропорциональной продаже должно продаться:")
    
    total_stock = sum(original_batches)
    expected_sold = []
    for i, qty in enumerate(original_batches, 1):
        sell = qty * (daily_demand / total_stock)
        expected_sold.append(sell)
        print(f"   - Из партии {i}: {sell:.1f} кг ({sell/qty*100:.1f}%)")
    
    # Запускаем симуляцию на 1 день
    results = product.run(1, start_date, 100, 0)
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Продано всего: {results['daily_history'][0]['sales']} кг")
    print(f"\n   Остатки после продажи:")
    
    all_correct = True
    for i, batch in enumerate(product.batches, 1):
        expected_remaining = original_batches[i-1] - expected_sold[i-1]
        actual_remaining = batch.quantity
        diff = abs(actual_remaining - expected_remaining)
        
        print(f"   Партия {i}: {actual_remaining:.1f} кг (ожидалось {expected_remaining:.1f} кг)")
        
        if diff < 0.1:
            print(f"      ✅ Верно")
        else:
            print(f"      ❌ Ошибка: {diff:.1f} кг")
            all_correct = False
    
    return all_correct


def test_fifo_for_strict():
    """
    ТЕСТ 2: Для strict продуктов должно быть FIFO (старые партии продаются первыми)
    """
    
    print("\n" + "="*80)
    print("📊 ТЕСТ 2: FIFO ДЛЯ STRICT ПРОДУКТА (МОЛОКО)")
    print("="*80)
    
    from core.spoilage import StrictExpirySpoilage
    
    # Параметры
    shelf_life = 10
    daily_demand = 100
    
    # Создаём стратегии
    demand_strategy = FixedDemand([daily_demand])
    spoilage_strategy = StrictExpirySpoilage()
    
    # Создаём продукт
    start_date = datetime(2026, 1, 1)
    product = Product(
        name="Молоко",
        purchase_price=30,
        sale_price=90,
        min_stock=0,
        demand_strategy=demand_strategy,
        spoilage_strategy=spoilage_strategy,
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=ManualDeliveryStrategy(),
        shelf_life_days=shelf_life,
        is_strict=True,  # ← STRICT продукт!
        weekday_factors=[1.0] * 7,
        utilization_price=5.0,
        delivery_type="unit",
        box_size=0
    )
    
    # Подменяем init_batches
    product.init_batches = lambda start_date: None
    
    # Две партии разного возраста
    product.batches = [
        Batch(start_date - timedelta(days=5), 100),   # Старая партия (возраст 5 дней)
        Batch(start_date, 100)                         # Новая партия
    ]
    
    print(f"\n📦 Начальные партии:")
    print(f"   Партия 1 (старая): {product.batches[0].quantity} кг, возраст 5 дней")
    print(f"   Партия 2 (новая): {product.batches[1].quantity} кг, возраст 0 дней")
    
    print(f"\n📈 Спрос: {daily_demand} кг")
    print(f"📋 Ожидание (FIFO): должны продаться ТОЛЬКО старые партии")
    print(f"   - Из партии 1 (старая): 100 кг")
    print(f"   - Из партии 2 (новая): 0 кг")
    
    # Запускаем симуляцию на 1 день (100% FIFO)
    results = product.run(1, start_date, 100, 0)
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Продано всего: {results['daily_history'][0]['sales']} кг")
    print(f"\n   Остатки после продажи:")
    
    # Проверяем остатки
    all_correct = True
    
    # Находим старую и новую партии по возрасту
    old_batch = None
    new_batch = None
    for batch in product.batches:
        age = (start_date - batch.arrival_date).days
        if age > 0:
            old_batch = batch
        else:
            new_batch = batch
    
    if old_batch:
        if old_batch.quantity == 0:
            print(f"   ✅ Старая партия: полностью продана (0 кг)")
        else:
            print(f"   ❌ Старая партия: осталось {old_batch.quantity} кг (ожидалось 0)")
            all_correct = False
    else:
        print(f"   ✅ Старая партия: полностью продана (удалена из списка)")
    
    if new_batch:
        if abs(new_batch.quantity - 100) < 0.1:
            print(f"   ✅ Новая партия: не тронута (100 кг)")
        else:
            print(f"   ❌ Новая партия: продано {100 - new_batch.quantity} кг (ожидалось 0)")
            all_correct = False
    else:
        # Если новой партии нет в списке, значит она тоже была продана — это ошибка
        print(f"   ❌ Новая партия: удалена из списка (должна была остаться 100 кг)")
        all_correct = False
    
    return all_correct


def test_lifo_for_strict():
    """
    ТЕСТ 3: Для strict продуктов LIFO (новые партии продаются первыми)
    """
    
    print("\n" + "="*80)
    print("📊 ТЕСТ 3: LIFO ДЛЯ STRICT ПРОДУКТА (МОЛОКО)")
    print("="*80)
    
    from core.spoilage import StrictExpirySpoilage
    
    # Параметры
    shelf_life = 10
    daily_demand = 100
    
    # Создаём стратегии
    demand_strategy = FixedDemand([daily_demand])
    spoilage_strategy = StrictExpirySpoilage()
    
    # Создаём продукт
    start_date = datetime(2026, 1, 1)
    product = Product(
        name="Молоко",
        purchase_price=30,
        sale_price=90,
        min_stock=0,
        demand_strategy=demand_strategy,
        spoilage_strategy=spoilage_strategy,
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=ManualDeliveryStrategy(),
        shelf_life_days=shelf_life,
        is_strict=True,  # ← STRICT продукт!
        weekday_factors=[1.0] * 7,
        utilization_price=5.0,
        delivery_type="unit",
        box_size=0
    )
    
    # Подменяем init_batches
    product.init_batches = lambda start_date: None
    
    # Две партии разного возраста
    product.batches = [
        Batch(start_date - timedelta(days=5), 100),   # Старая партия
        Batch(start_date, 100)                         # Новая партия
    ]
    
    print(f"\n📦 Начальные партии:")
    print(f"   Партия 1 (старая): {product.batches[0].quantity} кг, возраст 5 дней")
    print(f"   Партия 2 (новая): {product.batches[1].quantity} кг, возраст 0 дней")
    
    print(f"\n📈 Спрос: {daily_demand} кг")
    print(f"📋 Ожидание (LIFO): должны продаться ТОЛЬКО новые партии")
    print(f"   - Из партии 1 (старая): 0 кг")
    print(f"   - Из партии 2 (новая): 100 кг")
    
    # Запускаем симуляцию на 1 день (0% FIFO = 100% LIFO)
    results = product.run(1, start_date, 0, 100)
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Продано всего: {results['daily_history'][0]['sales']} кг")
    print(f"\n   Остатки после продажи:")
    
    all_correct = True
    
    # Находим старую и новую партии по возрасту
    old_batch = None
    new_batch = None
    for batch in product.batches:
        age = (start_date - batch.arrival_date).days
        if age > 0:
            old_batch = batch
        else:
            new_batch = batch
    
    if old_batch:
        if abs(old_batch.quantity - 100) < 0.1:
            print(f"   ✅ Старая партия: не тронута (100 кг)")
        else:
            print(f"   ❌ Старая партия: продано {100 - old_batch.quantity} кг (ожидалось 0)")
            all_correct = False
    else:
        # Если старой партии нет в списке, значит она была продана — это ошибка
        print(f"   ❌ Старая партия: удалена из списка (должна была остаться 100 кг)")
        all_correct = False
    
    if new_batch:
        if new_batch.quantity == 0:
            print(f"   ✅ Новая партия: полностью продана (0 кг)")
        else:
            print(f"   ❌ Новая партия: осталось {new_batch.quantity} кг (ожидалось 0)")
            all_correct = False
    else:
        print(f"   ✅ Новая партия: полностью продана (удалена из списка)")
    
    return all_correct


def test_mixed_fifo_lifo():
    """
    ТЕСТ 4: Смешанное FIFO/LIFO для strict продуктов
    """
    
    print("\n" + "="*80)
    print("📊 ТЕСТ 4: СМЕШАННОЕ FIFO/LIFO (75% FIFO, 25% LIFO)")
    print("="*80)
    
    from core.spoilage import StrictExpirySpoilage
    
    # Параметры
    shelf_life = 10
    daily_demand = 100
    fifo_percent = 75
    lifo_percent = 25
    
    # Создаём стратегии
    demand_strategy = FixedDemand([daily_demand])
    spoilage_strategy = StrictExpirySpoilage()
    
    # Создаём продукт
    start_date = datetime(2026, 1, 1)
    product = Product(
        name="Молоко",
        purchase_price=30,
        sale_price=90,
        min_stock=0,
        demand_strategy=demand_strategy,
        spoilage_strategy=spoilage_strategy,
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=ManualDeliveryStrategy(),
        shelf_life_days=shelf_life,
        is_strict=True,
        weekday_factors=[1.0] * 7,
        utilization_price=5.0,
        delivery_type="unit",
        box_size=0
    )
    
    # Подменяем init_batches
    product.init_batches = lambda start_date: None
    
    # Две партии
    product.batches = [
        Batch(start_date - timedelta(days=5), 100),   # Старая
        Batch(start_date, 100)                         # Новая
    ]
    
    print(f"\n📦 Начальные партии:")
    print(f"   Партия 1 (старая): 100 кг")
    print(f"   Партия 2 (новая): 100 кг")
    print(f"\n📈 Спрос: 100 кг")
    print(f"👥 Распределение: FIFO={fifo_percent}%, LIFO={lifo_percent}%")
    print(f"📋 Ожидание:")
    print(f"   - FIFO: {fifo_percent} кг из старой партии")
    print(f"   - LIFO: {lifo_percent} кг из новой партии")
    
    # Запускаем симуляцию
    results = product.run(1, start_date, fifo_percent, lifo_percent)
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Продано всего: {results['daily_history'][0]['sales']} кг")
    print(f"   FIFO продажи: {results['daily_history'][0]['fifo_sales']} кг")
    print(f"   LIFO продажи: {results['daily_history'][0]['lifo_sales']} кг")
    
    # Проверяем
    all_correct = True
    fifo_actual = results['daily_history'][0]['fifo_sales']
    lifo_actual = results['daily_history'][0]['lifo_sales']
    
    if abs(fifo_actual - fifo_percent) <= 1:
        print(f"   ✅ FIFO: {fifo_actual:.0f} кг (ожидалось {fifo_percent} кг)")
    else:
        print(f"   ❌ FIFO: {fifo_actual:.0f} кг (ожидалось {fifo_percent} кг)")
        all_correct = False
    
    if abs(lifo_actual - lifo_percent) <= 1:
        print(f"   ✅ LIFO: {lifo_actual:.0f} кг (ожидалось {lifo_percent} кг)")
    else:
        print(f"   ❌ LIFO: {lifo_actual:.0f} кг (ожидалось {lifo_percent} кг)")
        all_correct = False
    
    return all_correct


def run_all_tests():
    """Запуск всех тестов"""
    
    print("\n" + "🧪"*20)
    print("🧪 ЗАПУСК ТЕСТОВ ПРОДАЖ (FIFO/LIFO vs ПРОПОРЦИОНАЛЬНО)")
    print("🧪"*20)
    
    results = []
    
    # Тест 1: Пропорциональная продажа (gradual)
    results.append(("Пропорциональная продажа (gradual)", test_proportional_sales_gradual()))
    
    # Тест 2: FIFO (strict)
    results.append(("FIFO (строгий срок)", test_fifo_for_strict()))
    
    # Тест 3: LIFO (strict)
    results.append(("LIFO (строгий срок)", test_lifo_for_strict()))
    
    # Тест 4: Смешанное FIFO/LIFO
    results.append(("Смешанное FIFO/LIFO", test_mixed_fifo_lifo()))
    
    # Итоги
    print("\n" + "="*80)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)
    
    all_passed = True
    for name, passed in results:
        status = "✅ ПРОЙДЕН" if passed else "❌ НЕ ПРОЙДЕН"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("   - Gradual продукты: продажа пропорциональная")
        print("   - Strict продукты: FIFO/LIFO работают корректно")
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ, ТРЕБУЕТСЯ ДОРАБОТКА product.py")
    print("="*80)
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()