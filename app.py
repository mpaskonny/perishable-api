import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

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

    days = st.slider("Количество дней/недель", 10, 100, 30)

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
            # Автоматически вычисляем LIFO как 100 - FIFO
            lifo_percent = 100 - fifo_percent
            st.metric("LIFO %", f"{lifo_percent}%")

        st.markdown("---")
        st.subheader("🚚 Поставки")

        # Радио-кнопка для выбора типа расписания
        delivery_schedule_type = st.radio(
            "Тип расписания",
            options=["frequency", "days"],
            format_func=lambda
                x: "📅 Периодичность (каждые N дней)" if x == "frequency" else "📅 Конкретные дни недели",
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
            delivery_days = []  # не используется
        else:
            delivery_frequency = 0  # не используется
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
            # Извлекаем только числовые значения дней
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

    # Для помидоров добавляем настройку типа поставок
    if product == "tomatoes":
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

    run_button = st.button("🚀 Запустить симуляцию", type="primary", use_container_width=True)

# Основная область
if run_button:
    with st.spinner("Симуляция выполняется..."):
        # Формируем параметры
        params = {
            "days": days,
            "min_stock": float(min_stock),
            "purchase_price": float(purchase_price),
            "sale_price": float(sale_price)
        }

        # Добавляем коэффициенты только для молока
        if product == "milk":
            params["weekday_factors"] = weekday_factors

        # Добавляем специфичные параметры
        if product == "milk":
            params["shelf_life_days"] = 10
            params["utilization_price"] = 5
            params["sigma_buyer"] = 1.51
            params["delivery_frequency"] = delivery_frequency if delivery_schedule_type == "frequency" else 0
            params["delivery_days"] = delivery_days if delivery_schedule_type == "days" else []
            params["delivery_type"] = delivery_type_milk
            params["box_size"] = box_size_milk if delivery_type_milk == "box" else 0

            # ДЛЯ ОБОИХ ЗАКОНОВ ПЕРЕДАЕМ ЗАДАННЫЕ ПРОЦЕНТЫ
            params["fifo_percent"] = float(fifo_percent)
            params["lifo_percent"] = float(100 - fifo_percent)

        else:  # tomatoes
            params["sigma_10"] = 0.96
            params["sigma_50"] = 1.59
            params["delivery_type"] = delivery_type_tomatoes
            params["box_size"] = box_size_tomatoes if delivery_type_tomatoes == "box" else 0

        # Отправляем запрос к API
        endpoint = f"{API_URL}/simulate"
        params["product_type"] = product
        params["distribution"] = distribution

        try:
            response = requests.post(endpoint, json=params)
            response.raise_for_status()
            data = response.json()

            # Отображаем результаты
            st.success("✅ Симуляция завершена!")

            # Метрики
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
                # Преобразуем в DataFrame
                df = pd.DataFrame(data['daily_history'])

                # Преобразуем колонки в числовой тип
                df['day'] = pd.to_numeric(df['day'], errors='coerce')
                df['demand'] = pd.to_numeric(df['demand'], errors='coerce')

                # Обрабатываем sales - это список [fifo, lifo, random] или число
                if 'sales' in df.columns:
                    if isinstance(df['sales'].iloc[0], list):
                        # Если это список, суммируем все элементы
                        df['total_sales'] = df['sales'].apply(lambda x: sum(x) if isinstance(x, list) else x)
                    else:
                        # Если это число, просто берем его
                        df['total_sales'] = pd.to_numeric(df['sales'], errors='coerce')

                # Временной ряд спроса и продаж
                st.subheader("📈 Динамика спроса и продаж (временной ряд)")

                # Создаем DataFrame для графика
                plot_df = pd.DataFrame()
                plot_df['День'] = df['day']
                plot_df['Спрос'] = df['demand']
                plot_df['Продажи'] = df['total_sales'] if 'total_sales' in df else df['sales']

                # Удаляем строки с пропусками
                plot_df = plot_df.dropna()

                if not plot_df.empty and len(plot_df) > 0:
                    # Создаем график
                    fig = go.Figure()

                    # Добавляем линию спроса
                    fig.add_trace(go.Scatter(
                        x=plot_df['День'],
                        y=plot_df['Спрос'],
                        mode='lines+markers',
                        name='Спрос',
                        line=dict(color='#2E86AB', width=3),
                        marker=dict(size=6)
                    ))

                    # Добавляем линию продаж
                    fig.add_trace(go.Scatter(
                        x=plot_df['День'],
                        y=plot_df['Продажи'],
                        mode='lines+markers',
                        name='Продажи',
                        line=dict(color='#E74C3C', width=3),
                        marker=dict(size=6)
                    ))

                    # Настраиваем оформление
                    fig.update_layout(
                        title=f"Спрос vs Продажи ({distribution} распределение)",
                        xaxis_title="День",
                        yaxis_title="Количество (кг/пакеты)",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        margin=dict(t=50),
                        hovermode='x unified',
                        template='plotly_white'
                    )

                    # Добавляем сетку
                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Нет данных для графика")

                st.markdown("---")

                # ГИСТОГРАММЫ В ЗАВИСИМОСТИ ОТ ПРОДУКТА
                if product == "milk":
                    # Для молока: гистограмма спроса + ДВЕ гистограммы покупателей
                    st.subheader("📊 Анализ распределений (Молоко)")

                    # Первая строка - спрос
                    col1, col2 = st.columns(2)

                    with col1:
                        # Гистограмма спроса
                        fig_hist_demand = px.histogram(
                            df,
                            x='demand',
                            nbins=15,
                            title=f"Распределение спроса ({distribution})",
                            labels={'demand': 'Спрос (пакеты)', 'count': 'Частота'},
                            opacity=0.8,
                            color_discrete_sequence=['#2E86AB']
                        )

                        # Добавляем вертикальную линию среднего
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

                    # Вторая строка - два графика покупателей
                    st.subheader("📊 Распределение процентов покупателей")

                    col1, col2 = st.columns(2)

                    # График для FIFO
                    with col1:
                        if 'spoilage_stats' in data and 'fifo_rates' in data['spoilage_stats']:
                            fifo_rates = data['spoilage_stats']['fifo_rates']

                            if fifo_rates:
                                # Определяем ожидаемое значение в зависимости от закона
                                expected_fifo = params.get('fifo_percent', 75)

                                fig_hist_fifo = px.histogram(
                                    x=fifo_rates,
                                    nbins=15,
                                    title=f"FIFO (ожидаемый {expected_fifo}%)",
                                    labels={'x': 'Процент покупателей (%)', 'count': 'Частота'},
                                    opacity=0.8,
                                    color_discrete_sequence=['#27AE60']
                                )

                                # Вертикальная линия для ожидаемого значения
                                fig_hist_fifo.add_vline(
                                    x=expected_fifo,
                                    line_dash="dash",
                                    line_color="red",
                                    annotation_text=f"Ожид. {expected_fifo}%",
                                    annotation_position="top"
                                )

                                # Вертикальная линия для среднего
                                mean_fifo = np.mean(fifo_rates)
                                fig_hist_fifo.add_vline(
                                    x=mean_fifo,
                                    line_dash="solid",
                                    line_color="#27AE60",
                                    annotation_text=f"Ср: {mean_fifo:.2f}%",
                                    annotation_position="bottom"
                                )

                                st.plotly_chart(fig_hist_fifo, use_container_width=True)

                                with st.expander("📊 Статистика FIFO"):
                                    st.write(f"**Среднее:** {mean_fifo:.2f}%")
                                    st.write(f"**Медиана:** {np.median(fifo_rates):.2f}%")
                                    st.write(f"**Ст. отклонение:** {np.std(fifo_rates):.2f}%")
                                    st.write(f"**Мин/Макс:** {min(fifo_rates):.2f}% / {max(fifo_rates):.2f}%")

                    # График для LIFO
                    with col2:
                        if 'spoilage_stats' in data and 'lifo_rates' in data['spoilage_stats']:
                            lifo_rates = data['spoilage_stats']['lifo_rates']

                            if lifo_rates:
                                # Ожидаемое LIFO = 100 - FIFO
                                expected_lifo = 100 - params.get('fifo_percent', 25)

                                fig_hist_lifo = px.histogram(
                                    x=lifo_rates,
                                    nbins=15,
                                    title=f"LIFO (ожидаемый {expected_lifo}%)",
                                    labels={'x': 'Процент покупателей (%)', 'count': 'Частота'},
                                    opacity=0.8,
                                    color_discrete_sequence=['#E74C3C']
                                )

                                # Вертикальная линия для ожидаемого значения
                                fig_hist_lifo.add_vline(
                                    x=expected_lifo,
                                    line_dash="dash",
                                    line_color="red",
                                    annotation_text=f"Ожид. {expected_lifo}%",
                                    annotation_position="top"
                                )

                                # Вертикальная линия для среднего
                                mean_lifo = np.mean(lifo_rates)
                                fig_hist_lifo.add_vline(
                                    x=mean_lifo,
                                    line_dash="solid",
                                    line_color="#E74C3C",
                                    annotation_text=f"Ср: {mean_lifo:.2f}%",
                                    annotation_position="bottom"
                                )

                                st.plotly_chart(fig_hist_lifo, use_container_width=True)

                                with st.expander("📊 Статистика LIFO"):
                                    st.write(f"**Среднее:** {mean_lifo:.2f}%")
                                    st.write(f"**Медиана:** {np.median(lifo_rates):.2f}%")
                                    st.write(f"**Ст. отклонение:** {np.std(lifo_rates):.2f}%")
                                    st.write(f"**Мин/Макс:** {min(lifo_rates):.2f}% / {max(lifo_rates):.2f}%")

                else:  # tomatoes
                    # Для помидоров: гистограмма спроса + ДВЕ гистограммы порчи
                    st.subheader("📊 Анализ распределений (Помидоры)")

                    # Первая строка - спрос
                    col1, col2 = st.columns(2)

                    with col1:
                        # Гистограмма спроса
                        fig_hist_demand = px.histogram(
                            df,
                            x='demand',
                            nbins=15,
                            title=f"Распределение спроса ({distribution})",
                            labels={'demand': 'Спрос (кг)', 'count': 'Частота'},
                            opacity=0.8,
                            color_discrete_sequence=['#A23B72']
                        )

                        # Добавляем вертикальную линию среднего
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
                        st.info("Графики порчи расположены ниже")

                    st.markdown("---")

                    # Вторая строка - два графика порчи
                    st.subheader("📊 Распределение процентов порчи")

                    col1, col2 = st.columns(2)

                    # Гистограмма для 1-й недели (10%)
                    with col1:
                        if 'spoilage_stats' in data and 'week10_rates' in data['spoilage_stats']:
                            week10_rates = data['spoilage_stats']['week10_rates']

                            if week10_rates:
                                fig_hist_10 = px.histogram(
                                    x=week10_rates,
                                    nbins=15,
                                    title="1-я неделя хранения (базовый процент 10%)",
                                    labels={'x': 'Процент порчи (%)', 'count': 'Частота'},
                                    opacity=0.8,
                                    color_discrete_sequence=['#3498DB']
                                )

                                # Вертикальная линия для ожидаемого значения
                                fig_hist_10.add_vline(
                                    x=10.0,
                                    line_dash="dash",
                                    line_color="red",
                                    annotation_text="Ожид. 10%",
                                    annotation_position="top"
                                )

                                # Вертикальная линия для среднего
                                mean10_actual = np.mean(week10_rates)
                                fig_hist_10.add_vline(
                                    x=mean10_actual,
                                    line_dash="solid",
                                    line_color="#3498DB",
                                    annotation_text=f"Ср: {mean10_actual:.2f}%",
                                    annotation_position="bottom"
                                )

                                st.plotly_chart(fig_hist_10, use_container_width=True)

                                with st.expander("📊 Статистика (1-я нед)"):
                                    st.write(f"**Среднее:** {mean10_actual:.2f}%")
                                    st.write(f"**Медиана:** {np.median(week10_rates):.2f}%")
                                    st.write(f"**Ст. отклонение:** {np.std(week10_rates):.2f}%")
                                    st.write(f"**Мин/Макс:** {min(week10_rates):.2f}% / {max(week10_rates):.2f}%")

                    # Гистограмма для 2-й недели (50%)
                    with col2:
                        if 'spoilage_stats' in data and 'week50_rates' in data['spoilage_stats']:
                            week50_rates = data['spoilage_stats']['week50_rates']

                            if week50_rates:
                                fig_hist_50 = px.histogram(
                                    x=week50_rates,
                                    nbins=15,
                                    title="2-я неделя хранения (базовый процент 50%)",
                                    labels={'x': 'Процент порчи (%)', 'count': 'Частота'},
                                    opacity=0.8,
                                    color_discrete_sequence=['#F39C12']
                                )

                                # Вертикальная линия для ожидаемого значения
                                fig_hist_50.add_vline(
                                    x=50.0,
                                    line_dash="dash",
                                    line_color="red",
                                    annotation_text="Ожид. 50%",
                                    annotation_position="top"
                                )

                                # Вертикальная линия для среднего
                                mean50_actual = np.mean(week50_rates)
                                fig_hist_50.add_vline(
                                    x=mean50_actual,
                                    line_dash="solid",
                                    line_color="#F39C12",
                                    annotation_text=f"Ср: {mean50_actual:.2f}%",
                                    annotation_position="bottom"
                                )

                                st.plotly_chart(fig_hist_50, use_container_width=True)

                                with st.expander("📊 Статистика (2-я нед)"):
                                    st.write(f"**Среднее:** {mean50_actual:.2f}%")
                                    st.write(f"**Медиана:** {np.median(week50_rates):.2f}%")
                                    st.write(f"**Ст. отклонение:** {np.std(week50_rates):.2f}%")
                                    st.write(f"**Мин/Макс:** {min(week50_rates):.2f}% / {max(week50_rates):.2f}%")

                st.markdown("---")

            # Статистика спроса из API
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📊 Статистика спроса (из API)")
                if 'demand_stats' in data:
                    stats = data['demand_stats']
                    st.write(f"**Среднее:** {stats.get('mean', 0):.2f}")
                    st.write(f"**Минимум:** {stats.get('min', 0):.2f}")
                    st.write(f"**Максимум:** {stats.get('max', 0):.2f}")
                    if 'sigma' in stats:
                        st.write(f"**Сигма:** {stats['sigma']:.2f}")

            with col2:
                st.subheader("🗑️ Статистика порчи (из API)")
                if product == "milk" and 'spoilage_stats' in data:
                    s = data['spoilage_stats']
                    st.write(f"**FIFO среднее:** {s.get('fifo_mean', 0):.2f}%")
                    st.write(f"**LIFO среднее:** {s.get('lifo_mean', 0):.2f}%")
                elif product == "tomatoes" and 'spoilage_stats' in data:
                    s = data['spoilage_stats']
                    st.write(f"**1-я нед (10%):** {s.get('week10_mean', 0):.2f}%")
                    st.write(f"**2-я нед (50%):** {s.get('week50_mean', 0):.2f}%")

            # Таблица с историей
            with st.expander("📋 Детальная история"):
                st.dataframe(df, use_container_width=True)

        except requests.Timeout:
            st.error("⏰ Превышено время ожидания от сервера (30 секунд)")
            st.info("Попробуйте уменьшить количество дней симуляции")
        except requests.ConnectionError:
            st.error("🔌 Не удалось подключиться к серверу")
            st.info("Убедитесь, что FastAPI сервер запущен: python main.py")
        except requests.HTTPError as e:
            st.error(f"❌ Ошибка сервера: {e}")
            if response.status_code == 500:
                st.info("Проверьте консоль с запущенным API для деталей")
        except json.JSONDecodeError:
            st.error("❌ Ошибка: Сервер вернул некорректный ответ")
        except Exception as e:
            st.error(f"❌ Неожиданная ошибка: {str(e)}")
            st.info("Проверьте что API запущен и параметры корректны")
else:
    st.info("👈 Настройте параметры слева и нажмите 'Запустить симуляцию'")
