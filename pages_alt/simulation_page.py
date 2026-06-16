"""
simulation_page.py - Главная страница симуляции

Содержит:
- Выбор товара из БД
- Отображение текущих настроек
- Запуск симуляции (через API)
- Отображение результатов (метрики, графики, таблицы)
- Сохранение эксперимента в БД

Взаимодействует с FastAPI бэкендом через HTTP-запросы.
"""


import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os
from io import BytesIO
from database.db_manager import DatabaseManager


def run_multiple_simulations(params, num_simulations, API_URL, days):
    """
    Запускает несколько симуляций (метод Монте-Карло).
    Возвращает усреднённые результаты + статистику (мин/макс/среднее/σ).
    """
    all_daily_histories = []
    all_metrics = []
    
    with st.spinner(f"Запуск {num_simulations} симуляций..."):
        progress_bar = st.progress(0)
        
        for i in range(num_simulations):
            try:
                response = requests.post(f"{API_URL}/simulate", json=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                all_daily_histories.append(data['daily_history'])
                all_metrics.append(data)
                progress_bar.progress((i + 1) / num_simulations)
            except Exception as e:
                st.error(f"Ошибка в симуляции {i+1}: {str(e)}")
                continue
    
    if not all_daily_histories:
        st.error("❌ Не удалось выполнить ни одной симуляции")
        return None
    
    # Извлекаем значения метрик для статистики
    revenues = [m['total_revenue'] for m in all_metrics]
    profits = [m['profit'] for m in all_metrics]
    unmet_demands = [sum(day.get('unmet_demand', 0) for day in m['daily_history']) for m in all_metrics]
    spoilage_kg = [m['total_spoilage_kg'] for m in all_metrics]
    costs = [m['total_cost'] for m in all_metrics]
    avg_stocks = [m.get('avg_stock', 0) for m in all_metrics]
    
    # Усредняем метрики
    avg_metrics = {
        'total_revenue': np.mean(revenues),
        'total_cost': np.mean(costs),
        'total_purchase_cost': np.mean([m.get('total_purchase_cost', 0) for m in all_metrics]),
        'total_delivery_cost': np.mean([m.get('total_delivery_cost', 0) for m in all_metrics]),
        'total_utilization_cost': np.mean([m.get('total_utilization_cost', 0) for m in all_metrics]),
        'total_spoilage_kg': np.mean(spoilage_kg),
        'total_spoilage_money': np.mean([m['total_spoilage_money'] for m in all_metrics]),
        'profit': np.mean(profits),
        'avg_stock': np.mean(avg_stocks),
        'std_profit': np.std(profits),
        'num_simulations': len(all_metrics),
        'stats': {
            'revenue': {'min': min(revenues), 'max': max(revenues), 'avg': np.mean(revenues)},
            'profit': {'min': min(profits), 'max': max(profits), 'avg': np.mean(profits)},
            'spoilage': {'min': min(spoilage_kg), 'max': max(spoilage_kg), 'avg': np.mean(spoilage_kg)},
            'cost': {'min': min(costs), 'max': max(costs), 'avg': np.mean(costs)},
            'avg_stock': {'min': min(avg_stocks), 'max': max(avg_stocks), 'avg': np.mean(avg_stocks)},
            'unmet_demand': {'min': min(unmet_demands), 'max': max(unmet_demands), 'avg': np.mean(unmet_demands)}
        }
    }

    # Усредняем дневные данные
    avg_daily_history = []
    for day_idx in range(days):
        day_avg = {}
        
        for key in ['demand', 'start_stock', 'sales', 'spoilage', 'order', 'revenue', 'purchase_cost', 'end_stock', 'unmet_demand']:
            values = []
            for hist in all_daily_histories:
                if day_idx < len(hist):
                    values.append(hist[day_idx].get(key, 0))
            day_avg[key] = np.mean(values) if values else 0
        
        for key in ['stock_week1', 'stock_week2', 'stock_week3']:
            values = []
            for hist in all_daily_histories:
                if day_idx < len(hist):
                    val = hist[day_idx].get(key, 0)
                    values.append(val if val is not None else 0)
            day_avg[key] = np.mean(values) if values else 0
        
        for key in ['fifo_percent', 'lifo_percent']:
            values = []
            for hist in all_daily_histories:
                if day_idx < len(hist):
                    val = hist[day_idx].get(key)
                    if val is not None:
                        values.append(val)
            day_avg[key] = np.mean(values) if values else None
        
        day_avg['day'] = day_idx + 1
        day_avg['date'] = all_daily_histories[0][day_idx]['date'] if all_daily_histories else ""
        
        avg_daily_history.append(day_avg)

    avg_metrics['daily_history'] = avg_daily_history
    avg_metrics['demand_stats'] = all_metrics[0].get('demand_stats', {}) if all_metrics else {}
    avg_metrics['spoilage_stats'] = all_metrics[0].get('spoilage_stats', {}) if all_metrics else {}
    
    return avg_metrics


def export_experiment_to_excel(db, id_experiment: int) -> BytesIO:
    """
    Выгружает эксперимент из БД в многостраничный Excel-отчёт.
    Формирует 5 листов: Метрики, 1. Общие настройки, 2. Стратегия поставок,
    3. Доставка, Детально по дням.
    """
    
    data = db.get_full_experiment_data(id_experiment)
    if not data:
        return None
    
    settings = data['settings']
    experiment = data['experiment']
    daily_history = data['daily_history']
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # ========== ЛИСТ 1: МЕТРИКИ ==========
        metrics_data = {
            'Показатель': [
                'ID эксперимента',
                'Товар',
                'Категория',
                'Стратегия поставок',
                'Дата сохранения',
                '',
                'Выручка (руб)',
                'Затраты на закупку (руб)',
                'Затраты на доставку (руб)',
                'Затраты на утилизацию (руб)',
                'Итого затраты (руб)',
                'Прибыль (руб)',
                '',
                'Потери от порчи (кг)',
                'Потери от порчи (руб)',
                'Неудовлетворённый спрос (кг)',
                'Средний остаток (кг)'
            ],
            'Значение': [
                id_experiment,
                settings.get('product_name'),
                "Строгий срок" if settings.get('product_category') == 'strict' else "Постепенная порча",
                settings.get('strategy_type'),
                experiment.get('created_at', ''),
                '',
                f"{experiment.get('total_revenue', 0):.2f}",
                f"{experiment.get('total_purchase_cost', 0):.2f}",
                f"{experiment.get('total_delivery_cost', 0):.2f}",
                f"{experiment.get('total_utilization_cost', 0):.2f}",
                f"{experiment.get('total_cost', 0):.2f}",
                f"{experiment.get('profit', 0):.2f}",
                '',
                f"{experiment.get('total_spoilage_kg', 0):.2f}",
                f"{experiment.get('total_spoilage_money', 0):.2f}",
                f"{experiment.get('total_unmet_demand', 0):.2f}",
                f"{experiment.get('avg_stock', 0):.2f}"
            ]
        }
        pd.DataFrame(metrics_data).to_excel(writer, sheet_name='Метрики', index=False)
        
        # ========== ЛИСТ 2: НАСТРОЙКИ (ВКЛАДКА 1 - ОБЩИЕ) ==========
        # Преобразуем weekday_factors
        weekday_factors = settings.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1])
        if isinstance(weekday_factors, str):
            import json
            weekday_factors = json.loads(weekday_factors)
        
        general_settings = {
            'Параметр': [
                'Товар',
                'Категория',
                'Цена закупки (руб)',
                'Цена продажи (руб)',
                'Срок годности (дней)',
                'Базовый спрос (ед/день)',
                '',
                'Закон распределения спроса',
                'Мин. спрос (равномерный)',
                'Макс. спрос (равномерный)',
                'Сигма (нормальный)',
                '',
                'Коэффициенты дней недели (Пн)',
                'Коэффициенты дней недели (Вт)',
                'Коэффициенты дней недели (Ср)',
                'Коэффициенты дней недели (Чт)',
                'Коэффициенты дней недели (Пт)',
                'Коэффициенты дней недели (Сб)',
                'Коэффициенты дней недели (Вс)',
                '',
                'Тип порчи',
                'Степень p (для степенной)',
                'Коэффициент k (для логистической)',
                '',
                'FIFO / LIFO',
                'Стоимость утилизации (руб/кг)',
                '',
                'Период симуляции (дней)',
                'Дата начала',
                'Дата окончания',
                'Количество прогонов (усреднение)',
                'Seed (воспроизводимость)'
            ],
            'Значение': [
                settings.get('product_name'),
                "Строгий срок" if settings.get('product_category') == 'strict' else "Постепенная порча",
                settings.get('purchase_price'),
                settings.get('sale_price'),
                settings.get('shelf_life_days'),
                settings.get('base_demand'),
                '',
                "Нормальный" if settings.get('distribution') == 'normal' else "Равномерный",
                settings.get('demand_min') if settings.get('demand_min') else "—",
                settings.get('demand_max') if settings.get('demand_max') else "—",
                settings.get('demand_sigma') if settings.get('demand_sigma') else "—",
                '',
                weekday_factors[0] if len(weekday_factors) > 0 else 0.8,
                weekday_factors[1] if len(weekday_factors) > 1 else 0.6,
                weekday_factors[2] if len(weekday_factors) > 2 else 0.9,
                weekday_factors[3] if len(weekday_factors) > 3 else 1.0,
                weekday_factors[4] if len(weekday_factors) > 4 else 1.3,
                weekday_factors[5] if len(weekday_factors) > 5 else 1.5,
                weekday_factors[6] if len(weekday_factors) > 6 else 1.1,
                '',
                settings.get('spoilage_type'),
                settings.get('power_p') if settings.get('power_p') else "—",
                settings.get('logistic_k') if settings.get('logistic_k') else "—",
                '',
                f"{settings.get('fifo_percent')}% FIFO / {100 - settings.get('fifo_percent', 75)}% LIFO" if settings.get('fifo_percent') else "—",
                settings.get('utilization_price') if settings.get('utilization_price') else 0,
                '',
                settings.get('days'),
                settings.get('start_date'),
                settings.get('end_date'),
                settings.get('num_simulations', 1),
                settings.get('random_seed', '—')
            ]
        }
        pd.DataFrame(general_settings).to_excel(writer, sheet_name='1. Общие настройки', index=False)
        
        # ========== ЛИСТ 3: НАСТРОЙКИ (ВКЛАДКА 2 - СТРАТЕГИЯ ПОСТАВОК) ==========
        # Преобразуем delivery_days
        delivery_days = settings.get('delivery_days', [])
        if isinstance(delivery_days, str):
            import json
            delivery_days = json.loads(delivery_days)
        
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        delivery_days_str = ", ".join([day_names[d] for d in delivery_days if d < 7]) if delivery_days else "—"
        
        strategy_names = {
            "r_s": "(R, S) — Периодическая до целевого уровня",
            "r_q": "(R, Q) — Фиксированный объём по расписанию",
            "s_s": "(s, S) — Двухуровневая (точка заказа)",
            "s_q": "(s, Q) — Двухуровневая с фиксированным объёмом",
            "custom": "Пользовательская"
        }
        
        schedule_names = {
            "frequency": "Периодичность (каждые N дней)",
            "days": "Конкретные дни недели"
        }
        
        delivery_settings = {
            'Параметр': [
                'Стратегия поставок',
                '',
                'Способ поставки',
                'Размер упаковки (кг/шт)',
                'Фиксированный объём заказа Q',
                '',
                'Тип расписания',
                'Периодичность (дней)',
                'Дни поставок',
                '',
                'Точка заказа s',
                'Максимальный запас S',
                'Целевой уровень запаса'
            ],
            'Значение': [
                strategy_names.get(settings.get('strategy_type', 'r_s'), settings.get('strategy_type')),
                '',
                "Коробками/ящиками" if settings.get('delivery_type') == 'box' else "Штучно" if settings.get('delivery_type') == 'unit' else "Фиксированный",
                settings.get('box_size', 0) if settings.get('box_size', 0) > 0 else "—",
                settings.get('fixed_quantity') if settings.get('fixed_quantity') else "—",
                '',
                schedule_names.get(settings.get('schedule_type'), "—") if settings.get('schedule_type') else "—",
                settings.get('delivery_frequency') if settings.get('delivery_frequency') else "—",
                delivery_days_str,
                '',
                settings.get('reorder_point') if settings.get('reorder_point') else "—",
                settings.get('max_stock') if settings.get('max_stock') else "—",
                settings.get('min_stock') if settings.get('min_stock') else "—"
            ]
        }
        pd.DataFrame(delivery_settings).to_excel(writer, sheet_name='2. Стратегия поставок', index=False)
        
        # ========== ЛИСТ 4: НАСТРОЙКИ (ВКЛАДКА 3 - ДОСТАВКА) ==========
        cost_type_names = {
            "none": "Не учитывать",
            "fixed": "Фиксированная (за одну поставку)",
            "rate": "Тариф за кг/шт",
            "combined": "Комбинированная (фикс + тариф)"
        }
        
        delivery_cost_settings = {
            'Параметр': [
                'Тип расчёта доставки',
                'Фиксированная стоимость (руб)',
                'Тариф за кг/шт (руб)',
                '',
                'Пример расчёта (при заказе 100 кг)'
            ],
            'Значение': [
                cost_type_names.get(settings.get('delivery_cost_type', 'none'), "Не учитывать"),
                settings.get('delivery_fixed_cost', 0) if settings.get('delivery_cost_type') in ['fixed', 'combined'] else "—",
                settings.get('delivery_rate_cost', 0) if settings.get('delivery_cost_type') in ['rate', 'combined'] else "—",
                '',
                f"{settings.get('delivery_fixed_cost', 0) + settings.get('delivery_rate_cost', 0) * 100:.2f} руб" if settings.get('delivery_cost_type') != 'none' else "—"
            ]
        }
        pd.DataFrame(delivery_cost_settings).to_excel(writer, sheet_name='3. Доставка', index=False)
        
        # ========== ЛИСТ 5: ДЕТАЛЬНАЯ ИСТОРИЯ ПО ДНЯМ (РУССКИЕ КОЛОНКИ) ==========
        if not daily_history.empty:
            # Переименовываем колонки на русские
            column_names_ru = {
                'day': 'День',
                'date': 'Дата',
                'demand': 'Спрос',
                'start_stock': 'Остаток на начало',
                'sales': 'Продажи',
                'spoilage_kg': 'Порча',
                'order_qty': 'Поставка',
                'revenue': 'Выручка (руб)',
                'purchase_cost': 'Затраты на закупку (руб)',
                'end_stock': 'Остаток на конец',
                'unmet_demand': 'Неудовлетворённый спрос',
                'fifo_percent': 'FIFO (%)',
                'lifo_percent': 'LIFO (%)',
                'stock_week1': 'Остаток 0-7 дней',
                'stock_week2': 'Остаток 8-14 дней',
                'stock_week3': 'Остаток 15+ дней'
            }
            
            # Переименовываем только существующие колонки
            daily_history_ru = daily_history.rename(columns={k: v for k, v in column_names_ru.items() if k in daily_history.columns})
            daily_history_ru.to_excel(writer, sheet_name='Детально по дням', index=False)
    
    output.seek(0)
    return output


