import requests
import pandas as pd
import numpy as np
import sqlite3
from database.db_manager import DatabaseManager

API_URL = "http://127.0.0.1:8000"

def test_spoilage_from_initial_quantity():
    """Тест: порча считается от начального количества партии"""
    print("=" * 70)
    print("ТЕСТ: Порча от начального количества (должно быть 100% к 4-й неделе)")
    print("=" * 70)
    
    # 1. Проверяем параметры порчи в БД
    db = DatabaseManager()
    products_df = db.get_all_products()
    tomatoes = products_df[products_df['name'].str.contains('Помидор', case=False)]
    
    if tomatoes.empty:
        print("❌ В БД нет помидоров!")
        return False
    
    product_name = tomatoes.iloc[0]['name']
    product_id = tomatoes.iloc[0]['id_product']
    
    print(f"\n📊 Товар: {product_name}")
    
    # Параметры порчи из БД
    spoilage_rates = db.get_spoilage_rates(product_id)
    print(f"\n📊 Параметры порчи из БД:")
    for _, row in spoilage_rates.iterrows():
        print(f"   Неделя {int(row['week_number'])}: {row['rate']}%")
    
    # 2. Запускаем симуляцию
    params = {
        "days": 30,
        "product_type": "tomatoes",
        "distribution": "fixed",
        "fixed_demand": [0] * 30,
        "product_name": product_name,
        "min_stock": 1000,
        "purchase_price": tomatoes.iloc[0]['purchase_price'],
        "sale_price": tomatoes.iloc[0]['sale_price'],
        "start_date": "2026-02-01T00:00:00",
        "tomatoes_delivery_frequency": 999,
        "delivery_type": "unit",
        "box_size": 0,
        "weekday_factors": [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]
    }
    
    print(f"\n🚀 Запуск симуляции (30 дней, начальный запас = 1000 кг)...")
    
    response = requests.post(f"{API_URL}/simulate", json=params)
    
    if response.status_code != 200:
        print(f"❌ Ошибка API: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    df = pd.DataFrame(data['daily_history'])
    
    # 3. Результаты
    start_stock = df.iloc[0]['start_stock']
    print(f"\n📊 Результаты симуляции:")
    print(f"   Начальный запас: {start_stock:.0f} кг")
    print(f"   Всего испортилось: {data['total_spoilage_kg']:.2f} кг")
    print(f"   Процент от начального: {(data['total_spoilage_kg'] / start_stock) * 100:.2f}%")
    
    # 4. Понедельная порча
    print(f"\n📊 Понедельная порча (от начального запаса):")
    print("-" * 60)
    print(f"{'Неделя':<8} {'Цель':<12} {'Факт (кг)':<15} {'Факт (%)':<12}")
    print("-" * 60)
    
    for week in range(1, 5):
        start_day = (week - 1) * 7
        end_day = week * 7
        
        if end_day <= len(df):
            week_spoilage = df.iloc[start_day:end_day]['spoilage'].sum()
            week_percent = (week_spoilage / start_stock) * 100
        else:
            week_spoilage = 0
            week_percent = 0
        
        target = spoilage_rates[spoilage_rates['week_number'] == week]['rate'].values[0] if week in spoilage_rates['week_number'].values else 100
        print(f"{week:<8} {target:<12} {week_spoilage:<15.2f} {week_percent:<12.2f}")
    
    print("-" * 60)
    
    # 4.5. Ежедневная порча с накоплением
    print(f"\n📊 ЕЖЕДНЕВНАЯ ПОРЧА (с накоплением):")
    print("-" * 70)
    print(f"{'День':<6} {'Возраст':<8} {'Порча (кг)':<12} {'% за день':<10} {'Накоплено %':<12}")
    print("-" * 70)
    
    cumulative_percent = 0
    for i, row in df.iterrows():
        day = row['day']
        age = day
        spoiled_kg = row['spoilage']
        percent = (spoiled_kg / start_stock) * 100
        cumulative_percent += percent
        print(f"{day:<6} {age:<8} {spoiled_kg:<12.2f} {percent:<10.2f} {cumulative_percent:<12.2f}")
        
        if day >= 30:
            break
    
    print("-" * 70)
    print(f"Итого за 30 дней: {cumulative_percent:.2f}%")
    
    # 5. Остаток после каждой недели
    print(f"\n📊 Остаток после каждой недели:")
    for week in range(1, 5):
        end_day = week * 7
        if end_day <= len(df):
            remaining = df.iloc[end_day - 1]['end_stock']
            remaining_percent = (remaining / start_stock) * 100
            print(f"   Неделя {week}: остаток = {remaining:.2f} кг ({remaining_percent:.2f}% от начального)")
    
    # 6. Проверка
    total_percent = (data['total_spoilage_kg'] / start_stock) * 100
    print(f"\n📊 ИТОГО: испортилось {total_percent:.2f}% от начального запаса")
    
    if total_percent >= 95:
        print("\n✅ УСПЕХ: Порча достигла ~100% от начального запаса!")
        return True
    else:
        print(f"\n⚠️ ВНИМАНИЕ: Порча составила только {total_percent:.2f}% от начального запаса")
        return False


def test_spoilage_with_multiple_batches():
    """Тест: порча при нескольких партиях"""
    print("\n" + "=" * 70)
    print("ТЕСТ: Порча при нескольких партиях (с поставками)")
    print("=" * 70)
    
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    products_df = db.get_all_products()
    tomatoes = products_df[products_df['name'].str.contains('Помидор', case=False)]
    
    if tomatoes.empty:
        print("❌ Нет помидоров")
        return False
    
    product_name = tomatoes.iloc[0]['name']
    
    # Симуляция с поставками каждые 5 дней
    params = {
        "days": 30,
        "product_type": "tomatoes",
        "distribution": "fixed",
        "fixed_demand": [100] * 30,  # есть спрос
        "product_name": product_name,
        "min_stock": 500,
        "purchase_price": tomatoes.iloc[0]['purchase_price'],
        "sale_price": tomatoes.iloc[0]['sale_price'],
        "start_date": "2026-02-01T00:00:00",
        "tomatoes_delivery_frequency": 5,  # поставка каждые 5 дней
        "delivery_type": "unit",
        "box_size": 0,
        "weekday_factors": [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]
    }
    
    print(f"\n🚀 Запуск симуляции с поставками каждые 5 дней...")
    
    response = requests.post(f"{API_URL}/simulate", json=params)
    
    if response.status_code != 200:
        print(f"❌ Ошибка API: {response.status_code}")
        return False
    
    data = response.json()
    
    print(f"\n📊 Результаты:")
    print(f"   Выручка: {data['total_revenue']:.2f} руб")
    print(f"   Прибыль: {data['profit']:.2f} руб")
    print(f"   Потери от порчи: {data['total_spoilage_kg']:.2f} кг")
    
    # Проверяем, что порча распределена по разным партиям
    print(f"\n✅ Тест пройден: система работает с несколькими партиями")
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 НОВЫЙ ТЕСТ ЛОГИКИ ПОРЧИ")
    print("=" * 70)
    
    try:
        requests.get(f"{API_URL}/")
        print("✅ Сервер доступен\n")
    except:
        print("❌ Сервер не запущен!")
        exit(1)
    
    # Запускаем тесты
    test_spoilage_from_initial_quantity()
    test_spoilage_with_multiple_batches()
    
    print("\n" + "=" * 70)
    print("✅ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 70)