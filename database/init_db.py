from db_manager import DatabaseManager

if __name__ == "__main__":
    print("Инициализация базы данных...")
    db = DatabaseManager()
    print("✅ База данных успешно инициализирована")
    print(f"   Файл БД: {db.db_path}")
    
    # Проверка
    products = db.get_all_products()
    print(f"   Товаров в БД: {len(products)}")
