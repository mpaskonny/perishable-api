from datetime import datetime
from core.demand import UniformDemand
from core.customer import FixedCustomerStrategy
from core.delivery import PeriodicDelivery
from products.tomatoes import Tomatoes

print("=" * 60)
print("ПРЯМАЯ ПРОВЕРКА ИСТОРИИ ПОМИДОРОВ")
print("=" * 60)

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

results = tomatoes.run(14, datetime(2026, 2, 1), 50, 50)

print(f"\n✅ Симуляция завершена")
print(f"Всего порчи (кг): {results['total_spoilage_kg']:.2f}")
print(f"Всего порчи (руб): {results['total_spoilage_money']:.2f}")
print(f"\nПервые 3 дня истории:")
print("-" * 40)

for h in results['daily_history'][:3]:
    print(f"\nДень {h['day']}:")
    print(f"  spoilage_kg: {h.get('spoilage_kg', 'НЕТ ПОЛЯ!')}")
    print(f"  spoilage_money: {h.get('spoilage_money', 'НЕТ ПОЛЯ!')}")
    print(f"  Все ключи: {list(h.keys())}")

print(f"\n\nПоследние 3 дня истории:")
print("-" * 40)
for h in results['daily_history'][-3:]:
    print(f"\nДень {h['day']}:")
    print(f"  spoilage_kg: {h.get('spoilage_kg', 'НЕТ ПОЛЯ!')}")
