from datetime import datetime, timedelta
import random
import numpy as np

# Импортируем необходимые модули
from core.demand import FixedDemand, UniformDemand
from core.customer import FixedCustomerStrategy
from core.delivery import PeriodicDelivery
from core.product import Batch
from products.tomatoes import Tomatoes
from core.spoilage import WeeklySpoilage
from core.probabilistic_spoilage import ProbabilisticWeeklySpoilage


def test_tomatoes_spoilage():
    """Диагностика порчи для помидоров (по неделям)"""
    
    print("=" * 60)
    print("ДИАГНОСТИКА ПОРЧИ ДЛЯ ПОМИДОРОВ")
    print("=" * 60)
    
    start_date = datetime(2026, 2, 1)  # Понедельник
    
    # Создаем продукт
    tomatoes = Tomatoes(
        name="Помидоры",
        purchase_price=220,
        sale_price=295,
        min_stock=300,
        demand_strategy=UniformDemand(150, 200),
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=PeriodicDelivery(1),
        week_rates={1: 10.0, 2: 50.0, 3: 100.0},
        week_sigmas={1: 0.96, 2: 1.59},
        delivery_type="unit",
        box_size=0
    )
    
    # Создаем тестовые партии разного возраста
    print("\n1. СОЗДАНИЕ ТЕСТОВЫХ ПАРТИЙ:")
    print("-" * 40)
    
    # Партия 1: свежая (1 день)
    batch1 = Batch(start_date - timedelta(days=1), 100)
    # Партия 2: недельной давности (7 дней)
    batch2 = Batch(start_date - timedelta(days=7), 100)
    # Партия 3: двухнедельной давности (14 дней)
    batch3 = Batch(start_date - timedelta(days=14), 100)
    
    tomatoes.batches = [batch1, batch2, batch3]
    
    print(f"Партия 1: возраст 1 день, кол-во: {batch1.quantity} кг")
    print(f"Партия 2: возраст 7 дней, кол-во: {batch2.quantity} кг")
    print(f"Партия 3: возраст 14 дней, кол-во: {batch3.quantity} кг")
    
    # Проверяем, какая стратегия порчи используется
    print(f"\n2. ТИП СТРАТЕГИИ ПОРЧИ:")
    print("-" * 40)
    print(f"Тип: {type(tomatoes.spoilage).__name__}")
    print(f"Стратегия: {tomatoes.spoilage}")
    
    # Проверяем метод calculate_spoilage для каждой партии
    print(f"\n3. РАСЧЕТ ПОРЧИ ДЛЯ КАЖДОЙ ПАРТИИ:")
    print("-" * 40)
    
    current_date = start_date
    
    for i, batch in enumerate(tomatoes.batches, 1):
        age_days = (current_date - batch.arrival_date).days
        age_weeks = age_days // 7
        
        print(f"\nПартия {i}:")
        print(f"  Дата прибытия: {batch.arrival_date.strftime('%Y-%m-%d')}")
        print(f"  Возраст: {age_days} дней ({age_weeks} недель)")
        print(f"  Количество: {batch.quantity} кг")
        
        # Вызываем расчет порчи
        spoiled = tomatoes.spoilage.calculate_spoilage(batch, current_date)
        print(f"  Испортилось сегодня: {spoiled:.2f} кг")
        
        # Если используется ProbabilisticWeeklySpoilage, проверяем его внутреннее состояние
        if hasattr(tomatoes.spoilage, 'spoilage_records'):
            print(f"  Записей в статистике: {len(tomatoes.spoilage.spoilage_records)}")
    
    print(f"\n4. СИМУЛЯЦИЯ 2 НЕДЕЛИ (14 дней):")
    print("-" * 40)
    
    # Пересоздаем продукт для чистой симуляции
    tomatoes2 = Tomatoes(
        name="Помидоры",
        purchase_price=220,
        sale_price=295,
        min_stock=300,
        demand_strategy=FixedDemand([0] * 30),  # Нулевой спрос, чтобы не мешал
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=PeriodicDelivery(999),  # Без поставок
        week_rates={1: 10.0, 2: 50.0, 3: 100.0},
        week_sigmas={1: 0.96, 2: 1.59},
        delivery_type="unit",
        box_size=0
    )
    
    # Создаем одну партию
    tomatoes2.batches = [Batch(start_date, 1000)]  # 1000 кг свежих помидоров
    print(f"Начальный запас: 1000 кг (свежие, дата: {start_date.strftime('%Y-%m-%d')})")
    
    total_spoiled = 0
    weekly_stats = []
    
    for day in range(1, 15):
        current_date = start_date + timedelta(days=day)
        age_days = (current_date - tomatoes2.batches[0].arrival_date).days
        age_weeks = age_days // 7
        
        # Сохраняем количество до порчи
        before = tomatoes2.batches[0].quantity
        
        # Рассчитываем порчу
        spoiled = tomatoes2._process_spoilage(current_date)
        spoiled_kg = spoiled[0] if isinstance(spoiled, tuple) else spoiled
        
        total_spoiled += spoiled_kg
        
        if spoiled_kg > 0:
            weekly_stats.append({
                'day': day,
                'age_weeks': age_weeks,
                'spoiled': spoiled_kg,
                'remaining': tomatoes2.batches[0].quantity
            })
        
        print(f"День {day:2d} (возраст {age_days:2d} дн/{age_weeks} нед): "
              f"испортилось {spoiled_kg:6.2f} кг, осталось {tomatoes2.batches[0].quantity:6.2f} кг")
    
    print(f"\n5. ИТОГИ ЗА 14 ДНЕЙ:")
    print("-" * 40)
    print(f"Всего испортилось: {total_spoiled:.2f} кг из 1000 кг")
    print(f"Процент порчи: {total_spoiled/10:.2f}%")
    
    if total_spoiled == 0:
        print("\n❌ ПРОБЛЕМА: Порча полностью отсутствует!")
        print("   Возможные причины:")
        print("   1. Стратегия порчи возвращает 0 для всех возрастов")
        print("   2. Метод _process_spoilage в Product не вызывается")
        print("   3. Неправильно рассчитывается возраст партии")
    elif total_spoiled > 0 and total_spoiled < 500:
        print("\n⚠️ ВНИМАНИЕ: Порча есть, но очень маленькая")
        print("   Возможно, порча начисляется ежедневно малыми долями")
    elif total_spoiled >= 500:
        print("\n✅ ПОРЧА РАБОТАЕТ: Значительная часть товара испортилась")
    
    return total_spoiled


