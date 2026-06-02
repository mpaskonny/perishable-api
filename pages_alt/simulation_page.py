import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os
from database.db_manager import DatabaseManager

def show():
    """Страница симуляции"""
    
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
    
    # Выбор товара
    selected_product_name = st.selectbox(
        "📦 Выберите продукт",
        options=products_df['name'].tolist(),
        key="sim_product"
    )
    
    selected_product = products_df[products_df['name'] == selected_product_name].iloc[0]
    product_category = selected_product['category']
    
    # ========== СОХРАНЯЕМ ПАРАМЕТРЫ В SESSION_STATE ==========
    st.session_state.current_base_demand = selected_product['base_demand']
    st.session_state.current_product_category = product_category
    
    st.markdown("---")
    
    # ========== ОПРЕДЕЛЕНИЕ ДАТ СИМУЛЯЦИИ ==========
    settings = st.session_state.get('settings', {})
    use_real_demand = st.session_state.get('use_real_demand', False)
    real_start_date = st.session_state.get('real_start_date')
    real_demand_dates = st.session_state.get('real_demand_dates')
    
    if use_real_demand and real_start_date and real_demand_dates:
        # Используем даты из загруженного Excel
        start_date = datetime.fromisoformat(real_start_date)
        end_date = start_date + timedelta(days=len(real_demand_dates) - 1)
        days = len(real_demand_dates)
    else:
        # Используем даты из настроек (сохранённые пользователем)
        sim_start_date = settings.get('sim_start_date', '2026-02-01')
        sim_end_date = settings.get('sim_end_date', '2026-03-03')
        start_date = datetime.strptime(sim_start_date, '%Y-%m-%d')
        end_date = datetime.strptime(sim_end_date, '%Y-%m-%d')
        days = (end_date - start_date).days + 1
    
    # ========== ДВА КОНТЕЙНЕРА РЯДОМ ==========
    col_left, col_right = st.columns(2)
    
    # ===== ЛЕВЫЙ КОНТЕЙНЕР: Информация о товаре =====
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
    
    # ===== ПРАВЫЙ КОНТЕЙНЕР: Краткая сводка настроек =====
    with col_right:
        st.subheader("⚙️ Текущие настройки")
        
        # Период
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
        
        # Спрос
        distribution = settings.get('distribution', 'uniform')
        dist_text = "Равномерный" if distribution == "uniform" else "Нормальный"
        st.markdown(f"**📊 Спрос:** {dist_text}")
        
        # Коэффициенты дней недели (кратко)
        factors = settings.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1])
        st.markdown(f"**📅 Коэфф.:** Пн{factors[0]:.1f} Вт{factors[1]:.1f} Ср{factors[2]:.1f} Чт{factors[3]:.1f} Пт{factors[4]:.1f} Сб{factors[5]:.1f} Вс{factors[6]:.1f}")
        
        # Порча или FIFO/LIFO
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
        
        # Стратегия поставок
        strategy_type = settings.get('strategy_type', 'r_s')
        strategy_names = {
            "r_s": "(R, S) — до целевого уровня",
            "r_q": "(R, Q) — фиксированный объём",
            "s_s": "(s, S) — точка заказа",
            "custom": "Пользовательская"
        }
        st.markdown(f"**🚚 Стратегия:** {strategy_names.get(strategy_type, '(R, S)')}")
        
        # Доставка
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
        with st.spinner("Симуляция выполняется..."):
            settings = st.session_state.get('settings', {})
            
            # Получаем параметры
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
            
            # Определяем даты симуляции
            use_real_demand = st.session_state.get('use_real_demand', False)
            real_demand_dates = st.session_state.get('real_demand_dates')
            real_demand_values = st.session_state.get('real_demand_values')
            real_start_date = st.session_state.get('real_start_date')
            
            if use_real_demand and real_start_date and real_demand_dates:
                start_date = datetime.fromisoformat(real_start_date)
                days = len(real_demand_dates)
            else:
                start_date = datetime(2026, 2, 1)
                days = 30
            
            # Определяем параметры в зависимости от стратегии
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
            else:  # custom
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
                    'fifo_percent': fifo_percent
                }
                st.session_state.last_saved_experiment_id = None
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Ошибка: {str(e)}")
    
    # Отображение результатов
    if st.session_state.simulation_results:
        display_simulation_results(st.session_state.simulation_results)


