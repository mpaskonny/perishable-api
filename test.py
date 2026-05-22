"""
test_sigma.py
Тест загрузки сигм из Excel-файла
"""

from core.sigma_loader import get_sigma_loader

def test_sigma():
    print("=" * 60)
    print("📊 ТЕСТ ЗАГРУЗКИ СИГМ")
    print("=" * 60)
    
    loader = get_sigma_loader()
    stats = loader.get_stats()
    
    print(f"\n📈 Статистика:")
    print(f"   Загружено сигм: {stats['loaded']}")
    print(f"   Доступные спросы: {stats['demands']}")
    
    print("\n🔍 Проверка получения сигм:")
    
    # Список спросов для теста
    test_demands = [10, 15, 23, 30, 35, 42, 50, 55, 100]
    
    for demand in test_demands:
        sigma = loader.get_sigma(demand)
        print(f"   Базовый спрос: {demand:3d} → сигма: {sigma:.4f}")
    
    print("\n✅ Тест завершён")

if __name__ == "__main__":
    test_sigma()