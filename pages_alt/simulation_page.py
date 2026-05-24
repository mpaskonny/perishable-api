import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
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
    
    st.markdown("---")
    
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
    
    # ===== ПРАВЫЙ КОНТЕЙНЕР: Источник данных спроса =====
    with col_right:
        st.subheader("📊 Источник данных спроса")
        
        demand_source = st.radio(
            "Выберите источник",
            options=["generated", "excel"],
            format_func=lambda x: "🎲 Генерировать случайно" if x == "generated" else "📁 Загрузить из Excel (реальные данные)",
            horizontal=True,
            key="demand_source"
        )
        
        use_real_demand = False
        real_demand_file = None
        
        if demand_source == "excel":
            from core.data_loader import DemandDataLoader
            
            col_btn, _ = st.columns([1, 3])
            with col_btn:
                template_path = "demand_template.xlsx"
                DemandDataLoader.create_template(template_path)
                
                with open(template_path, "rb") as f:
                    st.download_button(
                        label="📥 Шаблон",
                        data=f,
                        file_name="demand_template.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_template",
                        help="Скачать шаблон Excel для заполнения"
                    )
            
            st.caption("📝 Заполните шаблон и загрузите ниже:")
            
            uploaded_file = st.file_uploader(
                "Загрузите файл",
                type=['xlsx', 'xls'],
                help="Файл должен содержать колонки: 'Дата' и 'Спрос'",
                key="demand_file",
                label_visibility="collapsed"
            )
            
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    
                    has_date = any(col in df.columns for col in ['Дата', 'Date', 'ДАТА', 'date'])
                    has_demand = any(col in df.columns for col in ['Спрос', 'Demand', 'demand', 'СПРОС'])
                    
                    if has_date and has_demand:
                        os.makedirs("uploads", exist_ok=True)
                        file_path = f"uploads/demand_{selected_product_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        use_real_demand = True
                        real_demand_file = file_path
                        st.success(f"✅ Загружено {len(df)} записей")
                    else:
                        st.error("❌ Файл должен содержать колонки 'Дата' и 'Спрос'")
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
    
    st.markdown("---")
    
    # ========== ДВЕ КОЛОНКИ С КОНТЕЙНЕРАМИ ==========
    col_left, col_right = st.columns(2)
    
    # ЛЕВЫЙ КОНТЕЙНЕР: Параметры симуляции
    with col_left:
        st.subheader("⚙️ Параметры симуляции")
        days = st.slider("📅 Количество дней симуляции", 10, 365, 30, key="sim_days")
        min_stock = st.number_input("📦 Целевой уровень запаса", min_value=0.0, value=300.0, step=50.0, key="sim_min_stock")
    
    # ПРАВЫЙ КОНТЕЙНЕР: зависит от типа продукта
    with col_right:
        if product_category == "strict":
            st.subheader("👥 Распределение покупателей")
            fifo_percent = st.slider("FIFO % (остальные LIFO)", 0, 100, 75, step=5, key="sim_fifo")
            lifo_percent = 100 - fifo_percent
            st.caption(f"📊 LIFO: {lifo_percent}%")
            spoilage_type = "strict"
            power_p = 2.0
            logistic_k = 15.0
        else:
            st.subheader("🕐 Параметры порчи")
            
            spoilage_type = st.selectbox(
                "Тип порчи",
                options=["linear", "power", "logistic"],
                format_func=lambda x: {
                    "linear": "📈 Линейная (равномерное старение)",
                    "power": "📉 Степенная (ускорение к концу срока)",
                    "logistic": "📊 Логистическая (S-образная)"
                }[x],
                key="sim_spoilage_type"
            )
            
            power_p = 2.0
            logistic_k = 15.0
            
            if spoilage_type == "power":
                power_p = st.slider(
                    "Степень кривизны (p)", 
                    min_value=1.5, 
                    max_value=4.0, 
                    value=2.0, 
                    step=0.1,
                    help="Чем больше p, тем резче рост порчи в конце срока",
                    key="sim_power_p"
                )
            elif spoilage_type == "logistic":
                logistic_k = st.slider(
                    "Коэффициент крутизны (k)", 
                    min_value=5.0, 
                    max_value=30.0, 
                    value=15.0, 
                    step=1.0,
                    help="Чем больше k, тем резче переход от свежего к испорченному",
                    key="sim_log_k"
                )
            
            fifo_percent = 100
            lifo_percent = 0
    
    # ========== КНОПКА ЗАПУСКА ==========
    st.markdown("---")
    
    if st.button("🚀 Запустить симуляцию", type="primary", use_container_width=True):
        with st.spinner("Симуляция выполняется..."):
            settings = st.session_state.get('settings', {})
            
            params = {
                "days": days,
                "min_stock": float(min_stock),
                "purchase_price": float(selected_product['purchase_price']),
                "sale_price": float(selected_product['sale_price']),
                "distribution": settings.get('distribution', 'uniform'),
                "weekday_factors": settings.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1]),
                "spoilage_type": spoilage_type,
                "shelf_life_days": int(selected_product['shelf_life_days']),
                "power_p": power_p if spoilage_type == "power" else None,
                "logistic_k": logistic_k if spoilage_type == "logistic" else None,
                "delivery_type": settings.get('delivery_type', 'unit'),
                "box_size": settings.get('box_size', 0),
                "product_type": "milk" if product_category == "strict" else "tomatoes",
                "start_date": datetime(2026, 2, 1).isoformat(),
                "product_name": selected_product_name,
                "fifo_percent": float(fifo_percent) if product_category == "strict" else None,
                "lifo_percent": float(lifo_percent) if product_category == "strict" else None,
                "utilization_price": 5.0 if product_category == "strict" else 0.0,
                "sigma_buyer": 1.51 if product_category == "strict" else None,
                "use_real_demand": use_real_demand,
                "real_demand_file": real_demand_file if use_real_demand else None
            }
            
            schedule_type = settings.get('schedule_type', 'frequency')
            if product_category == "strict":
                if schedule_type == 'frequency':
                    params["milk_delivery_frequency"] = settings.get('delivery_frequency', 2)
                    params["milk_delivery_days"] = []
                else:
                    params["milk_delivery_frequency"] = 0
                    params["milk_delivery_days"] = settings.get('delivery_days', [0, 3])
            else:
                if schedule_type == 'frequency':
                    params["tomatoes_delivery_frequency"] = settings.get('delivery_frequency', 2)
                    params["tomatoes_delivery_days"] = []
                else:
                    params["tomatoes_delivery_frequency"] = 0
                    params["tomatoes_delivery_days"] = settings.get('delivery_days', [0, 3])
            
            try:
                response = requests.post(f"{API_URL}/simulate", json=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                total_unmet = sum(day.get('unmet_demand', 0) for day in data['daily_history'])
                
                st.session_state.simulation_results = {
                    'data': data,
                    'total_unmet': total_unmet,
                    'params': params,
                    'distribution': settings.get('distribution', 'uniform'),
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
        
        columns_to_drop = ['fifo_sales', 'lifo_sales', 'total_sales', 'life_sales']
        for col in columns_to_drop:
            if col in df_display.columns:
                df_display = df_display.drop(columns=[col])
        
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
                'unmet_demand': 'Неудовлетворенный спрос (пакеты)',
                'spoilage_kg': 'Порча (пакеты)',
                'order': 'Заказ (пакеты)',
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
                'unmet_demand': 'Неудовлетворенный спрос (кг)',
                'spoilage_kg': 'Порча (кг)',
                'order': 'Заказ (кг)',
                'revenue': 'Выручка (руб)',
                'purchase_cost': 'Затраты на закупку (руб)',
                'end_stock': 'Остаток на конец (кг)',
                'stock_week1': 'Остаток 0-7 дней (кг)',
                'stock_week2': 'Остаток 8-14 дней (кг)',
                'stock_week3': 'Остаток 15+ дней (кг)'
            }
            
            if 'start_stock' in df_display.columns and 'spoilage_kg' in df_display.columns:
                df_display['Порча % от остатка'] = df_display.apply(
                    lambda row: round((row['spoilage_kg'] / row['start_stock'] * 100), 2) 
                    if row['start_stock'] > 0 else 0, axis=1
                )
                column_names['Порча % от остатка'] = 'Порча % от остатка'
        
        existing_columns = {k: v for k, v in column_names.items() if k in df_display.columns}
        df_display = df_display.fillna(0)
        df_display = df_display.rename(columns=existing_columns)
        
        st.dataframe(df_display, use_container_width=True)
        
        csv = df_display.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Скачать таблицу (CSV)", data=csv,
                          file_name=f"{selected_product_name}_simulation_{days}_days.csv", 
                          mime="text/csv")