def display_simulation_results(results):
    """Отображает результаты симуляции"""
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
    
    # Кнопка сохранения
    col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
    with col_save2:
        if st.button("💾 Сохранить результат в историю", use_container_width=True):
            if st.session_state.last_saved_experiment_id is not None:
                st.warning("⚠️ Этот эксперимент уже сохранён!")
            else:
                try:
                    from database.db_manager import DatabaseManager
                    db = DatabaseManager()
                    
                    exp_data = {
                        'product_name': selected_product_name,
                        'distribution': distribution,
                        'days': days,
                        'fifo_percent': fifo_percent if product_category == "strict" else None,
                        'min_stock': min_stock,
                        'purchase_price': params['purchase_price'],
                        'sale_price': params['sale_price'],
                        'shelf_life_days': params['shelf_life_days'],
                        'spoilage_type': spoilage_type,
                        'delivery_type': 'periodic' if params.get('milk_delivery_frequency') or params.get('tomatoes_delivery_frequency') else 'days_of_week',
                        'delivery_frequency': params.get('milk_delivery_frequency') or params.get('tomatoes_delivery_frequency'),
                        'delivery_days': str(params.get('milk_delivery_days') or params.get('tomatoes_delivery_days', [])),
                        'packing_type': params.get('delivery_type', 'unit'),
                        'box_size': params.get('box_size', 0),
                        'total_revenue': data['total_revenue'],
                        'total_cost': data['total_cost'],
                        'total_spoilage_kg': data['total_spoilage_kg'],
                        'total_spoilage_money': data['total_spoilage_money'],
                        'profit': data['profit'],
                        'total_unmet_demand': total_unmet,
                        'avg_stock': data.get('avg_stock', 0)
                    }
                    
                    experiment_id = db.save_experiment(exp_data)
                    st.session_state.last_saved_experiment_id = experiment_id
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка сохранения: {e}")
    
    if st.session_state.last_saved_experiment_id is not None:
        st.info(f"✅ Результат сохранён в историю! (ID: {st.session_state.last_saved_experiment_id})")
    
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
    
    # График остатков
    st.subheader("📊 Динамика остатков на складе")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df['day'], y=df['start_stock'], name='Остаток на начало дня',
                              line=dict(color='#3498DB', width=2)))
    fig2.add_trace(go.Scatter(x=df['day'], y=df['end_stock'], name='Остаток на конец дня',
                              line=dict(color='#2ECC71', width=3)))
    fig2.add_hline(y=min_stock, line_dash="dash", line_color="red", 
                   annotation_text=f"Min запас: {min_stock}")
    fig2.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Остаток (кг/шт)")
    st.plotly_chart(fig2, use_container_width=True)
    
    # График порчи
    st.subheader("🗑️ Динамика порчи")
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=df['day'], y=df['spoilage_kg'], name='Порча', 
                          marker_color='#E74C3C', opacity=0.7))
    fig3.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Порча (кг/шт)")
    st.plotly_chart(fig3, use_container_width=True)
    
    # График поставок
    st.subheader("🚚 Поставки")
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(x=df['day'], y=df['order'], name='Поставки', 
                          marker_color='#27AE60', opacity=0.7))
    fig4.update_layout(template='plotly_white', xaxis_title="День", yaxis_title="Объём поставки")
    st.plotly_chart(fig4, use_container_width=True)
    
    # ========== ГИСТОГРАММЫ ==========
    st.markdown("---")
    st.subheader("📊 Анализ распределений")
    
    col1, col2 = st.columns(2)
    with col1:
        fig_hist = px.histogram(df, x='demand', nbins=15, title="Распределение спроса",
                                labels={'demand': 'Спрос'}, template='plotly_white')
        fig_hist.add_vline(x=df['demand'].mean(), line_dash="dash", line_color="red",
                          annotation_text=f"Среднее: {df['demand'].mean():.2f}")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        if product_category == "strict" and 'spoilage_stats' in data:
            fifo_rates = data['spoilage_stats'].get('fifo_rates', [])
            if fifo_rates:
                fig_fifo = px.histogram(x=fifo_rates, nbins=15, 
                                        title=f"FIFO (ожидаемый {fifo_percent}%)",
                                        labels={'x': 'Процент покупателей (%)'}, 
                                        template='plotly_white')
                fig_fifo.add_vline(x=fifo_percent, line_dash="dash", line_color="red")
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
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Статистика спроса")
        if 'demand_stats' in data:
            stats = data['demand_stats']
            st.write(f"**Среднее:** {stats.get('mean', 0):.2f}")
            st.write(f"**Минимум:** {stats.get('min', 0):.2f}")
            st.write(f"**Максимум:** {stats.get('max', 0):.2f}")
    with col2:
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
        
        csv = df_display.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Скачать таблицу (CSV)", data=csv,
                        file_name=f"{selected_product_name}_simulation_{days}_days.csv", 
                        mime="text/csv")
