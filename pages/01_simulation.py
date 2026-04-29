import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import json
from sidebar_config import setup_sidebar
from database.db_manager import DatabaseManager

# Устанавливаем параметр ДО загрузки боковой панели
st.query_params["page"] = "simulation"

# Фикс ширины страницы через JavaScript
st.markdown("""
    <script>
        function fixWidth() {
            const container = document.querySelector('.main .block-container');
            if (container) {
                container.style.maxWidth = '100%';
                container.style.paddingLeft = '2rem';
                container.style.paddingRight = '2rem';
            }
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar) {
                sidebar.style.width = '280px';
            }
        }
        setTimeout(fixWidth, 100);
        setTimeout(fixWidth, 300);
        setTimeout(fixWidth, 600);
    </script>
""", unsafe_allow_html=True)

# Загрузка единых стилей
with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Настройка боковой панели
setup_sidebar()

API_URL = "http://127.0.0.1:8000"

# Инициализация БД
db = DatabaseManager()

# Заголовок страницы
st.title("🥛 Симуляция управления запасами")
st.markdown("---")

# Получаем список товаров из БД
products_df = db.get_all_products()
if products_df.empty:
    st.error("❌ Нет товаров в базе данных. Добавьте товары в «Управление БД»")
    st.stop()

# Боковая панель с параметрами
with st.sidebar:
    st.header("⚙️ Параметры симуляции")

    # Выбор товара из БД
    product_options = {row['name']: row for _, row in products_df.iterrows()}
    selected_product_name = st.selectbox(
        "Выберите продукт",
        options=list(product_options.keys()),
        key="product_select"
    )
    selected_product = product_options[selected_product_name]
    
    product_id = selected_product['id_product']
    product_category = selected_product['category']  # strict / gradual
    purchase_price = selected_product['purchase_price']
    sale_price = selected_product['sale_price']
    shelf_life_days = selected_product['shelf_life_days']

    # Отображаем цены (только для информации, не редактируются)
    st.info(f"💰 Цена закупки: {purchase_price:.2f} руб | Цена продажи: {sale_price:.2f} руб")

    distribution = st.selectbox(
        "Закон распределения спроса",
        options=["uniform", "normal"],
        format_func=lambda x: "📊 Равномерный" if x == "uniform" else "📈 Нормальный"
    )

    days = st.slider("Количество дней", 10, 100, 30)

    st.markdown("---")
    st.subheader("📦 Запасы")
    min_stock = st.number_input("Минимальный запас", min_value=0.0, value=300.0, step=50.0)

    st.markdown("---")
    st.subheader("📅 Коэффициенты спроса по дням недели")
    st.info("Базовый спрос умножается на коэффициент дня недели")

    col1, col2, col3 = st.columns(3)
    with col1:
        mon = st.number_input("Пн", value=0.8, step=0.1, format="%.1f", key="mon")
        tue = st.number_input("Вт", value=0.6, step=0.1, format="%.1f", key="tue")
        wed = st.number_input("Ср", value=0.9, step=0.1, format="%.1f", key="wed")
    with col2:
        thu = st.number_input("Чт", value=1.0, step=0.1, format="%.1f", key="thu")
        fri = st.number_input("Пт", value=1.3, step=0.1, format="%.1f", key="fri")
        sat = st.number_input("Сб", value=1.5, step=0.1, format="%.1f", key="sat")
    with col3:
        sun = st.number_input("Вс", value=1.1, step=0.1, format="%.1f", key="sun")

    weekday_factors = [mon, tue, wed, thu, fri, sat, sun]

    # Параметры для молока (strict)
    if product_category == "strict":
        st.markdown("---")
        st.subheader("👥 Распределение покупателей")

        fifo_percent = st.number_input(
            "FIFO %",
            min_value=0,
            max_value=100,
            value=75,
            step=5,
            help="Процент покупателей, берущих самое старое"
        )
        lifo_percent = 100 - fifo_percent
        st.metric("LIFO %", f"{lifo_percent}%")

    # Параметры поставок (общие для всех)
    st.markdown("---")
    st.subheader("🚚 Поставки")

    delivery_schedule_type = st.radio(
        "Тип расписания",
        options=["frequency", "days"],
        format_func=lambda x: "📅 Периодичность (каждые N дней)" if x == "frequency" else "📅 Конкретные дни недели",
        index=0,
        horizontal=True
    )

    if delivery_schedule_type == "frequency":
        delivery_frequency = st.selectbox(
            "Периодичность поставок",
            options=[1, 2, 3, 4, 5, 6, 7],
            format_func=lambda x: {
                1: "📅 Каждый день",
                2: "📅 Через день",
                3: "📅 Каждые 3 дня",
                4: "📅 Каждые 4 дня",
                5: "📅 Каждые 5 дней",
                6: "📅 Каждые 6 дней",
                7: "📅 Раз в неделю"
            }.get(x, f"📅 Каждые {x} дней"),
            index=1
        )
        delivery_days = []
    else:
        delivery_frequency = 0
        delivery_days = st.multiselect(
            "Выберите дни поставок",
            options=[
                ("Понедельник", 0),
                ("Вторник", 1),
                ("Среда", 2),
                ("Четверг", 3),
                ("Пятница", 4),
                ("Суббота", 5),
                ("Воскресенье", 6)
            ],
            format_func=lambda x: x[0],
            default=[("Понедельник", 0), ("Четверг", 3)],
            help="Выберите дни, в которые будут осуществляться поставки"
        )
        delivery_days = [day[1] for day in delivery_days]

    st.markdown("---")
    st.subheader("📦 Тип поставок")

    delivery_type = st.radio(
        "Способ поставки",
        options=["unit", "box"],
        format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками/ящиками",
        index=0,
        horizontal=True,
        help="Штучно — заказ любого количества, Коробками — заказ кратно размеру упаковки"
    )

    box_size = 1
    if delivery_type == "box":
        box_size = st.number_input(
            "Размер упаковки (шт/кг)",
            min_value=1,
            value=20,
            step=5,
            help="Количество в одной упаковке"
        )


