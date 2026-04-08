# test_spoilage_quick.py
import requests

params = {
    "days": 21,
    "product_type": "tomatoes",
    "distribution": "fixed",
    "fixed_demand": [0] * 21,
    "min_stock": 1000,
    "purchase_price": 220,
    "sale_price": 295,
    "start_date": "2026-02-01T00:00:00",
    "tomatoes_delivery_frequency": 999,
    "delivery_type": "unit",
    "box_size": 0
}

response = requests.post("http://127.0.0.1:8000/simulate", json=params)
data = response.json()

print(f"Порча за 21 день: {data['total_spoilage_kg']:.2f} кг")
print(f"Статистика: {data.get('spoilage_stats', {})}")

for day in data['daily_history'][:7]:
    print(f"День {day['day']}: spoilage={day['spoilage']:.2f} кг")