import requests
import json
from datetime import datetime

API_URL = "http://127.0.0.1:8000"

# Параметры для теста (как в Streamlit)
params = {
    "days": 30,
    "min_stock": 300.0,
    "purchase_price": 220.0,
    "sale_price": 295.0,
    "product_type": "tomatoes",
    "distribution": "uniform",
    "start_date": "2026-02-01T00:00:00",
    "sigma_10": 0.96,
    "sigma_50": 1.59,
    "delivery_type": "unit",
    "box_size": 0,
    "weekday_factors": [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]
}

print("=" * 60)
print("ОТЛАДКА API ДЛЯ ПОМИДОРОВ")
print("=" * 60)

try:
    response = requests.post(f"{API_URL}/simulate", json=params)
    response.raise_for_status()
    data = response.json()
    
    print(f"\n✅ API ответил успешно")
    print(f"Общая выручка: {data['total_revenue']:.2f}")
    print(f"Общие затраты: {data['total_cost']:.2f}")
    print(f"Прибыль: {data['profit']:.2f}")
    print(f"Всего порчи (кг): {data['total_spoilage_kg']:.2f}")
    print(f"Всего порчи (руб): {data['total_spoilage_money']:.2f}")
    
    # Проверяем daily_history
    if data['daily_history']:
        print(f"\n📊 ПРОВЕРКА DAILY_HISTORY (первые 5 дней):")
        print("-" * 40)
        
        for i, day in enumerate(data['daily_history'][:5]):
            print(f"\nДень {day['day']}:")
            print(f"  Спрос: {day['demand']}")
            print(f"  Продажи: {day['sales']}")  # ← посмотрим, что приходит
            print(f"  Порча (spoilage list): {day['spoilage']}")  # ← критично!
            print(f"  Порча (spoilage_kg original): {day.get('spoilage_kg', 'N/A')}")
            
            # Проверяем, есть ли порча в данных
            if isinstance(day['spoilage'], list):
                total_spoilage_day = sum(day['spoilage'])
                print(f"  Суммарная порча за день: {total_spoilage_day}")
            else:
                print(f"  Порча не в формате списка: {type(day['spoilage'])}")
    
    # Проверяем spoilage_stats
    print(f"\n📊 СТАТИСТИКА ПОРЧИ ИЗ API:")
    print("-" * 40)
    if 'spoilage_stats' in data:
        stats = data['spoilage_stats']
        for key, value in stats.items():
            if 'rates' not in key:  # Не выводим огромные списки
                print(f"  {key}: {value}")
    
    # Проверяем суммарную порчу по дням
    print(f"\n📊 СУММАРНАЯ ПОРЧА ПО ДНЯМ:")
    print("-" * 40)
    total_from_days = 0
    days_with_spoilage = 0
    
    for day in data['daily_history']:
        if isinstance(day['spoilage'], list):
            day_spoilage = sum(day['spoilage'])
        else:
            day_spoilage = day['spoilage'] if isinstance(day['spoilage'], (int, float)) else 0
        
        total_from_days += day_spoilage
        if day_spoilage > 0:
            days_with_spoilage += 1
    
    print(f"Всего дней с порчей: {days_with_spoilage} из {len(data['daily_history'])}")
    print(f"Суммарная порча из daily_history: {total_from_days:.2f} кг")
    print(f"Суммарная порча из total_spoilage_kg: {data['total_spoilage_kg']:.2f} кг")
    
    if total_from_days != data['total_spoilage_kg']:
        print(f"\n⚠️ НЕСООТВЕТСТВИЕ: daily_history показывает {total_from_days}, а total_spoilage_kg = {data['total_spoilage_kg']}")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()