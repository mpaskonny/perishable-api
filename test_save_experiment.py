import sqlite3
import os
from database.db_manager import DatabaseManager

def test_db_structure():
    """Проверка структуры БД"""
    print("=" * 50)
    print("ТЕСТ 1: Проверка структуры БД")
    print("=" * 50)
    
    db = DatabaseManager()
    
    with sqlite3.connect("database/perishable.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Таблицы в БД:", [t[0] for t in tables])
        
        if ('experiments',) in tables:
            cursor.execute("PRAGMA table_info(experiments)")
            columns = cursor.fetchall()
            print("Колонки в experiments:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            return True
        else:
            print("❌ Таблица 'experiments' не найдена!")
            return False

def test_save_experiment():
    """Тест сохранения эксперимента"""
    print("\n" + "=" * 50)
    print("ТЕСТ 2: Сохранение эксперимента")
    print("=" * 50)
    
    db = DatabaseManager()
    
    test_data = {
        'product_name': 'Тестовый товар',
        'distribution': 'uniform',
        'days': 30,
        'fifo_percent': 75.0,
        'min_stock': 300.0,
        'purchase_price': 220.0,
        'sale_price': 295.0,
        'delivery_type': 'periodic',
        'delivery_frequency': 3,
        'delivery_days': None,
        'packing_type': 'unit',
        'box_size': 1,
        'total_revenue': 100000.0,
        'total_cost': 80000.0,
        'total_spoilage_kg': 50.0,
        'total_spoilage_money': 11000.0,
        'profit': 20000.0,
        'total_unmet_demand': 100.0
    }
    
    print("📝 Отправляемые данные:")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    
    try:
        experiment_id = db.save_experiment(test_data)
        print(f"\n✅ Эксперимент сохранён! ID = {experiment_id}")
        return experiment_id
    except Exception as e:
        print(f"\n❌ Ошибка сохранения: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_read_experiments():
    """Тест чтения экспериментов"""
    print("\n" + "=" * 50)
    print("ТЕСТ 3: Чтение экспериментов")
    print("=" * 50)
    
    db = DatabaseManager()
    experiments = db.get_all_experiments()
    
    if experiments.empty:
        print("❌ Нет экспериментов в БД")
    else:
        print(f"✅ Найдено {len(experiments)} экспериментов:")
        print(experiments.to_string())
    
    return not experiments.empty

def test_direct_sql():
    """Прямая SQL-проверка"""
    print("\n" + "=" * 50)
    print("ТЕСТ 4: Прямая SQL-проверка")
    print("=" * 50)
    
    try:
        with sqlite3.connect("database/perishable.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experiments")
            rows = cursor.fetchall()
            
            if rows:
                print(f"✅ Найдено {len(rows)} записей:")
                for row in rows:
                    print(f"  ID: {row[0]}, Продукт: {row[1]}, Прибыль: {row[16]}")
            else:
                print("❌ Нет записей в таблице experiments")
            
            cursor.execute("SELECT COUNT(*) FROM experiments")
            count = cursor.fetchone()[0]
            print(f"\nВсего записей: {count}")
            
    except Exception as e:
        print(f"❌ Ошибка SQL: {e}")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТОВ СОХРАНЕНИЯ ЭКСПЕРИМЕНТОВ")
    print()
    
    # Тест 1
    if not test_db_structure():
        print("\n⚠️ Проблема со структурой БД. Возможно, нужно удалить database/perishable.db и перезапустить приложение.")
        exit(1)
    
    # Тест 2
    exp_id = test_save_experiment()
    
    # Тест 3
    test_read_experiments()
    
    # Тест 4
    test_direct_sql()
    
    print("\n" + "=" * 50)
    print("✅ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 50)