def test_milk_spoilage():
    """Диагностика порчи для молока (по дням, строгий срок)"""
    
    print("\n" + "=" * 60)
    print("ДИАГНОСТИКА ПОРЧИ ДЛЯ МОЛОКА")
    print("=" * 60)
    
    from products.milk import Milk
    from core.spoilage import StrictExpirySpoilage
    
    start_date = datetime(2026, 2, 1)
    
    milk = Milk(
        name="Молоко",
        purchase_price=30,
        sale_price=90,
        min_stock=100,
        demand_strategy=FixedDemand([0] * 20),  # Нулевой спрос
        customer_strategy=FixedCustomerStrategy(),
        delivery_strategy=PeriodicDelivery(999),  # Без поставок
        shelf_life_days=10,
        utilization_price=5.0,
        delivery_type="unit",
        box_size=0
    )
    
    print("\n1. ТИП СТРАТЕГИИ ПОРЧИ:")
    print("-" * 40)
    print(f"Тип: {type(milk.spoilage).__name__}")
    
    # Создаем партию с истекающим сроком
    expiry_date = start_date + timedelta(days=5)
    milk.batches = [Batch(start_date, 100, expiry_date)]
    
    print(f"\n2. ТЕСТИРОВАНИЕ ПОРЧИ МОЛОКА:")
    print("-" * 40)
    print(f"Дата старта: {start_date.strftime('%Y-%m-%d')}")
    print(f"Срок годности: {expiry_date.strftime('%Y-%m-%d')}")
    print(f"Начальный запас: 100 пакетов")
    
    for day in range(1, 12):
        current_date = start_date + timedelta(days=day)
        before = milk.batches[0].quantity
        
        spoiled = milk._process_spoilage(current_date)
        spoiled_kg = spoiled[0] if isinstance(spoiled, tuple) else spoiled
        
        status = "✓ свежее" if current_date < expiry_date else "⚠️ ПРОСРОЧЕНО"
        print(f"День {day:2d}: {current_date.strftime('%Y-%m-%d')} - {status}, "
              f"испортилось: {spoiled_kg:3.0f} пакетов, осталось: {milk.batches[0].quantity:3.0f}")
    
    print("\n✅ Диагностика молока завершена")


