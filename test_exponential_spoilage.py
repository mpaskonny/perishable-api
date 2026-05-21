import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from core.exponential_spoilage import ExponentialSpoilage

def test_product(name, weekly_rates):
    print("\n" + "=" * 70)
    print(f"📊 ТЕСТ: {name}")
    print("=" * 70)
    print(f"Недельные цели: {weekly_rates}")
    
    spoilage = ExponentialSpoilage(weekly_rates, sigma=0)
    initial_qty = 1000
    
    print("\n📊 ПО ДНЯМ (от начального количества):")
    print("-" * 70)
    print(f"{'День':<6} {'Остаток':<10} {'Порча кг':<12} {'% от нач.':<12} {'% от остатка':<12}")
    print("-" * 70)
    
    remaining = initial_qty
    max_days = max(weekly_rates.keys()) * 7
    
    for day in range(1, max_days + 1):
        daily_percent = spoilage._get_daily_rate(day)
        spoiled_kg = initial_qty * daily_percent / 100
        remaining -= spoiled_kg
        
        percent_of_remaining = (spoiled_kg / (remaining + spoiled_kg)) * 100 if (remaining + spoiled_kg) > 0 else 0
        
        marker = " *" if day % 7 == 0 else ""
        print(f"{day:<6} {remaining:<10.2f} {spoiled_kg:<12.2f} {daily_percent:<12.4f} {percent_of_remaining:<12.2f}{marker}")
    
    print("-" * 70)
    
    # Проверка недельных целей
    print("\n📊 ПРОВЕРКА ПО НЕДЕЛЯМ:")
    print("-" * 55)
    print(f"{'Неделя':<8} {'Цель':<12} {'Накоплено':<12} {'Отклонение':<12}")
    print("-" * 55)
    
    for week, target in weekly_rates.items():
        day = week * 7
        actual = spoilage._get_cumulative_rate(day)
        diff = actual - target
        status = "✅" if abs(diff) < 0.1 else "❌"
        print(f"{week:<8} {target:<12} {actual:<12.2f} {diff:+12.2f} {status}")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ТЕСТ КУСОЧНО-ЭКСПОНЕНЦИАЛЬНОЙ ПОРЧИ")
    print("=" * 70)
    
    # Продукты из твоей БД
    test_product("Помидор (4 недели)", {1: 1, 2: 30, 3: 90, 4: 100})
    test_product("Клубника (3 недели)", {1: 1, 2: 50, 3: 100})
    test_product("Лимон (6 недель)", {1: 1, 2: 5, 3: 40, 4: 70, 5: 90, 6: 100})
    test_product("Яблоко (6 недель)", {1: 1, 2: 5, 3: 10, 4: 25, 5: 50, 6: 75})
    
    print("\n" + "=" * 70)
    print("✅ ТЕСТ ЗАВЕРШЁН")
    print("=" * 70)