def save_complete_experiment(results, params, daily_history_df, db):
    """
    Сохраняет эксперимент целиком:
    1. Настройки → experiment_settings
    2. Метрики → experiments
    3. История по дням → experiment_daily_history
    
    Генерирует случайный seed для воспроизводимости.
    """
    
    import random
    
    # Получаем id_product
    id_product = db.get_product_id_by_name(results['selected_product_name'])
    
    # Генерируем seed
    random_seed = random.randint(1, 1000000)
    
    # Определяем даты
    start_date = params.get('start_date')
    end_date = None
    if start_date and results.get('days'):
        start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
        end_dt = start_dt + timedelta(days=results['days'] - 1)
        end_date = end_dt.strftime('%Y-%m-%d')
        start_date = start_dt.strftime('%Y-%m-%d')
    
    # 1. Сохраняем настройки
    settings = {
        'id_product': id_product,
        'product_name': results['selected_product_name'],
        'purchase_price': params.get('purchase_price'),
        'sale_price': params.get('sale_price'),
        'shelf_life_days': params.get('shelf_life_days'),
        'base_demand': params.get('base_demand', 100),
        'product_category': results['product_category'],
        'distribution': params.get('distribution', 'uniform'),
        'demand_min': params.get('demand_min'),
        'demand_max': params.get('demand_max'),
        'demand_sigma': params.get('demand_sigma'),
        'weekday_factors': params.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]),
        'spoilage_type': params.get('spoilage_type', 'linear'),
        'power_p': params.get('power_p'),
        'logistic_k': params.get('logistic_k'),
        'strategy_type': params.get('strategy_type', 'r_s'),
        'delivery_type': params.get('delivery_type', 'unit'),
        'box_size': params.get('box_size', 0),
        'fixed_quantity': params.get('fixed_quantity'),
        'schedule_type': params.get('schedule_type'),
        'delivery_frequency': params.get('delivery_frequency'),
        'delivery_days': params.get('delivery_days', []),
        'reorder_point': params.get('reorder_point'),
        'max_stock': params.get('max_stock'),
        'min_stock': params.get('min_stock'),
        'delivery_cost_type': params.get('delivery_cost_type', 'none'),
        'delivery_fixed_cost': params.get('delivery_fixed_cost', 0),
        'delivery_rate_cost': params.get('delivery_rate_cost', 0),
        'fifo_percent': params.get('fifo_percent'),
        'utilization_price': params.get('utilization_price', 0),
        'days': results['days'],
        'start_date': start_date,
        'end_date': end_date,
        'num_simulations': results.get('num_simulations', 1),
        'random_seed': random_seed
    }
    
    id_setting = db.save_settings(settings)
    
    # 2. Сохраняем метрики
    data = results['data']
    experiment_data = {
        'id_setting': id_setting,
        'total_revenue': data['total_revenue'],
        'total_cost': data['total_cost'],
        'total_purchase_cost': data.get('total_purchase_cost', 0),
        'total_delivery_cost': data.get('total_delivery_cost', 0),
        'total_utilization_cost': data.get('total_utilization_cost', 0),
        'total_spoilage_kg': data['total_spoilage_kg'],
        'total_spoilage_money': data['total_spoilage_money'],
        'profit': data['profit'],
        'avg_stock': data.get('avg_stock', 0),
        'total_unmet_demand': results['total_unmet']
    }
    
    id_experiment = db.save_experiment(experiment_data)
    
    # 3. Сохраняем историю по дням
    daily_list = daily_history_df.to_dict('records')
    db.save_daily_history_batch(id_experiment, daily_list)
    
    return id_experiment


