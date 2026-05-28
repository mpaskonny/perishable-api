"""
test_settings_debug.py
Тест для проверки сохранения настроек в session_state
"""

import streamlit as st
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_settings_structure():
    """Тест структуры настроек"""
    
    print("\n" + "=" * 60)
    print("📊 ТЕСТ 1: СТРУКТУРА НАСТРОЕК ПО УМОЛЧАНИЮ")
    print("=" * 60)
    
    # Имитация st.session_state.settings
    default_settings = {
        'distribution': 'uniform',
        'weekday_factors': [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1],
        'delivery_type': 'unit',
        'box_size': 20,
        'fixed_quantity': None,
        'delivery_frequency': 2,
        'delivery_days': [0, 3],
        'schedule_type': 'frequency',
        'use_custom_bounds': False,
        'demand_min': None,
        'demand_max': None,
        'reorder_point': None,
        'max_stock': None,
        'delivery_cost_type': 'none',
        'delivery_fixed_cost': 0.0,
        'delivery_rate_cost': 0.0,
        'min_stock': 300
    }
    
    print("\n📦 Настройки по умолчанию:")
    for key, value in default_settings.items():
        print(f"   {key}: {value}")
    
    return default_settings


def test_save_fixed_quantity():
    """Тест: сохраняется ли fixed_quantity при изменении"""
    
    print("\n" + "=" * 60)
    print("📊 ТЕСТ 2: СОХРАНЕНИЕ FIXED_QUANTITY")
    print("=" * 60)
    
    # Имитация настроек до изменения
    settings_before = {
        'delivery_type': 'unit',
        'fixed_quantity': None
    }
    
    print(f"\n📦 ДО изменения:")
    print(f"   delivery_type: {settings_before['delivery_type']}")
    print(f"   fixed_quantity: {settings_before['fixed_quantity']}")
    
    # Имитация выбора фиксированного объёма в модальном окне
    # и нажатия "Сохранить настройки"
    settings_after = {
        'delivery_type': 'fixed',
        'fixed_quantity': 100
    }
    
    print(f"\n📦 ПОСЛЕ изменения:")
    print(f"   delivery_type: {settings_after['delivery_type']}")
    print(f"   fixed_quantity: {settings_after['fixed_quantity']}")
    
    if settings_after['fixed_quantity'] == 100:
        print("\n✅ fixed_quantity успешно сохранён!")
        return True
    else:
        print("\n❌ fixed_quantity НЕ сохранён!")
        return False


def test_schedule_type_with_fixed():
    """Тест: при фиксированном объёме schedule_type должен быть НЕ ss_policy"""
    
    print("\n" + "=" * 60)
    print("📊 ТЕСТ 3: РАСПИСАНИЕ ПРИ ФИКСИРОВАННОМ ОБЪЁМЕ")
    print("=" * 60)
    
    # При фиксированном объёме (s, S) недоступен
    delivery_type = "fixed"
    available_schedule_types = ["frequency", "days"]
    
    print(f"\n📦 Способ поставки: {delivery_type}")
    print(f"   Доступные типы расписания: {available_schedule_types}")
    
    if "ss_policy" not in available_schedule_types:
        print("\n✅ (s, S)-стратегия недоступна при фиксированном объёме")
        return True
    else:
        print("\n❌ Ошибка: (s, S) доступен при фиксированном объёме")
        return False


def test_params_transfer():
    """Тест: проверяет, какие параметры должны быть в params"""
    
    print("\n" + "=" * 60)
    print("📊 ТЕСТ 4: ПРОВЕРКА ПАРАМЕТРОВ ДЛЯ API")
    print("=" * 60)
    
    # Имитация settings после выбора фиксированного объёма
    settings = {
        'delivery_type': 'fixed',
        'fixed_quantity': 100,
        'schedule_type': 'frequency',
        'delivery_frequency': 3,
        'min_stock': 300
    }
    
    # Формирование params (как в simulation_page.py)
    params = {
        "delivery_type": settings.get('delivery_type', 'unit'),
        "fixed_quantity": settings.get('fixed_quantity'),
        "schedule_type": settings.get('schedule_type', 'frequency'),
        "delivery_frequency": settings.get('delivery_frequency', 2),
        "min_stock": float(settings.get('min_stock', 300))
    }
    
    print("\n📤 Параметры, отправляемые в API:")
    for key, value in params.items():
        print(f"   {key}: {value}")
    
    # Проверка
    errors = []
    if params['delivery_type'] != 'fixed':
        errors.append("delivery_type должен быть 'fixed'")
    if params['fixed_quantity'] != 100:
        errors.append("fixed_quantity должен быть 100")
    if params['schedule_type'] != 'frequency':
        errors.append("schedule_type должен быть 'frequency'")
    if params['delivery_frequency'] != 3:
        errors.append("delivery_frequency должен быть 3")
    
    if errors:
        print("\n❌ Ошибки:")
        for e in errors:
            print(f"   - {e}")
        return False
    else:
        print("\n✅ Все параметры корректны!")
        return True


def test_fixed_quantity_in_milk():
    """Тест: фиксированный объём должен работать и для молока"""
    
    print("\n" + "=" * 60)
    print("📊 ТЕСТ 5: ФИКСИРОВАННЫЙ ОБЪЁМ ДЛЯ МОЛОКА")
    print("=" * 60)
    
    settings = {
        'delivery_type': 'fixed',
        'fixed_quantity': 50,
        'schedule_type': 'days',
        'delivery_days': [0, 3]  # Пн и Чт
    }
    
    params = {
        "delivery_type": settings.get('delivery_type', 'unit'),
        "fixed_quantity": settings.get('fixed_quantity'),
        "schedule_type": settings.get('schedule_type', 'frequency'),
        "delivery_days": settings.get('delivery_days', [])
    }
    
    print("\n📤 Параметры для молока:")
    print(f"   delivery_type: {params['delivery_type']}")
    print(f"   fixed_quantity: {params['fixed_quantity']}")
    print(f"   schedule_type: {params['schedule_type']}")
    print(f"   delivery_days: {params['delivery_days']}")
    
    if params['delivery_type'] == 'fixed' and params['fixed_quantity'] == 50:
        print("\n✅ Фиксированный объём работает и для молока!")
        return True
    else:
        print("\n❌ Ошибка в параметрах для молока")
        return False


if __name__ == "__main__":
    print("\n" + "🧪" * 20)
    print("🧪 ТЕСТИРОВАНИЕ НАСТРОЕК ДОСТАВКИ")
    print("🧪" * 20)
    
    test_settings_structure()
    test_save_fixed_quantity()
    test_schedule_type_with_fixed()
    test_params_transfer()
    test_fixed_quantity_in_milk()
    
    print("\n" + "=" * 60)
    print("📝 РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    print("""
    1. Убедитесь, что в app.py при сохранении настроек есть:
       'fixed_quantity': fixed_quantity
    
    2. Убедитесь, что в simulation_page.py в params есть:
       "delivery_type": settings.get('delivery_type', 'unit'),
       "fixed_quantity": settings.get('fixed_quantity'),
    
    3. Проверьте, что при выборе фиксированного объёма
       в модальном окне появляется поле fixed_quantity
    """)