def debug_tomatoes_spoilage_direct():
    """Прямая диагностика метода порчи без симуляции"""
    
    print("\n" + "=" * 60)
    print("ПРЯМАЯ ДИАГНОСТИКА АЛГОРИТМА ПОРЧИ")
    print("=" * 60)
    
    from core.spoilage import WeeklySpoilage
    from core.probabilistic_spoilage import ProbabilisticWeeklySpoilage
    
    start_date = datetime(2026, 2, 1)
    
    # Тест 1: Старая стратегия WeeklySpoilage
    print("\n1. ТЕСТ СТАРОЙ СТРАТЕГИИ (WeeklySpoilage):")
    print("-" * 40)
    old_strategy = WeeklySpoilage({1: 10.0, 2: 50.0}, {1: 0.96, 2: 1.59})
    
    batch = Batch(start_date - timedelta(days=7), 100)  # 7 дней (1 неделя)
    spoiled = old_strategy.calculate_spoilage(batch, start_date)
    print(f"  Партия возрастом 7 дней: испортилось {spoiled:.2f} кг (ожидалось ~10 кг)")
    
    batch = Batch(start_date - timedelta(days=14), 100)  # 14 дней (2 недели)
    spoiled = old_strategy.calculate_spoilage(batch, start_date)
    print(f"  Партия возрастом 14 дней: испортилось {spoiled:.2f} кг (ожидалось ~50 кг)")
    
    # Тест 2: Новая стратегия ProbabilisticWeeklySpoilage
    print("\n2. ТЕСТ НОВОЙ СТРАТЕГИИ (ProbabilisticWeeklySpoilage):")
    print("-" * 40)
    new_strategy = ProbabilisticWeeklySpoilage({1: 10.0, 2: 50.0}, {1: 0.96, 2: 1.59})
    
    batch = Batch(start_date - timedelta(days=7), 100)
    spoiled = new_strategy.calculate_spoilage(batch, start_date)
    print(f"  Партия возрастом 7 дней: испортилось {spoiled:.2f} кг (ожидалось ~10 кг)")
    
    batch = Batch(start_date - timedelta(days=14), 100)
    spoiled = new_strategy.calculate_spoilage(batch, start_date)
    print(f"  Партия возрастом 14 дней: испортилось {spoiled:.2f} кг (ожидалось ~50 кг)")
    
    # Тест 3: Проверка накопления статистики
    print("\n3. ПРОВЕРКА СБОРА СТАТИСТИКИ:")
    print("-" * 40)
    stats = new_strategy.get_statistics()
    print(f"  Собрано статистики: {stats}")


if __name__ == "__main__":
    print("🔍 НАЧАЛО ДИАГНОСТИКИ ПОРЧИ")
    print()
    
    # Прямая диагностика алгоритмов
    debug_tomatoes_spoilage_direct()
    
    # Диагностика молока
    test_milk_spoilage()
    
    # Диагностика помидоров
    result = test_tomatoes_spoilage()
    
    print("\n" + "=" * 60)
    print("ВЫВОДЫ:")
    print("=" * 60)
    
    if result == 0:
        print("❌ ПОМИДОРЫ: Порча не работает")
        print("→ Проверьте, какая стратегия используется в Tomatoes.__init__")
        print("→ Убедитесь, что вызов super().__init__ передает spoilage_strategy")
    elif result < 100:
        print("⚠️ ПОМИДОРЫ: Порча работает, но очень слабо")
        print("→ Возможно, порча начисляется ежедневно дробными долями")
    else:
        print("✅ ПОМИДОРЫ: Порча работает корректно")
    
    print("\n💡 Для отладки добавьте в tomatoes.py временный print:")
    print("   def _process_spoilage(self, current_date):")
    print("       print(f'Processing spoilage for {current_date}')")
    print("       return super()._process_spoilage(current_date)")