def show(settings_dialog=None):
    """
    Главная функция страницы симуляции.
    Отвечает за интерфейс: выбор товара, кнопка настроек, кнопка запуска.
    После запуска вызывает display_simulation_results для отображения.
    """
    
    # Инициализация флагов (только один раз, при первом запуске)
    if 'simulation_started' not in st.session_state:
        st.session_state.show_add_modal = False
        st.session_state.show_edit_modal = False
        st.session_state.show_clear_modal = False
        st.session_state.simulation_started = True

    API_URL = "http://127.0.0.1:8000"
    db = DatabaseManager()
    
    # Инициализация состояния сессии
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    if 'last_saved_experiment_id' not in st.session_state:
        st.session_state.last_saved_experiment_id = None
    
    # Получаем список товаров из БД
    products_df = db.get_all_products()
    if products_df.empty:
        st.error("❌ Нет товаров в базе данных. Добавьте товары во вкладке «База данных»")
        return
    
    # ===== ДВЕ КОЛОНКИ: выбор продукта (широкая) и кнопка настроек (узкая) =====
    col_product, col_settings = st.columns([5, 1])
    
    with col_product:
        selected_product_name = st.selectbox(
            "📦 Выберите продукт",
            options=products_df['name'].tolist(),
            key="sim_product"
        )
    
    with col_settings:
        st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
        if settings_dialog and st.button("⚙️ Настройки", help="Открыть общие настройки", use_container_width=True):
            settings_dialog()
    
    # Получаем выбранный продукт
    selected_product = products_df[products_df['name'] == selected_product_name].iloc[0]
    product_category = selected_product['category']
    
    st.session_state.current_base_demand = selected_product['base_demand']
    st.session_state.current_product_category = product_category
    
    st.markdown("---")
    
    # ========== ОПРЕДЕЛЕНИЕ ДАТ СИМУЛЯЦИИ ==========
    settings = st.session_state.get('settings', {})
    use_real_demand = st.session_state.get('use_real_demand', False)
    real_start_date = st.session_state.get('real_start_date')
    real_demand_dates = st.session_state.get('real_demand_dates')
    
    if use_real_demand and real_start_date and real_demand_dates:
        start_date = datetime.fromisoformat(real_start_date)
        days = len(real_demand_dates)
    else:
        sim_start_date = settings.get('sim_start_date', '2026-02-01')
        sim_end_date = settings.get('sim_end_date', '2026-03-03')
        start_date = datetime.strptime(sim_start_date, '%Y-%m-%d')
        end_date = datetime.strptime(sim_end_date, '%Y-%m-%d')
        days = (end_date - start_date).days + 1
    
    # ========== ДВА КОНТЕЙНЕРА РЯДОМ ==========
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📋 Информация о товаре")
        
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            st.metric("💰 Цена закупки", f"{selected_product['purchase_price']:.2f} руб")
        with row1_col2:
            st.metric("💰 Цена продажи", f"{selected_product['sale_price']:.2f} руб")
        
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            st.metric("📅 Срок годности", f"{selected_product['shelf_life_days']} дней")
        with row2_col2:
            st.metric("📊 Базовый спрос", f"{selected_product['base_demand']:.0f} ед/день")
    
    with col_right:
        st.subheader("⚙️ Текущие настройки")
        
        if use_real_demand and real_start_date and real_demand_dates:
            start_date_dt = datetime.fromisoformat(real_start_date)
            end_date_dt = start_date_dt + timedelta(days=len(real_demand_dates) - 1)
            days_count = len(real_demand_dates)
            st.markdown(f"**📅 Период:** {start_date_dt.strftime('%d.%m.%Y')} — {end_date_dt.strftime('%d.%m.%Y')} ({days_count} дн)")
        else:
            sim_start_date = settings.get('sim_start_date', '2026-02-01')
            sim_end_date = settings.get('sim_end_date', '2026-03-03')
            start_date_dt = datetime.strptime(sim_start_date, '%Y-%m-%d')
            end_date_dt = datetime.strptime(sim_end_date, '%Y-%m-%d')
            days_count = (end_date_dt - start_date_dt).days + 1
            st.markdown(f"**📅 Период:** {start_date_dt.strftime('%d.%m.%Y')} — {end_date_dt.strftime('%d.%m.%Y')} ({days_count} дн)")
        
        distribution = settings.get('distribution', 'uniform')
        dist_text = "Равномерный" if distribution == "uniform" else "Нормальный"
        st.markdown(f"**📊 Спрос:** {dist_text}")
        
        factors = settings.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1])
        st.markdown(f"**📅 Коэфф.:** Пн{factors[0]:.1f} Вт{factors[1]:.1f} Ср{factors[2]:.1f} Чт{factors[3]:.1f} Пт{factors[4]:.1f} Сб{factors[5]:.1f} Вс{factors[6]:.1f}")
        
        if product_category == "strict":
            fifo = settings.get('fifo_percent', 75)
            st.markdown(f"**👥 Покупатели:** FIFO {fifo}% / LIFO {100-fifo}%")
        else:
            spoilage_type = settings.get('spoilage_type', 'linear')
            spoilage_names = {"linear": "Линейная", "power": "Степенная", "logistic": "Логистическая"}
            spoilage_text = spoilage_names.get(spoilage_type, "Линейная")
            if spoilage_type == "power":
                p = settings.get('power_p', 2.0)
                spoilage_text += f" (p={p:.1f})"
            elif spoilage_type == "logistic":
                k = settings.get('logistic_k', 15.0)
                spoilage_text += f" (k={k:.0f})"
            st.markdown(f"**🕐 Порча:** {spoilage_text}")
        
        strategy_type = settings.get('strategy_type', 'r_s')
        strategy_names = {
            "r_s": "(R, S) — до целевого уровня",
            "r_q": "(R, Q) — фиксированный объём",
            "s_s": "(s, S) — точка заказа",
            "s_q": "(s, Q) — фиксированный объём по точке заказа",
            "custom": "Пользовательская"
        }
        st.markdown(f"**🚚 Стратегия:** {strategy_names.get(strategy_type, '(R, S)')}")
        
        cost_type = settings.get('delivery_cost_type', 'none')
        if cost_type == 'none':
            st.markdown("**💰 Доставка:** ❌ Не учитывается")
        elif cost_type == 'fixed':
            st.markdown(f"**💰 Доставка:** Фикс {settings.get('delivery_fixed_cost', 500):.0f} руб")
        elif cost_type == 'rate':
            st.markdown(f"**💰 Доставка:** Тариф {settings.get('delivery_rate_cost', 5):.0f} руб/кг")
        else:
            st.markdown(f"**💰 Доставка:** Фикс {settings.get('delivery_fixed_cost', 200):.0f} + {settings.get('delivery_rate_cost', 3):.0f} руб/кг")
    
    # ========== КНОПКА ЗАПУСКА ==========
    st.markdown("---")
    
    if st.button("🚀 Запустить симуляцию", type="primary", use_container_width=True):
        st.session_state.show_view_dialog = False
        st.session_state.show_delete_modal = False
        st.session_state.show_add_modal = False
        st.session_state.show_edit_modal = False
        st.session_state.show_clear_modal = False
        st.session_state.view_experiment_data = None
        st.session_state.delete_exp_id = None
        st.session_state.delete_exp_name = None
        with st.spinner("Симуляция выполняется..."):
            settings = st.session_state.get('settings', {})
            
            distribution = settings.get('distribution', 'uniform')
            demand_min = settings.get('demand_min')
            demand_max = settings.get('demand_max')
            spoilage_type = settings.get('spoilage_type', 'linear')
            power_p = settings.get('power_p', 2.0)
            logistic_k = settings.get('logistic_k', 15.0)
            fifo_percent = settings.get('fifo_percent', 75)
            delivery_type = settings.get('delivery_type', 'unit')
            box_size = settings.get('box_size', 0)
            fixed_quantity = settings.get('fixed_quantity')
            schedule_type = settings.get('schedule_type', 'frequency')
            delivery_frequency = settings.get('delivery_frequency', 2)
            delivery_days = settings.get('delivery_days', [])
            reorder_point = settings.get('reorder_point')
            max_stock = settings.get('max_stock')
            min_stock_setting = settings.get('min_stock', 300)
            delivery_cost_type = settings.get('delivery_cost_type', 'none')
            delivery_fixed_cost = settings.get('delivery_fixed_cost', 0.0)
            delivery_rate_cost = settings.get('delivery_rate_cost', 0.0)
            strategy_type = settings.get('strategy_type', 'r_s')
            num_simulations = settings.get('num_simulations', 1)
            
            use_real_demand = st.session_state.get('use_real_demand', False)
            real_demand_dates = st.session_state.get('real_demand_dates')
            real_demand_values = st.session_state.get('real_demand_values')
            real_start_date = st.session_state.get('real_start_date')
            
            if use_real_demand and real_start_date and real_demand_dates:
                start_date = datetime.fromisoformat(real_start_date)
                days = len(real_demand_dates)
            
            if strategy_type == "r_s":
                min_stock = min_stock_setting
                final_fixed_quantity = None
                final_reorder_point = None
                final_max_stock = None
                final_delivery_type = delivery_type
                final_box_size = box_size
            elif strategy_type == "r_q":
                min_stock = 0
                final_fixed_quantity = fixed_quantity
                final_reorder_point = None
                final_max_stock = None
                final_delivery_type = "fixed"
                final_box_size = 0
            elif strategy_type == "s_s":
                min_stock = max_stock if max_stock else 300
                final_fixed_quantity = None
                final_reorder_point = reorder_point
                final_max_stock = max_stock
                final_delivery_type = delivery_type
                final_box_size = box_size
            elif strategy_type == "s_q":
                min_stock = 0
                final_fixed_quantity = fixed_quantity
                final_reorder_point = reorder_point
                final_max_stock = None
                final_delivery_type = delivery_type
                final_box_size = box_size
            else:
                min_stock = min_stock_setting
                final_fixed_quantity = fixed_quantity
                final_reorder_point = reorder_point
                final_max_stock = max_stock
                final_delivery_type = delivery_type
                final_box_size = box_size
            
            params = {
                "days": days,
                "min_stock": float(min_stock),
                "purchase_price": float(selected_product['purchase_price']),
                "sale_price": float(selected_product['sale_price']),
                "distribution": distribution,
                "strategy_type": strategy_type,
                "weekday_factors": settings.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]),
                "spoilage_type": spoilage_type,
                "shelf_life_days": int(selected_product['shelf_life_days']),
                "power_p": power_p if spoilage_type == "power" else None,
                "logistic_k": logistic_k if spoilage_type == "logistic" else None,
                "demand_min": demand_min,
                "demand_max": demand_max,
                "delivery_type": final_delivery_type,
                "box_size": final_box_size,
                "fixed_quantity": final_fixed_quantity,
                "schedule_type": schedule_type,
                "delivery_frequency": delivery_frequency if schedule_type == "frequency" else 0,
                "delivery_days": delivery_days if schedule_type == "days" else [],
                "reorder_point": final_reorder_point,
                "max_stock": final_max_stock,
                "delivery_cost_type": delivery_cost_type,
                "delivery_fixed_cost": delivery_fixed_cost,
                "delivery_rate_cost": delivery_rate_cost,
                "product_type": "milk" if product_category == "strict" else "tomatoes",
                "start_date": start_date.isoformat(),
                "product_name": selected_product_name,
                "fifo_percent": float(fifo_percent) if product_category == "strict" else None,
                "lifo_percent": float(100 - fifo_percent) if product_category == "strict" else None,
                "utilization_price": settings.get('utilization_price', 5.0),
                "sigma_buyer": 1.51 if product_category == "strict" else None,
                "use_real_demand": use_real_demand,
                "real_demand_dates": real_demand_dates if use_real_demand else None,
                "real_demand_values": real_demand_values if use_real_demand else None,
                "real_start_date": real_start_date if use_real_demand else None,
            }
            
            try:
                if num_simulations > 1:
                    data = run_multiple_simulations(params, num_simulations, API_URL, days)
                    if data is None:
                        return
                    total_unmet = sum(day.get('unmet_demand', 0) for day in data['daily_history'])
                    st.info(f"📊 Результаты усреднены по {num_simulations} симуляциям")
                else:
                    response = requests.post(f"{API_URL}/simulate", json=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    total_unmet = sum(day.get('unmet_demand', 0) for day in data['daily_history'])
                
                st.session_state.simulation_results = {
                    'data': data,
                    'total_unmet': total_unmet,
                    'params': params,
                    'distribution': distribution,
                    'product_category': product_category,
                    'selected_product_name': selected_product_name,
                    'days': days,
                    'min_stock': min_stock,
                    'spoilage_type': spoilage_type,
                    'fifo_percent': fifo_percent,
                    'num_simulations': num_simulations,
                    'std_profit': data.get('std_profit', 0) if num_simulations > 1 else 0
                }
                st.session_state.last_saved_experiment_id = None
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")
    
    # Отображение результатов
    if st.session_state.simulation_results:
        display_simulation_results(st.session_state.simulation_results, db)


def display_simulation_results(results, db):
    """
    Отображает результаты симуляции:
    - 6 метрик (выручка, затраты, прибыль, потери, неуд.спрос, средний остаток)
    - 4 графика (спрос/продажи, остатки, порча, поставки)
    - 2 гистограммы (распределение спроса, распределение FIFO)
    - Детальная таблица по дням
    
    Также содержит кнопку "Сохранить эксперимент".
    """
    if results is None:
        return

    data = results['data']
    total_unmet = results['total_unmet']
    params = results['params']
    distribution = results['distribution']
    product_category = results['product_category']
    selected_product_name = results['selected_product_name']
    days = results['days']
    min_stock = results['min_stock']
    spoilage_type = results.get('spoilage_type', 'linear')
    fifo_percent = results.get('fifo_percent', 75)
    num_simulations = results.get('num_simulations', 1)
    std_profit = results.get('std_profit', 0)
    
    if num_simulations > 1:
        st.info(f"📊 Результаты усреднены по {num_simulations} симуляциям | Стандартное отклонение прибыли: ±{std_profit:.0f} руб")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💾 Сохранить эксперимент", use_container_width=True):
            if st.session_state.last_saved_experiment_id is not None:
                st.warning("⚠️ Этот эксперимент уже сохранён!")
            else:
                try:
                    df = pd.DataFrame(data['daily_history'])
                    id_exp = save_complete_experiment(results, params, df, db)
                    st.session_state.last_saved_experiment_id = id_exp
                    st.success(f"✅ Эксперимент сохранён! ID: {id_exp}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка сохранения: {e}")
    
    if st.session_state.last_saved_experiment_id is not None:
        st.info(f"✅ Эксперимент сохранён в БД (ID: {st.session_state.last_saved_experiment_id})")
    
    # ========== МЕТРИКИ ==========
    st.markdown("---")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("Выручка", f"{data['total_revenue']:,.0f} руб")

    with col2:
        st.metric("Затраты", f"{data['total_cost']:,.0f} руб")
        st.caption(f"├ Закупка: {data.get('total_purchase_cost', 0):,.0f} руб")
        st.caption(f"├ Доставка: {data.get('total_delivery_cost', 0):,.0f} руб")
        st.caption(f"└ Утилизация: {data.get('total_utilization_cost', 0):,.0f} руб")

    with col3:
        st.metric("Прибыль", f"{data['profit']:,.0f} руб")

    with col4:
        st.metric("Потери", f"{data['total_spoilage_kg']:.1f} кг")

    with col5:
        st.metric("Неудовлетворенный спрос", f"{total_unmet:.0f} кг")

    with col6:
        st.metric("📦 Средний остаток", f"{data.get('avg_stock', 0):.1f} кг")
    
    # ========== СТАТИСТИКА ПО СИМУЛЯЦИЯМ ==========
    if num_simulations > 1 and 'stats' in data:
        st.markdown("---")
        st.subheader("📊 Статистика по результатам симуляций")
        
        stats = data['stats']
        
        stats_df = pd.DataFrame([
            {'Метрика': 'Выручка (руб)', 
             'Минимум': f"{stats['revenue']['min']:,.0f}",
             'Среднее': f"{stats['revenue']['avg']:,.0f}",
             'Максимум': f"{stats['revenue']['max']:,.0f}"},
            
            {'Метрика': 'Прибыль (руб)', 
             'Минимум': f"{stats['profit']['min']:,.0f}",
             'Среднее': f"{stats['profit']['avg']:,.0f}",
             'Максимум': f"{stats['profit']['max']:,.0f}"},
            
            {'Метрика': 'Затраты (руб)', 
             'Минимум': f"{stats['cost']['min']:,.0f}",
             'Среднее': f"{stats['cost']['avg']:,.0f}",
             'Максимум': f"{stats['cost']['max']:,.0f}"},
            
            {'Метрика': 'Потери (кг)', 
             'Минимум': f"{stats['spoilage']['min']:.1f}",
             'Среднее': f"{stats['spoilage']['avg']:.1f}",
             'Максимум': f"{stats['spoilage']['max']:.1f}"},
            
            {'Метрика': 'Средний остаток (кг)', 
             'Минимум': f"{stats['avg_stock']['min']:.1f}",
             'Среднее': f"{stats['avg_stock']['avg']:.1f}",
             'Максимум': f"{stats['avg_stock']['max']:.1f}"},
            
            {'Метрика': 'Неудовлетворённый спрос (кг)', 
             'Минимум': f"{stats.get('unmet_demand', {}).get('min', 0):.0f}",
             'Среднее': f"{stats.get('unmet_demand', {}).get('avg', 0):.0f}",
             'Максимум': f"{stats.get('unmet_demand', {}).get('max', 0):.0f}"},
        ])
        
        st.dataframe(stats_df, hide_index=True, use_container_width=True)
    
    # ========== ПОДГОТОВКА ДАННЫХ ==========
    df = pd.DataFrame(data['daily_history'])
    df['day'] = pd.to_numeric(df['day'])
    
    if 'spoilage' in df.columns and 'spoilage_kg' not in df.columns:
        df['spoilage_kg'] = df['spoilage']
    if 'order' not in df.columns:
        df['order'] = 0
    
    # ========== ГРАФИКИ ==========
    st.markdown("---")
    st.subheader("📈 Динамика спроса и продаж")
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df['day'], y=df['demand'], name='Спрос', 
                              line=dict(color='#2E86AB', width=3), mode='lines+markers'))
    fig1.add_trace(go.Scatter(x=df['day'], y=df['sales'], name='Продажи', 
                              line=dict(color='#E74C3C', width=3), mode='lines+markers'))
    fig1.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Количество (кг/шт)")
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("📊 Динамика остатков на складе")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df['day'], y=df['start_stock'], name='Остаток на начало дня',
                              line=dict(color='#3498DB', width=2)))
    fig2.add_trace(go.Scatter(x=df['day'], y=df['end_stock'], name='Остаток на конец дня',
                              line=dict(color='#2ECC71', width=3)))
    fig2.add_hline(y=min_stock, line_dash="dash", line_color="red", 
                   annotation_text=f"Мин. запас: {min_stock}")
    fig2.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Остаток (кг/шт)")
    st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("🗑️ Динамика порчи")
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=df['day'], y=df['spoilage_kg'], name='Порча', 
                          marker_color='#E74C3C', opacity=0.7))
    fig3.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Порча (кг/шт)")
    st.plotly_chart(fig3, use_container_width=True)
    
    st.subheader("🚚 Поставки")
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=df['day'], y=df['order'], name='Поставки', 
                          marker_color='#27AE60', opacity=0.7))
    fig4.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Объём поставки")
    st.plotly_chart(fig4, use_container_width=True)
    
    # ========== ГИСТОГРАММЫ ==========
    st.markdown("---")
    st.subheader("📊 Анализ распределений")
    
    col_hist1, col_hist2 = st.columns(2)
    with col_hist1:
        fig_hist = px.histogram(
            df, 
            x='demand', 
            nbins=15, 
            title="Распределение спроса",
            labels={'demand': 'Спрос (кг/шт)', 'count': 'Частота'},  
            template='plotly_white'
        )
        # Обновляем подсказки при наведении
        fig_hist.update_traces(
            hovertemplate='<b>Спрос</b>: %{x:.1f} кг/шт<br><b>Частота</b>: %{y} д.<extra></extra>'
        )
        fig_hist.add_vline(
            x=df['demand'].mean(), 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Среднее: {df['demand'].mean():.2f}"
        )
        fig_hist.update_layout(
            xaxis_title="Спрос (кг/шт)",
            yaxis_title="Частота (количество дней)"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_hist2:
        if product_category == "strict" and 'spoilage_stats' in data:
            fifo_rates = data['spoilage_stats'].get('fifo_rates', [])
            if fifo_rates:
                fig_fifo = px.histogram(
                    x=fifo_rates, 
                    nbins=15, 
                    title=f"Распределение FIFO (ожидаемый {fifo_percent}%)",
                    labels={'x': 'Процент FIFO покупателей (%)', 'count': 'Частота'},  
                    template='plotly_white'
                )
                # Обновляем подсказки при наведении
                fig_fifo.update_traces(
                    hovertemplate='<b>FIFO</b>: %{x:.1f}%<br><b>Частота</b>: %{y} дней<extra></extra>'
                )
                fig_fifo.add_vline(x=fifo_percent, line_dash="dash", line_color="red")
                fig_fifo.update_layout(
                    xaxis_title="Процент FIFO покупателей (%)",
                    yaxis_title="Частота (количество дней)"
                )
                st.plotly_chart(fig_fifo, use_container_width=True)
    
    # Возрастная структура для gradual продуктов
    if product_category != "strict":
        st.subheader("📊 Структура остатков по возрасту")
        
        if 'stock_week1' in df.columns and 'stock_week2' in df.columns and 'stock_week3' in df.columns:
            age_df = pd.DataFrame()
            age_df['День'] = df['day']
            age_df['0-7 дней'] = df['stock_week1']
            age_df['8-14 дней'] = df['stock_week2']
            age_df['15+ дней'] = df['stock_week3']
            
            fig_age = go.Figure()
            fig_age.add_trace(go.Scatter(x=age_df['День'], y=age_df['0-7 дней'], name='0-7 дней',
                                         line=dict(color='#2ECC71', width=2), fill='tozeroy'))
            fig_age.add_trace(go.Scatter(x=age_df['День'], y=age_df['8-14 дней'], name='8-14 дней',
                                         line=dict(color='#F39C12', width=2), fill='tozeroy'))
            fig_age.add_trace(go.Scatter(x=age_df['День'], y=age_df['15+ дней'], name='15+ дней',
                                         line=dict(color='#E74C3C', width=2), fill='tozeroy'))
            fig_age.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Остаток (кг)")
            st.plotly_chart(fig_age, use_container_width=True)
    
    # ========== СТАТИСТИКА ==========
    st.markdown("---")
    col_stats1, col_stats2 = st.columns(2)
    with col_stats1:
        st.subheader("📊 Статистика спроса")
        if 'demand_stats' in data:
            stats = data['demand_stats']
            st.write(f"**Среднее:** {stats.get('mean', 0):.2f}")
            st.write(f"**Минимум:** {stats.get('min', 0):.2f}")
            st.write(f"**Максимум:** {stats.get('max', 0):.2f}")
    with col_stats2:
        st.subheader("🗑️ Статистика порчи")
        if product_category == "strict":
            if 'spoilage_stats' in data:
                s = data['spoilage_stats']
                st.write(f"**FIFO среднее:** {s.get('fifo_mean', 0):.2f}%")
                st.write(f"**LIFO среднее:** {s.get('lifo_mean', 0):.2f}%")
        else:
            total_spoilage = data.get('total_spoilage_kg', 0)
            avg_daily_spoilage = total_spoilage / days if days > 0 else 0
            st.write(f"**Всего потеряно:** {total_spoilage:.2f} кг")
            st.write(f"**В среднем в день:** {avg_daily_spoilage:.2f} кг")
    
    # ========== ПОЛНАЯ ТАБЛИЦА ==========
    with st.expander("📋 Детальная история по дням"):
        df_display = df.copy()
        
        columns_to_drop = ['fifo_sales', 'lifo_sales', 'total_sales', 'life_sales', 'spoilage_money']
        for col in columns_to_drop:
            if col in df_display.columns:
                df_display = df_display.drop(columns=[col])
        
        if 'spoilage' in df_display.columns and 'spoilage_kg' in df_display.columns:
            df_display = df_display.drop(columns=['spoilage'])
        
        if 'spoilage_kg' in df_display.columns and 'Порча % от остатка' not in df_display.columns:
            if 'start_stock' in df_display.columns:
                df_display['Порча % от остатка'] = df_display.apply(
                    lambda row: round((row['spoilage_kg'] / row['start_stock'] * 100), 2) 
                    if row['start_stock'] > 0 else 0, axis=1
                )
        
        base_columns = ['day', 'date', 'demand', 'start_stock', 'sales']
        middle_columns = ['spoilage_kg', 'Порча % от остатка', 'order']
        remaining_columns = [col for col in df_display.columns if col not in base_columns + middle_columns + ['day', 'date']]
        
        ordered_columns = base_columns + middle_columns + remaining_columns
        df_display = df_display[[col for col in ordered_columns if col in df_display.columns]]
 
        if product_category == "strict":
            milk_cols = ['stock_week1', 'stock_week2', 'stock_week3']
            for col in milk_cols:
                if col in df_display.columns:
                    df_display = df_display.drop(columns=[col])
            
            column_names = {
                'day': 'День',
                'date': 'Дата',
                'demand': 'Спрос (пакеты)',
                'start_stock': 'Остаток на начало (пакеты)',
                'sales': 'Продажи (пакеты)',
                'spoilage_kg': 'Порча (пакеты)',
                'Порча % от остатка': 'Порча % от остатка',
                'order': 'Заказ (пакеты)',
                'unmet_demand': 'Неудовлетворенный спрос (пакеты)',
                'revenue': 'Выручка (руб)',
                'purchase_cost': 'Затраты на закупку (руб)',
                'utilization_cost': 'Затраты на утилизацию (руб)',
                'end_stock': 'Остаток на конец (пакеты)',
                'fifo_percent': 'FIFO %',
                'lifo_percent': 'LIFO %'
            }
            
            batch_cols = ['batch_1_stock', 'batch_2_stock', 'batch_3_stock', 'batch_4_stock', 'batch_5_stock']
            for i, col in enumerate(batch_cols, 1):
                if col in df_display.columns:
                    column_names[col] = f'Партия {i}'
        else:
            tomato_cols = ['fifo_percent', 'lifo_percent', 'utilization_cost', 
                        'batch_1_stock', 'batch_2_stock', 'batch_3_stock', 
                        'batch_4_stock', 'batch_5_stock', 'fifo_sales', 'lifo_sales']
            for col in tomato_cols:
                if col in df_display.columns:
                    df_display = df_display.drop(columns=[col])
            
            column_names = {
                'day': 'День',
                'date': 'Дата',
                'demand': 'Спрос (кг)',
                'start_stock': 'Остаток на начало (кг)',
                'sales': 'Продажи (кг)',
                'spoilage_kg': 'Порча (кг)',
                'Порча % от остатка': 'Порча % от остатка',
                'order': 'Заказ (кг)',
                'unmet_demand': 'Неудовлетворенный спрос (кг)',
                'revenue': 'Выручка (руб)',
                'purchase_cost': 'Затраты на закупку (руб)',
                'end_stock': 'Остаток на конец (кг)',
                'stock_week1': 'Остаток 0-7 дней (кг)',
                'stock_week2': 'Остаток 8-14 дней (кг)',
                'stock_week3': 'Остаток 15+ дней (кг)'
            }
        
        existing_columns = {k: v for k, v in column_names.items() if k in df_display.columns}
        df_display = df_display.fillna(0)
        df_display = df_display.rename(columns=existing_columns)
        
        st.dataframe(df_display, use_container_width=True)
