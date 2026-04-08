import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import json

# Настройка страницы
st.set_page_config(
    page_title="Симулятор продуктов",
    page_icon="🥛",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"

# Заголовок
st.title("🥛 Симулятор продуктов с ограниченным сроком годности")
st.markdown("---")

# Боковая панель с параметрами
with st.sidebar:
    st.header("⚙️ Параметры симуляции")

    product = st.selectbox(
        "Выберите продукт",
        options=["milk", "tomatoes"],
        format_func=lambda x: "🥛 Молоко" if x == "milk" else "🍅 Помидоры"
    )

    distribution = st.selectbox(
        "Закон распределения спроса",
        options=["uniform", "normal"],
        format_func=lambda x: "📊 Равномерный" if x == "uniform" else "📈 Нормальный"
    )

    days = st.slider("Количество дней", 10, 100, 30)

    st.markdown("---")
    st.subheader("💰 Цены")

    if product == "milk":
        default_purchase = 30
        default_sale = 90
    else:
        default_purchase = 220
        default_sale = 295

    purchase_price = st.number_input("Цена закупки (руб)", value=default_purchase)
    sale_price = st.number_input("Цена продажи (руб)", value=default_sale)

    st.markdown("---")
    st.subheader("📦 Запасы")
    min_stock = st.number_input("Минимальный запас", value=100 if product == "milk" else 300)

    # ==================== КОЭФФИЦИЕНТЫ ТОЛЬКО ДЛЯ МОЛОКА ====================
    if product == "milk":
        st.markdown("---")
        st.subheader("📅 Коэффициенты спроса по дням недели")

        st.info("Базовый спрос умножается на коэффициент дня недели")

        col1, col2, col3 = st.columns(3)
        with col1:
            mon = st.number_input("Пн", value=0.8, step=0.1, format="%.1f")
            tue = st.number_input("Вт", value=0.6, step=0.1, format="%.1f")
            wed = st.number_input("Ср", value=0.9, step=0.1, format="%.1f")
        with col2:
            thu = st.number_input("Чт", value=1.0, step=0.1, format="%.1f")
            fri = st.number_input("Пт", value=1.3, step=0.1, format="%.1f")
            sat = st.number_input("Сб", value=1.5, step=0.1, format="%.1f")
        with col3:
            sun = st.number_input("Вс", value=1.1, step=0.1, format="%.1f")

        weekday_factors = [mon, tue, wed, thu, fri, sat, sun]

        st.markdown("---")
        st.subheader("👥 Распределение покупателей")

        col1, col2 = st.columns(2)
        with col1:
            fifo_percent = st.number_input(
                "FIFO %",
                min_value=0,
                max_value=100,
                value=75,
                step=5,
                help="Процент покупателей, берущих самое старое"
            )
        with col2:
            lifo_percent = 100 - fifo_percent
            st.metric("LIFO %", f"{lifo_percent}%")

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

        delivery_type_milk = st.radio(
            "Способ поставки",
            options=["unit", "box"],
            format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками",
            index=0,
            horizontal=True,
            help="Штучно — заказ любого количества, Коробками — заказ кратно размеру коробки"
        )

        if delivery_type_milk == "box":
            box_size_milk = st.number_input(
                "Размер коробки (пакетов)",
                min_value=1,
                max_value=100,
                value=20,
                step=5,
                help="Количество пакетов в одной коробке"
            )
        else:
            box_size_milk = 0


    # ==================== ДЛЯ ПОМИДОРОВ ====================
    if product == "tomatoes":
        st.markdown("---")
        st.subheader("📅 Коэффициенты спроса по дням недели")

        st.info("Базовый спрос умножается на коэффициент дня недели")

        col1, col2, col3 = st.columns(3)
        with col1:
            mon_tom = st.number_input("Пн", value=0.8, step=0.1, format="%.1f", key="tom_mon")
            tue_tom = st.number_input("Вт", value=0.6, step=0.1, format="%.1f", key="tom_tue")
            wed_tom = st.number_input("Ср", value=0.9, step=0.1, format="%.1f", key="tom_wed")
        with col2:
            thu_tom = st.number_input("Чт", value=1.0, step=0.1, format="%.1f", key="tom_thu")
            fri_tom = st.number_input("Пт", value=1.3, step=0.1, format="%.1f", key="tom_fri")
            sat_tom = st.number_input("Сб", value=1.5, step=0.1, format="%.1f", key="tom_sat")
        with col3:
            sun_tom = st.number_input("Вс", value=1.1, step=0.1, format="%.1f", key="tom_sun")

        # Сохраняем коэффициенты в переменную, которая будет доступна
        tomatoes_weekday_factors = [mon_tom, tue_tom, wed_tom, thu_tom, fri_tom, sat_tom, sun_tom]

        st.markdown("---")
        st.subheader("🚚 Настройки поставок")

        delivery_schedule_type_tomatoes = st.radio(
            "Тип расписания",
            options=["frequency", "days"],
            format_func=lambda x: "📅 Периодичность (каждые N дней)" if x == "frequency" else "📅 Конкретные дни недели",
            index=0,
            horizontal=True
        )

        if delivery_schedule_type_tomatoes == "frequency":
            delivery_frequency_tomatoes = st.selectbox(
                "Периодичность поставок",
                options=[1, 2, 3, 4, 5, 6, 7, 10, 14],
                format_func=lambda x: {
                    1: "📅 Каждый день",
                    2: "📅 Через день",
                    3: "📅 Каждые 3 дня",
                    4: "📅 Каждые 4 дня",
                    5: "📅 Каждые 5 дней",
                    6: "📅 Каждые 6 дней",
                    7: "📅 Раз в неделю",
                    10: "📅 Каждые 10 дней",
                    14: "📅 Каждые 14 дней"
                }.get(x, f"📅 Каждые {x} дней"),
                index=2
            )
            delivery_days_tomatoes = []
        else:
            delivery_frequency_tomatoes = 0
            delivery_days_tomatoes = st.multiselect(
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
            delivery_days_tomatoes = [day[1] for day in delivery_days_tomatoes]

        st.markdown("---")
        st.subheader("📦 Тип поставок")

        delivery_type_tomatoes = st.radio(
            "Способ поставки",
            options=["unit", "box"],
            format_func=lambda x: "📦 Штучно (кг)" if x == "unit" else "📦 Ящиками",
            index=0,
            horizontal=True,
            help="Штучно — заказ любого количества кг, Ящиками — заказ кратно весу ящика"
        )

        if delivery_type_tomatoes == "box":
            box_size_tomatoes = st.number_input(
                "Вес ящика (кг)",
                min_value=1,
                max_value=100,
                value=20,
                step=5,
                help="Количество кг в одном ящике"
            )
        else:
            box_size_tomatoes = 0


# Кнопка запуска (ВНЕ боковой панели)
run_button = st.button("🚀 Запустить симуляцию", type="primary", use_container_width=True)

# Основная область
if run_button:
    with st.spinner("Симуляция выполняется..."):
        params = {
            "days": days,
            "min_stock": float(min_stock),
            "purchase_price": float(purchase_price),
            "sale_price": float(sale_price)
        }

        if product == "milk":
            params["weekday_factors"] = weekday_factors

        if product == "milk":
            params["shelf_life_days"] = 10
            params["utilization_price"] = 5
            params["sigma_buyer"] = 1.51
            params["milk_delivery_frequency"] = delivery_frequency if delivery_schedule_type == "frequency" else 0
            params["milk_delivery_days"] = delivery_days if delivery_schedule_type == "days" else []
            params["delivery_type"] = delivery_type_milk
            params["box_size"] = box_size_milk if delivery_type_milk == "box" else 0
            params["fifo_percent"] = float(fifo_percent)
            params["lifo_percent"] = float(100 - fifo_percent)

        else:  # tomatoes
            # tomatoes_weekday_factors уже определена в боковой панели
            params["weekday_factors"] = tomatoes_weekday_factors
            params["sigma_10"] = 0.96
            params["sigma_50"] = 1.59
            params["delivery_type"] = delivery_type_tomatoes
            params["box_size"] = box_size_tomatoes if delivery_type_tomatoes == "box" else 0
            params["tomatoes_delivery_frequency"] = delivery_frequency_tomatoes if delivery_schedule_type_tomatoes == "frequency" else 0
            params["tomatoes_delivery_days"] = delivery_days_tomatoes if delivery_schedule_type_tomatoes == "days" else []

        endpoint = f"{API_URL}/simulate"
        params["product_type"] = product
        params["distribution"] = distribution

        try:
            response = requests.post(endpoint, json=params)
            response.raise_for_status()
            data = response.json()

            st.success("✅ Симуляция завершена!")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Выручка", f"{data['total_revenue']:,.0f} руб")
            with col2:
                st.metric("Затраты", f"{data['total_cost']:,.0f} руб")
            with col3:
                profit = data['profit']
                st.metric("Прибыль", f"{profit:,.0f} руб")
            with col4:
                st.metric("Потери", f"{data['total_spoilage_kg']:.1f} кг")

            st.markdown("---")

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

                    fig.add_trace(go.Scatter(
                        x=plot_df['День'],
                        y=plot_df['Спрос'],
                        mode='lines+markers',
                        name='Спрос',
                        line=dict(color='#2E86AB', width=3),
                        marker=dict(size=6)
                    ))

                    fig.add_trace(go.Scatter(
                        x=plot_df['День'],
                        y=plot_df['Продажи'],
                        mode='lines+markers',
                        name='Продажи',
                        line=dict(color='#E74C3C', width=3),
                        marker=dict(size=6)
                    ))

                    fig.update_layout(
                        title=f"Спрос vs Продажи ({distribution} распределение)",
                        xaxis_title="День",
                        yaxis_title="Количество (кг/пакеты)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(t=50),
                        hovermode='x unified',
                        template='plotly_white'
                    )

                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Нет данных для графика")

                st.markdown("---")

                if product == "milk":
                    st.subheader("📊 Анализ распределений (Молоко)")

                    col1, col2 = st.columns(2)

                    with col1:
                        fig_hist_demand = px.histogram(
                            df,
                            x='demand',
                            nbins=15,
                            title=f"Распределение спроса ({distribution})",
                            labels={'demand': 'Спрос (пакеты)', 'count': 'Частота'},
                            opacity=0.8,
                            color_discrete_sequence=['#2E86AB']
                        )

                        mean_demand = df['demand'].mean()
                        fig_hist_demand.add_vline(
                            x=mean_demand,
                            line_dash="dash",
                            line_color="red",
                            annotation_text=f"Среднее: {mean_demand:.2f}",
                            annotation_position="top"
                        )

                        st.plotly_chart(fig_hist_demand, use_container_width=True)

                        with st.expander("📊 Статистика спроса"):
                            st.write(f"**Среднее:** {df['demand'].mean():.2f}")
                            st.write(f"**Медиана:** {df['demand'].median():.2f}")
                            st.write(f"**Ст. отклонение:** {df['demand'].std():.2f}")
                            st.write(f"**Мин/Макс:** {df['demand'].min():.2f} / {df['demand'].max():.2f}")

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
                                fig_hist_fifo = px.histogram(
                                    x=fifo_rates,
                                    nbins=15,
                                    title=f"FIFO (ожидаемый {expected_fifo}%)",
                                    labels={'x': 'Процент покупателей (%)', 'count': 'Частота'},
                                    opacity=0.8,
                                    color_discrete_sequence=['#27AE60']
                                )
                                fig_hist_fifo.add_vline(x=expected_fifo, line_dash="dash", line_color="red", annotation_text=f"Ожид. {expected_fifo}%", annotation_position="top")
                                mean_fifo = np.mean(fifo_rates)
                                fig_hist_fifo.add_vline(x=mean_fifo, line_dash="solid", line_color="#27AE60", annotation_text=f"Ср: {mean_fifo:.2f}%", annotation_position="bottom")
                                st.plotly_chart(fig_hist_fifo, use_container_width=True)

                    with col2:
                        if 'spoilage_stats' in data and 'lifo_rates' in data['spoilage_stats']:
                            lifo_rates = data['spoilage_stats']['lifo_rates']
                            if lifo_rates:
                                expected_lifo = 100 - params.get('fifo_percent', 25)
                                fig_hist_lifo = px.histogram(
                                    x=lifo_rates,
                                    nbins=15,
                                    title=f"LIFO (ожидаемый {expected_lifo}%)",
                                    labels={'x': 'Процент покупателей (%)', 'count': 'Частота'},
                                    opacity=0.8,
                                    color_discrete_sequence=['#E74C3C']
                                )
                                fig_hist_lifo.add_vline(x=expected_lifo, line_dash="dash", line_color="red", annotation_text=f"Ожид. {expected_lifo}%", annotation_position="top")
                                mean_lifo = np.mean(lifo_rates)
                                fig_hist_lifo.add_vline(x=mean_lifo, line_dash="solid", line_color="#E74C3C", annotation_text=f"Ср: {mean_lifo:.2f}%", annotation_position="bottom")
                                st.plotly_chart(fig_hist_lifo, use_container_width=True)

                else:  # tomatoes
                    st.subheader("📊 Анализ распределений (Помидоры)")

                    col1, col2 = st.columns(2)

                    with col1:
                        fig_hist_demand = px.histogram(
                            df,
                            x='demand',
                            nbins=15,
                            title=f"Распределение спроса ({distribution})",
                            labels={'demand': 'Спрос (кг)', 'count': 'Частота'},
                            opacity=0.8,
                            color_discrete_sequence=['#A23B72']
                        )
                        mean_demand = df['demand'].mean()
                        fig_hist_demand.add_vline(
                            x=mean_demand,
                            line_dash="dash",
                            line_color="red",
                            annotation_text=f"Среднее: {mean_demand:.2f}",
                            annotation_position="top"
                        )
                        st.plotly_chart(fig_hist_demand, use_container_width=True)

                    with col2:
                        st.info("Графики порчи расположены ниже")

                    st.markdown("---")
                    st.subheader("📊 Распределение процентов порчи по неделям")

                    spoilage_stats = data.get('spoilage_stats', {})
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        week1_rates = spoilage_stats.get('week1_rates', spoilage_stats.get('week10_rates', []))
                        if week1_rates and len(week1_rates) > 0:
                            fig1 = px.histogram(
                                x=week1_rates,
                                nbins=15,
                                title="1-я неделя (базовый 10%)",
                                labels={'x': 'Процент порчи (%)', 'count': 'Частота'},
                                opacity=0.8,
                                color_discrete_sequence=['#3498DB']
                            )
                            fig1.add_vline(x=10.0, line_dash="dash", line_color="red", annotation_text="10%")
                            mean1 = spoilage_stats.get('week1_mean', spoilage_stats.get('week10_mean', np.mean(week1_rates)))
                            fig1.add_vline(x=mean1, line_dash="solid", line_color="#3498DB", annotation_text=f"Ср: {mean1:.1f}%")
                            st.plotly_chart(fig1, use_container_width=True)
                            st.caption(f"📊 {len(week1_rates)} записей, среднее: {mean1:.1f}%")
                        else:
                            st.info("Нет данных (нужно >7 дней)")
                    
                    with col2:
                        week2_rates = spoilage_stats.get('week2_rates', spoilage_stats.get('week50_rates', []))
                        if week2_rates and len(week2_rates) > 0:
                            fig2 = px.histogram(
                                x=week2_rates,
                                nbins=15,
                                title="2-я неделя (базовый 50%)",
                                labels={'x': 'Процент порчи (%)', 'count': 'Частота'},
                                opacity=0.8,
                                color_discrete_sequence=['#F39C12']
                            )
                            fig2.add_vline(x=50.0, line_dash="dash", line_color="red", annotation_text="50%")
                            mean2 = spoilage_stats.get('week2_mean', spoilage_stats.get('week50_mean', np.mean(week2_rates)))
                            fig2.add_vline(x=mean2, line_dash="solid", line_color="#F39C12", annotation_text=f"Ср: {mean2:.1f}%")
                            st.plotly_chart(fig2, use_container_width=True)
                            st.caption(f"📊 {len(week2_rates)} записей, среднее: {mean2:.1f}%")
                        else:
                            st.info("Нет данных (нужно >14 дней)")
                    
                    with col3:
                        week3_rates = spoilage_stats.get('week3_rates', spoilage_stats.get('week100_rates', []))
                        if week3_rates and len(week3_rates) > 0:
                            fig3 = px.histogram(
                                x=week3_rates,
                                nbins=15,
                                title="3-я неделя (базовый 100%)",
                                labels={'x': 'Процент порчи (%)', 'count': 'Частота'},
                                opacity=0.8,
                                color_discrete_sequence=['#E74C3C']
                            )
                            fig3.add_vline(x=100.0, line_dash="dash", line_color="red", annotation_text="100%")
                            mean3 = spoilage_stats.get('week3_mean', np.mean(week3_rates))
                            fig3.add_vline(x=mean3, line_dash="solid", line_color="#E74C3C", annotation_text=f"Ср: {mean3:.1f}%")
                            st.plotly_chart(fig3, use_container_width=True)
                            st.caption(f"📊 {len(week3_rates)} записей, среднее: {mean3:.1f}%")
                        else:
                            st.info("Нет данных (нужно >21 дня)")

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
                if product == "milk" and 'spoilage_stats' in data:
                    s = data['spoilage_stats']
                    st.write(f"**FIFO среднее:** {s.get('fifo_mean', 0):.2f}%")
                    st.write(f"**LIFO среднее:** {s.get('lifo_mean', 0):.2f}%")
                elif product == "tomatoes" and 'spoilage_stats' in data:
                    s = data['spoilage_stats']
                    st.write(f"**1-я неделя (10%):** {s.get('week1_mean', s.get('week10_mean', 0)):.2f}%")
                    st.write(f"**2-я неделя (50%):** {s.get('week2_mean', s.get('week50_mean', 0)):.2f}%")

            # Таблица с историей
            with st.expander("📋 Детальная история"):
                df_display = df.copy()
                
                # Удаляем служебные колонки
                columns_to_drop = []
                if 'fifo_sales' in df_display.columns:
                    columns_to_drop.append('fifo_sales')
                if 'lifo_sales' in df_display.columns:
                    columns_to_drop.append('lifo_sales')
                if 'total_sales' in df_display.columns:
                    columns_to_drop.append('total_sales')
                if 'life_sales' in df_display.columns:
                    columns_to_drop.append('life_sales')
                if 'spoilage_money' in df_display.columns:
                    columns_to_drop.append('spoilage_money')
                
                if columns_to_drop:
                    df_display = df_display.drop(columns=columns_to_drop)
                
                # РАЗНЫЕ КОЛОНКИ ДЛЯ МОЛОКА И ПОМИДОРОВ
                if product == "milk":
                    # Для молока: убираем недельные колонки (они None)
                    milk_columns_to_drop = ['stock_week1', 'stock_week2', 'stock_week3']
                    existing_milk_drop = [c for c in milk_columns_to_drop if c in df_display.columns]
                    if existing_milk_drop:
                        df_display = df_display.drop(columns=existing_milk_drop)
                    
                    column_names = {
                        'day': 'День',
                        'date': 'Дата',
                        'demand': 'Спрос (пакеты)',
                        'start_stock': 'Остаток на начало (пакеты)',
                        'sales': 'Продажи (пакеты)',
                        'spoilage': 'Порча (пакеты)',
                        'order': 'Заказ (пакеты)',
                        'revenue': 'Выручка (руб)',
                        'purchase_cost': 'Затраты на закупку (руб)',
                        'utilization_cost': 'Затраты на утилизацию (руб)',
                        'end_stock': 'Остаток на конец (пакеты)',
                        'fifo_percent': 'FIFO %',
                        'lifo_percent': 'LIFO %'
                    }
                    
                    # Добавляем партии (только если они есть в данных)
                    batch_columns = ['batch_1_stock', 'batch_2_stock', 'batch_3_stock', 'batch_4_stock', 'batch_5_stock']
                    for i, col in enumerate(batch_columns, 1):
                        if col in df_display.columns:
                            column_names[col] = f'Партия {i}'
                    
                else:  # tomatoes
                    # Удаляем колонки молока
                    milk_columns = ['fifo_percent', 'lifo_percent', 'utilization_cost', 
                                    'batch_1_stock', 'batch_2_stock', 'batch_3_stock', 
                                    'batch_4_stock', 'batch_5_stock', 'fifo_sales', 'lifo_sales']
                    for col in milk_columns:
                        if col in df_display.columns:
                            df_display = df_display.drop(columns=[col])
                    
                    column_names = {
                        'day': 'День',
                        'date': 'Дата',
                        'demand': 'Спрос (кг)',
                        'start_stock': 'Остаток на начало (кг)',
                        'sales': 'Продажи (кг)',
                        'spoilage': 'Порча (кг)',
                        'order': 'Заказ (кг)',
                        'revenue': 'Выручка (руб)',
                        'purchase_cost': 'Затраты на закупку (руб)',
                        'end_stock': 'Остаток на конец (кг)',
                        'stock_week1': 'Остаток 0-7 дней (кг)',
                        'stock_week2': 'Остаток 8-14 дней (кг)',
                        'stock_week3': 'Остаток 15+ дней (кг)'
                    }
                
                # Применяем переименование
                existing_columns = {k: v for k, v in column_names.items() if k in df_display.columns}
                df_display = df_display.rename(columns=existing_columns)
                
                # Для помидоров добавляем колонку с процентом порчи
                if product == "tomatoes":
                    df_display['Порча % от остатка'] = df_display.apply(
                        lambda row: round((row['Порча (кг)'] / row['Остаток на начало (кг)'] * 100), 2) 
                        if row['Остаток на начало (кг)'] > 0 else 0, axis=1
                    )
                    
                    if 'spoilage_stats' in data:
                        spoilage_stats = data['spoilage_stats']
                        week1_mean = spoilage_stats.get('week1_mean', spoilage_stats.get('week10_mean', 0))
                        week2_mean = spoilage_stats.get('week2_mean', spoilage_stats.get('week50_mean', 0))
                        week3_mean = spoilage_stats.get('week3_mean', 0)
                        st.caption(f"📊 Средний процент порчи: 1-я неделя: {week1_mean:.1f}% | 2-я неделя: {week2_mean:.1f}% | 3-я неделя: {week3_mean:.1f}%")
                
                # Отображаем таблицу
                st.dataframe(df_display, use_container_width=True)
                
                # Кнопка для скачивания CSV
                csv = df_display.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Скачать таблицу (CSV)",
                    data=csv,
                    file_name=f"{product}_simulation_{days}_days.csv",
                    mime="text/csv",
                    help="Скачать детальную историю в формате CSV"
                )

        except requests.Timeout:
            st.error("⏰ Превышено время ожидания от сервера (30 секунд)")
            st.info("Попробуйте уменьшить количество дней симуляции")
        except requests.ConnectionError:
            st.error("🔌 Не удалось подключиться к серверу")
            st.info("Убедитесь, что FastAPI сервер запущен: python main.py")
        except requests.HTTPError as e:
            st.error(f"❌ Ошибка сервера: {e}")
        except json.JSONDecodeError:
            st.error("❌ Ошибка: Сервер вернул некорректный ответ")
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")
else:
    st.info("👈 Настройте параметры слева и нажмите 'Запустить симуляцию'")