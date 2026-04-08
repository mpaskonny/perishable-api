from datetime import datetime, timedelta
from core.demand import FixedDemand
from core.customer import FixedCustomerStrategy
from core.delivery import PeriodicDelivery
from core.product import Batch
from products.milk import Milk


def test_sales_logic():
    """Тест корректности FIFO/LIFO логики"""
    
    start_date = datetime(2026, 2, 1)
    
    milk = Milk(
        name="Тест",
        purchase_price=30,
        sale_price=90,
        min_stock=100,
        demand_strategy=FixedDemand([50]),
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=PeriodicDelivery(999),
        shelf_life_days=10,
        delivery_type="unit",
        box_size=0
    )
    
    print("=" * 50)
    print("ТЕСТ 1: Только FIFO (100% берут старое)")
    print("=" * 50)
    milk.batches = [
        Batch(start_date - timedelta(days=5), 30, start_date + timedelta(days=5)),
        Batch(start_date - timedelta(days=1), 30, start_date + timedelta(days=9))
    ]
    sold, revenue, fifo, lifo = milk._process_sales(50, start_date, 100, 0)
    print(f"Продано: {sold}, FIFO: {fifo}, LIFO: {lifo}")
    assert fifo == 50 and lifo == 0, f"❌ Ошибка! Получено FIFO={fifo}, LIFO={lifo}"
    print("✅ Пройден\n")
    
    print("=" * 50)
    print("ТЕСТ 2: Только LIFO (100% берут свежее)")
    print("=" * 50)
    milk.batches = [
        Batch(start_date - timedelta(days=5), 30, start_date + timedelta(days=5)),
        Batch(start_date - timedelta(days=1), 30, start_date + timedelta(days=9))
    ]
    sold, revenue, fifo, lifo = milk._process_sales(50, start_date, 0, 100)
    print(f"Продано: {sold}, FIFO: {fifo}, LIFO: {lifo}")
    assert lifo == 50 and fifo == 0, f"❌ Ошибка! Получено FIFO={fifo}, LIFO={lifo}"
    print("✅ Пройден\n")
    
    print("=" * 50)
    print("ТЕСТ 3: Смешанный режим 50/50")
    print("=" * 50)
    milk.batches = [
        Batch(start_date - timedelta(days=5), 30, start_date + timedelta(days=5)),
        Batch(start_date - timedelta(days=1), 30, start_date + timedelta(days=9))
    ]
    sold, revenue, fifo, lifo = milk._process_sales(50, start_date, 50, 50)
    print(f"Продано: {sold}, FIFO: {fifo}, LIFO: {lifo}")
    assert fifo == 25 and lifo == 25, f"❌ Ошибка! Ожидалось 25/25, получено {fifo}/{lifo}"
    print("✅ Пройден\n")
    
    print("=" * 50)
    print("ТЕСТ 4: Недостаточно товара (дефицит)")
    print("=" * 50)
    milk.batches = [
        Batch(start_date - timedelta(days=5), 20, start_date + timedelta(days=5)),  # всего 40
        Batch(start_date - timedelta(days=1), 20, start_date + timedelta(days=9))
    ]
    sold, revenue, fifo, lifo = milk._process_sales(50, start_date, 50, 50)
    print(f"Продано: {sold} (ожидалось 40 из-за дефицита), FIFO: {fifo}, LIFO: {lifo}")
    assert sold == 40, f"❌ Ошибка! При дефиците продано {sold}, ожидалось 40"
    print("✅ Пройден\n")
    
    print("\n" + "=" * 50)
    print("🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
    print("=" * 50)


if __name__ == "__main__":
    test_sales_logic()