# Кнопка запуска
run_button = st.button("🚀 Запустить симуляцию", type="primary", use_container_width=True)

# Основная область
if run_button:
    with st.spinner("Симуляция выполняется..."):
        # Формируем параметры для API
        params = {
            "days": days,
            "min_stock": float(min_stock),
            "purchase_price": float(purchase_price),
            "sale_price": float(sale_price),
            "weekday_factors": weekday_factors,
            "delivery_type": delivery_type,
            "box_size": box_size,
            "distribution": distribution,
            "product_type": "milk" if product_category == "strict" else "tomatoes",
            "start_date": datetime(2026, 2, 1).isoformat()
        }

        # Для strict (молоко)
        if product_category == "strict":
            params["fifo_percent"] = float(fifo_percent)
            params["lifo_percent"] = float(100 - fifo_percent)
            params["shelf_life_days"] = int(shelf_life_days) if shelf_life_days else 10
            params["utilization_price"] = 5.0
            params["sigma_buyer"] = 1.51
            params["delivery_frequency"] = delivery_frequency if delivery_schedule_type == "frequency" else 0
            params["delivery_days"] = delivery_days if delivery_schedule_type == "days" else []

        # Для gradual (помидоры)
        else:
            # Получаем параметры порчи из БД
            spoilage_rates = db.get_spoilage_rates(product_id)
            week_rates = {}
            week_sigmas = {}
            for _, row in spoilage_rates.iterrows():
                week = int(row['week_number'])
                rate = float(row['rate'])
                week_rates[week] = rate
                # sigma можно задать по умолчанию или хранить в отдельной таблице
                week_sigmas[week] = 0.96 if week == 1 else 1.59
            
            params["sigma_10"] = week_sigmas.get(1, 0.96)
            params["sigma_50"] = week_sigmas.get(2, 1.59)
            params["delivery_frequency"] = delivery_frequency if delivery_schedule_type == "frequency" else 0
            params["delivery_days"] = delivery_days if delivery_schedule_type == "days" else []

        endpoint = f"{API_URL}/simulate"

        try:
            response = requests.post(endpoint, json=params)
            response.raise_for_status()
            data = response.json()

            st.success("✅ Симуляция завершена!")

            total_unmet = sum(day.get('unmet_demand', 0) for day in data['daily_history'])

            if st.button("💾 Сохранить результат в историю"):
                try:
                    from database.db_manager import DatabaseManager
                    db = DatabaseManager()
                    
                    # Подготовка данных для сохранения
                    exp_data = {
                        'product_name': selected_product_name,
                        'distribution': distribution,
                        'days': days,
                        'fifo_percent': fifo_percent if product_category == "strict" else None,
                        'min_stock': min_stock,
                        'purchase_price': purchase_price,
                        'sale_price': sale_price,
                        'delivery_type': 'periodic' if delivery_schedule_type == "frequency" else 'days_of_week',
                        'delivery_frequency': delivery_frequency if delivery_schedule_type == "frequency" else None,
                        'delivery_days': ",".join(map(str, delivery_days)) if delivery_days else None,
                        'packing_type': delivery_type,
                        'box_size': box_size,
                        'total_revenue': data['total_revenue'],
                        'total_cost': data['total_cost'],
                        'total_spoilage_kg': data['total_spoilage_kg'],
                        'total_spoilage_money': data['total_spoilage_money'],
                        'profit': data['profit'],
                        'total_unmet_demand': total_unmet
                    }
                    
                    experiment_id = db.save_experiment(exp_data)
                    st.success(f"✅ Результат сохранён в историю! (ID: {experiment_id})")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Ошибка сохранения: {e}")

            # Отображение метрик
            col1, col2, col3, col4, col5 = st.columns(5)

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

            st.markdown("---")

            # Отображение графиков и таблицы (остаётся без изменений)
            if data['daily_history']:
                df = pd.DataFrame(data['daily_history'])
                df['day'] = pd.to_numeric(df['day'], errors='coerce')
                df['demand'] = pd.to_numeric(df['demand'], errors='coerce')
                df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
                df['spoilage'] = pd.to_numeric(df['spoilage'], errors='coerce')
                df['order'] = pd.to_numeric(df['order'], errors='coerce')
                df['end_stock'] = pd.to_numeric(df['end_stock'], errors='coerce')
                df['total_sales'] = df['sales']

                st.subheader("📈 Динамика спроса и продаж (временной ряд)")
                plot_df = pd.DataFrame()
                plot_df['День'] = df['day']
                plot_df['Спрос'] = df['demand']
                plot_df['Продажи'] = df['total_sales']
                plot_df = plot_df.dropna()

                if not plot_df.empty and len(plot_df) > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=plot_df['День'], y=plot_df['Спрос'], mode='lines+markers', name='Спрос', line=dict(color='#2E86AB', width=3), marker=dict(size=6)))
                    fig.add_trace(go.Scatter(x=plot_df['День'], y=plot_df['Продажи'], mode='lines+markers', name='Продажи', line=dict(color='#E74C3C', width=3), marker=dict(size=6)))
                    fig.update_layout(title=f"Спрос vs Продажи ({distribution} распределение)", xaxis_title="День", yaxis_title="Количество (кг/пакеты)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=50), hovermode='x unified', template='plotly_white')
                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("📊 Динамика остатков на складе")
                    stock_df = pd.DataFrame()
                    stock_df['День'] = df['day']
                    stock_df['Остаток на начало дня'] = df['start_stock']
                    stock_df['Остаток на конец дня'] = df['end_stock']
                    stock_df = stock_df.dropna()

                    if not stock_df.empty and len(stock_df) > 0:
                        fig_stock = go.Figure()
                        fig_stock.add_trace(go.Scatter(x=stock_df['День'], y=stock_df['Остаток на начало дня'], mode='lines+markers', name='Остаток на начало дня', line=dict(color='#3498DB', width=2), marker=dict(size=5)))
                        fig_stock.add_trace(go.Scatter(x=stock_df['День'], y=stock_df['Остаток на конец дня'], mode='lines+markers', name='Остаток на конец дня', line=dict(color='#2ECC71', width=3), marker=dict(size=6, color='#27AE60')))
                        fig_stock.add_hline(y=min_stock, line_dash="dash", line_color="red", annotation_text=f"Min запас: {min_stock}", annotation_position="bottom right")
                        fig_stock.update_layout(title=f"Динамика остатков ({distribution} распределение)", xaxis_title="День", yaxis_title="Остаток (кг/пакеты)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=50), hovermode='x unified', template='plotly_white')
                        st.plotly_chart(fig_stock, use_container_width=True)
                else:
                    st.warning("Нет данных для графика")

                st.markdown("---")

                # Гистограммы (оставляем как было, но адаптируем)
                if product_category == "strict":
                    st.subheader("📊 Анализ распределений (Молоко)")
                    col1, col2 = st.columns(2)
                    with col1:
                        fig_hist_demand = px.histogram(df, x='demand', nbins=15, title=f"Распределение спроса ({distribution})", labels={'demand': 'Спрос (пакеты)', 'count': 'Частота'}, opacity=0.8, color_discrete_sequence=['#2E86AB'])
                        fig_hist_demand.add_vline(x=df['demand'].mean(), line_dash="dash", line_color="red", annotation_text=f"Среднее: {df['demand'].mean():.2f}", annotation_position="top")
                        st.plotly_chart(fig_hist_demand, use_container_width=True)
                    with col2:
                        st.info("Графики покупателей расположены ниже")
                    st.markdown("---")
                    st.subheader("📊 Распределение процентов покупателей")
                    col1, col2 = st.columns(2)
                    with col1:
                        if 'spoilage_stats' in data and 'fifo_rates' in data['spoilage_stats']:
                            fifo_rates = data['spoilage_stats']['fifo_rates']
                            if fifo_rates:
                                expected_fifo = params.get('fifo_percent', 75)
                                fig_hist_fifo = px.histogram(x=fifo_rates, nbins=15, title=f"FIFO (ожидаемый {expected_fifo}%)", labels={'x': 'Процент покупателей (%)', 'count': 'Частота'}, opacity=0.8, color_discrete_sequence=['#27AE60'])
                                fig_hist_fifo.add_vline(x=expected_fifo, line_dash="dash", line_color="red", annotation_text=f"Ожид. {expected_fifo}%", annotation_position="top")
                                fig_hist_fifo.add_vline(x=np.mean(fifo_rates), line_dash="solid", line_color="#27AE60", annotation_text=f"Ср: {np.mean(fifo_rates):.2f}%", annotation_position="bottom")
                                st.plotly_chart(fig_hist_fifo, use_container_width=True)
                    with col2:
                        if 'spoilage_stats' in data and 'lifo_rates' in data['spoilage_stats']:
                            lifo_rates = data['spoilage_stats']['lifo_rates']
                            if lifo_rates:
                                expected_lifo = 100 - params.get('fifo_percent', 25)
                                fig_hist_lifo = px.histogram(x=lifo_rates, nbins=15, title=f"LIFO (ожидаемый {expected_lifo}%)", labels={'x': 'Процент покупателей (%)', 'count': 'Частота'}, opacity=0.8, color_discrete_sequence=['#E74C3C'])
                                fig_hist_lifo.add_vline(x=expected_lifo, line_dash="dash", line_color="red", annotation_text=f"Ожид. {expected_lifo}%", annotation_position="top")
                                fig_hist_lifo.add_vline(x=np.mean(lifo_rates), line_dash="solid", line_color="#E74C3C", annotation_text=f"Ср: {np.mean(lifo_rates):.2f}%", annotation_position="bottom")
                                st.plotly_chart(fig_hist_lifo, use_container_width=True)
                else:  # tomatoes
                    st.subheader("📊 Анализ распределений (Помидоры)")
                    col1, col2 = st.columns(2)
                    with col1:
                        fig_hist_demand = px.histogram(df, x='demand', nbins=15, title=f"Распределение спроса ({distribution})", labels={'demand': 'Спрос (кг)', 'count': 'Частота'}, opacity=0.8, color_discrete_sequence=['#A23B72'])
                        fig_hist_demand.add_vline(x=df['demand'].mean(), line_dash="dash", line_color="red", annotation_text=f"Среднее: {df['demand'].mean():.2f}", annotation_position="top")
                        st.plotly_chart(fig_hist_demand, use_container_width=True)
                    with col2:
                        st.info("Графики порчи расположены ниже")
                    st.markdown("---")
                    st.subheader("📊 Распределение процентов порчи по неделям")
                    spoilage_stats = data.get('spoilage_stats', {})
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        week1_rates = spoilage_stats.get('week1_rates', spoilage_stats.get('week10_rates', []))
                        if week1_rates:
                            fig1 = px.histogram(x=week1_rates, nbins=15, title="1-я неделя (базовый 10%)", labels={'x': 'Процент порчи (%)', 'count': 'Частота'}, opacity=0.8, color_discrete_sequence=['#3498DB'])
                            fig1.add_vline(x=10.0, line_dash="dash", line_color="red", annotation_text="10%")
                            fig1.add_vline(x=spoilage_stats.get('week1_mean', spoilage_stats.get('week10_mean', np.mean(week1_rates))), line_dash="solid", line_color="#3498DB", annotation_text=f"Ср: {spoilage_stats.get('week1_mean', np.mean(week1_rates)):.1f}%")
                            st.plotly_chart(fig1, use_container_width=True)
                    with col2:
                        week2_rates = spoilage_stats.get('week2_rates', spoilage_stats.get('week50_rates', []))
                        if week2_rates:
                            fig2 = px.histogram(x=week2_rates, nbins=15, title="2-я неделя (базовый 50%)", labels={'x': 'Процент порчи (%)', 'count': 'Частота'}, opacity=0.8, color_discrete_sequence=['#F39C12'])
                            fig2.add_vline(x=50.0, line_dash="dash", line_color="red", annotation_text="50%")
                            fig2.add_vline(x=spoilage_stats.get('week2_mean', np.mean(week2_rates)), line_dash="solid", line_color="#F39C12", annotation_text=f"Ср: {spoilage_stats.get('week2_mean', np.mean(week2_rates)):.1f}%")
                            st.plotly_chart(fig2, use_container_width=True)
                    with col3:
                        week3_rates = spoilage_stats.get('week3_rates', [])
                        if week3_rates:
                            fig3 = px.histogram(x=week3_rates, nbins=15, title="3-я неделя (базовый 100%)", labels={'x': 'Процент порчи (%)', 'count': 'Частота'}, opacity=0.8, color_discrete_sequence=['#E74C3C'])
                            fig3.add_vline(x=100.0, line_dash="dash", line_color="red", annotation_text="100%")
                            fig3.add_vline(x=spoilage_stats.get('week3_mean', np.mean(week3_rates)), line_dash="solid", line_color="#E74C3C", annotation_text=f"Ср: {spoilage_stats.get('week3_mean', np.mean(week3_rates)):.1f}%")
                            st.plotly_chart(fig3, use_container_width=True)

                st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📊 Статистика спроса (из API)")
                if 'demand_stats' in data:
                    stats = data['demand_stats']
                    st.write(f"**Среднее:** {stats.get('mean', 0):.2f}")
                    st.write(f"**Минимум:** {stats.get('min', 0):.2f}")
                    st.write(f"**Максимум:** {stats.get('max', 0):.2f}")
            with col2:
                st.subheader("🗑️ Статистика порчи (из API)")
                if product_category == "strict" and 'spoilage_stats' in data:
                    s = data['spoilage_stats']
                    st.write(f"**FIFO среднее:** {s.get('fifo_mean', 0):.2f}%")
                    st.write(f"**LIFO среднее:** {s.get('lifo_mean', 0):.2f}%")
                elif 'spoilage_stats' in data:
                    s = data['spoilage_stats']
                    st.write(f"**1-я неделя (10%):** {s.get('week1_mean', s.get('week10_mean', 0)):.2f}%")
                    st.write(f"**2-я неделя (50%):** {s.get('week2_mean', s.get('week50_mean', 0)):.2f}%")

            # Таблица с историей
            with st.expander("📋 Детальная история"):
                df_display = df.copy()
                columns_to_drop = ['fifo_sales', 'lifo_sales', 'total_sales', 'life_sales', 'spoilage_money']
                for col in columns_to_drop:
                    if col in df_display.columns:
                        df_display = df_display.drop(columns=[col])
                
                if product_category == "strict":
                    milk_cols = ['stock_week1', 'stock_week2', 'stock_week3']
                    for col in milk_cols:
                        if col in df_display.columns:
                            df_display = df_display.drop(columns=[col])
                    column_names = {
                        'day': 'День', 'date': 'Дата', 'demand': 'Спрос (пакеты)',
                        'start_stock': 'Остаток на начало (пакеты)', 'sales': 'Продажи (пакеты)',
                        'unmet_demand': 'Неудовлетворенный спрос (пакеты)', 'spoilage': 'Порча (пакеты)',
                        'order': 'Заказ (пакеты)', 'revenue': 'Выручка (руб)',
                        'purchase_cost': 'Затраты на закупку (руб)', 'utilization_cost': 'Затраты на утилизацию (руб)',
                        'end_stock': 'Остаток на конец (пакеты)', 'fifo_percent': 'FIFO %', 'lifo_percent': 'LIFO %'
                    }
                    batch_cols = ['batch_1_stock', 'batch_2_stock', 'batch_3_stock', 'batch_4_stock', 'batch_5_stock']
                    for i, col in enumerate(batch_cols, 1):
                        if col in df_display.columns:
                            column_names[col] = f'Партия {i}'
                else:
                    tomato_cols = ['fifo_percent', 'lifo_percent', 'utilization_cost', 'batch_1_stock', 'batch_2_stock', 'batch_3_stock', 'batch_4_stock', 'batch_5_stock', 'fifo_sales', 'lifo_sales']
                    for col in tomato_cols:
                        if col in df_display.columns:
                            df_display = df_display.drop(columns=[col])
                    column_names = {
                        'day': 'День', 'date': 'Дата', 'demand': 'Спрос (кг)',
                        'start_stock': 'Остаток на начало (кг)', 'sales': 'Продажи (кг)',
                        'unmet_demand': 'Неудовлетворенный спрос (кг)', 'spoilage': 'Порча (кг)',
                        'order': 'Заказ (кг)', 'revenue': 'Выручка (руб)',
                        'purchase_cost': 'Затраты на закупку (руб)', 'end_stock': 'Остаток на конец (кг)',
                        'stock_week1': 'Остаток 0-7 дней (кг)', 'stock_week2': 'Остаток 8-14 дней (кг)',
                        'stock_week3': 'Остаток 15+ дней (кг)'
                    }
                    df_display['Порча % от остатка'] = df_display.apply(lambda row: round((row['spoilage'] / row['start_stock'] * 100), 2) if row['start_stock'] > 0 else 0, axis=1)
                    if 'spoilage_stats' in data:
                        s = data['spoilage_stats']
                        st.caption(f"📊 Средний процент порчи: 1-я неделя: {s.get('week1_mean', s.get('week10_mean', 0)):.1f}% | 2-я неделя: {s.get('week2_mean', s.get('week50_mean', 0)):.1f}% | 3-я неделя: {s.get('week3_mean', 0):.1f}%")
                
                existing_columns = {k: v for k, v in column_names.items() if k in df_display.columns}
                df_display = df_display.rename(columns=existing_columns)
                st.dataframe(df_display, use_container_width=True)
                
                csv = df_display.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 Скачать таблицу (CSV)", data=csv, file_name=f"{selected_product_name}_simulation_{days}_days.csv", mime="text/csv")

        except requests.Timeout:
            st.error("⏰ Превышено время ожидания от сервера (30 секунд)")
            st.info("Попробуйте уменьшить количество дней симуляции")
        except requests.ConnectionError:
            st.error("🔌 Не удалось подключиться к серверу")
            st.info("Убедитесь, что FastAPI сервер запущен: python main.py")
        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")
else:
    st.info("👈 Настройте параметры слева и нажмите 'Запустить симуляцию'")
