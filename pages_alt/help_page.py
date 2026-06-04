import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta


def show():
    """Страница помощи"""
    
    # Создаём вкладки внутри страницы
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 О программе",
        "📊 Интерактивные модели порчи",
        "📈 Генерация спроса",
        "⚙️ Как пользоваться",
        "❓ Частые вопросы"
    ])
    
    # ========== ВКЛАДКА 1: О ПРОГРАММЕ ==========
    with tab1:
        st.markdown("""
        ### 🥛 Симулятор управления запасами скоропортящихся товаров
        
        Программа разработана для анализа и оптимизации управления запасами 
        товаров с ограниченным сроком годности.
        
        **Основные возможности:**
        - 📦 Симуляция работы склада на заданный период
        - 🥛 Учёт двух типов товаров (строгий срок / постепенная порча)
        - 📈 Три модели порчи: линейная, степенная, логистическая
        - 🎲 Два закона распределения спроса: равномерный, нормальный
        - 🚚 Настройка периодичности и типа поставок
        - 📁 Импорт реальных данных о продажах из Excel
        - 📊 Визуализация результатов в графиках и таблицах
        - 💾 Сохранение экспериментов в историю
        
        **Технологии:**
        - Python 3.11
        - FastAPI (бэкенд)
        - Streamlit (фронтенд)
        - SQLite (база данных)
        - Plotly (графики)
        """)
        
        st.info("💡 **Совет:** Для получения оптимальных результатов экспериментируйте с разными параметрами: целевой уровень запаса, периодичность поставок, тип порчи.")
    
    # ========== ВКЛАДКА 2: ИНТЕРАКТИВНЫЕ МОДЕЛИ ПОРЧИ ==========
    with tab2:
        st.markdown("### 📊 Модели порчи")
        st.markdown("Двигайте ползунки, чтобы увидеть, как меняется график порчи в реальном времени.")
        st.markdown("---")
        
        # ----- Контейнер 1: Линейная порча -----
        with st.container():
            st.markdown("#### 📈 1. Линейная порча (равномерное старение)")
            st.markdown("Каждый день портится фиксированный процент от текущего остатка.")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                shelf_life_linear = st.slider(
                    "Срок годности (дней)",
                    min_value=1, max_value=60, value=30, step=1, key="linear_shelf_life"
                )
                st.markdown("**Формула:** `p_день = 100% / T`")
                st.markdown(f"**Ежедневная порча:** {100/shelf_life_linear:.2f}%")
            
            with col2:
                days = list(range(1, shelf_life_linear + 1))
                spoilage = [100 * d / shelf_life_linear for d in days]
                
                fig_linear = go.Figure()
                fig_linear.add_trace(go.Scatter(
                    x=days, y=spoilage, mode='lines',
                    name='Накопленная порча',
                    line=dict(color='#3498DB', width=3),
                    fill='tozeroy', fillcolor='rgba(52, 152, 219, 0.2)'
                ))
                fig_linear.update_layout(
                    title=f"Накопленная порча (срок {shelf_life_linear} дней)",
                    xaxis_title="День", yaxis_title="Порча (%)",
                    template='plotly_white', height=300
                )
                st.plotly_chart(fig_linear, use_container_width=True)
            
            st.markdown("---")
        
        # ----- Контейнер 2: Степенная (параболическая) порча -----
        with st.container():
            st.markdown("#### 📉 2. Степенная порча (ускорение к концу срока)")
            st.markdown("Товар долго остаётся свежим, затем быстро портится в конце срока.")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                shelf_life_power = st.slider(
                    "Срок годности (дней)",
                    min_value=1, max_value=60, value=30, step=1, key="power_shelf_life"
                )
                power = st.slider(
                    "Степень кривизны (p)",
                    min_value=1.5, max_value=4.0, value=2.0, step=0.1, key="power_p",
                    help="p=2 — классическая парабола, p>2 — ещё более резкий рост в конце"
                )
                st.markdown("**Формула:** `S(t) = 100 × (t/T)^p`")
                st.caption(f"При p={power:.1f} кривая пологая в начале, резко растёт в конце")
            
            with col2:
                days = list(range(1, shelf_life_power + 1))
                spoilage = [100 * ((d / shelf_life_power) ** power) for d in days]
                
                fig_power = go.Figure()
                fig_power.add_trace(go.Scatter(
                    x=days, y=spoilage, mode='lines',
                    name='Накопленная порча',
                    line=dict(color='#E74C3C', width=3),
                    fill='tozeroy', fillcolor='rgba(231, 76, 60, 0.2)'
                ))
                fig_power.update_layout(
                    title=f"Накопленная порча (срок {shelf_life_power} дней, степень {power:.1f})",
                    xaxis_title="День", yaxis_title="Порча (%)",
                    template='plotly_white', height=300
                )
                st.plotly_chart(fig_power, use_container_width=True)
            
            st.markdown("---")
        
        # ----- Контейнер 3: Логистическая (S-образная) порча -----
        with st.container():
            st.markdown("#### 📊 3. Логистическая порча (S-образная, резкое старение)")
            st.markdown("Товар долго остаётся свежим, затем очень быстро портится в конце срока.")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                shelf_life_log = st.slider(
                    "Срок годности (дней)",
                    min_value=1, max_value=60, value=30, step=1, key="log_shelf_life"
                )
                k_log = st.slider(
                    "Коэффициент крутизны (k)",
                    min_value=5.0, max_value=30.0, value=15.0, step=1.0, key="log_k",
                    help="Чем больше k, тем резче переход от свежего к испорченному"
                )
                st.markdown("**Формула:** `S(t) = 100 / (1 + e⁻ᵏ⁽ᵗ⁻⁰·⁵⁾)`")
            
            with col2:
                days = list(range(1, shelf_life_log + 1))
                spoilage = []
                for d in days:
                    t = d / shelf_life_log
                    if t <= 0:
                        s = 0
                    elif t >= 1:
                        s = 100
                    else:
                        s = 100 / (1 + np.exp(-k_log * (t - 0.5)))
                    spoilage.append(s)
                
                fig_log = go.Figure()
                fig_log.add_trace(go.Scatter(
                    x=days, y=spoilage, mode='lines',
                    name='Накопленная порча',
                    line=dict(color='#2ECC71', width=3),
                    fill='tozeroy', fillcolor='rgba(46, 204, 113, 0.2)'
                ))
                fig_log.update_layout(
                    title=f"Накопленная порча (срок {shelf_life_log} дней, k={k_log:.0f})",
                    xaxis_title="День", yaxis_title="Порча (%)",
                    template='plotly_white', height=300
                )
                st.plotly_chart(fig_log, use_container_width=True)
            
            st.markdown("---")
        
        # ----- Сравнение всех трёх моделей -----
        with st.container():
            st.markdown("#### 🔍 Сравнение всех трёх моделей")
            
            col1, col2 = st.columns([1, 1.5])
            
            with col1:
                compare_T = st.slider(
                    "Срок годности для сравнения (дней)",
                    min_value=7, max_value=60, value=30, step=1, key="compare_T"
                )
                compare_power = st.slider(
                    "Степень (p)", 1.5, 4.0, 2.0, 0.1, key="compare_power"
                )
                compare_k_log = st.slider(
                    "k (логистическая)", 5.0, 30.0, 15.0, 1.0, key="compare_log_k"
                )
            
            with col2:
                days = list(range(1, compare_T + 1))
                
                # Линейная
                linear = [100 * d / compare_T for d in days]
                
                # Степенная
                power_vals = [100 * ((d / compare_T) ** compare_power) for d in days]
                
                # Логистическая
                logi = []
                for d in days:
                    t = d / compare_T
                    logi.append(100 / (1 + np.exp(-compare_k_log * (t - 0.5))) if t < 1 else 100)
                
                fig_compare = go.Figure()
                fig_compare.add_trace(go.Scatter(x=days, y=linear, mode='lines', 
                                                 name='Линейная', line=dict(color='#3498DB', width=3)))
                fig_compare.add_trace(go.Scatter(x=days, y=power_vals, mode='lines', 
                                                 name='Степенная', line=dict(color='#E74C3C', width=3)))
                fig_compare.add_trace(go.Scatter(x=days, y=logi, mode='lines', 
                                                 name='Логистическая', line=dict(color='#2ECC71', width=3)))
                fig_compare.update_layout(
                    title="Сравнение моделей порчи",
                    xaxis_title="День", yaxis_title="Накопленная порча (%)",
                    template='plotly_white', height=350,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(fig_compare, use_container_width=True)
    
    # ========== ВКЛАДКА 3: ГЕНЕРАЦИЯ СПРОСА ==========
    with tab3:
        st.markdown("### 🎲 Генерация спроса")
        st.markdown("Двигайте ползунки, чтобы увидеть, как генерируется спрос при разных законах распределения.")
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            base_demand = st.slider("📊 Базовый спрос (ед/день)", 50, 500, 200, step=10, key="help_base_demand")
            
            demand_type = st.radio(
                "🎲 Закон распределения",
                options=["uniform", "normal"],
                format_func=lambda x: "Равномерный" if x == "uniform" else "Нормальный",
                horizontal=True,
                key="help_demand_type"
            )
            
            if demand_type == "uniform":
                st.caption(f"Диапазон: от {base_demand * 0.5:.0f} до {base_demand * 1.5:.0f} ед/день")
            else:
                sigma = st.slider("📈 Стандартное отклонение", 5, 100, int(base_demand * 0.15), step=5, key="help_sigma")
                st.caption(f"Среднее: {base_demand}, σ = {sigma}")
        
        with col2:
            days = list(range(1, 101))
            np.random.seed(42)
            
            if demand_type == "uniform":
                demands = [np.random.uniform(base_demand * 0.5, base_demand * 1.5) for _ in days]
            else:
                sigma_val = sigma if 'sigma' in locals() else base_demand * 0.15
                demands = [np.random.normal(base_demand, sigma_val) for _ in days]
            
            fig_demand = go.Figure()
            fig_demand.add_trace(go.Scatter(
                x=days, y=demands, mode='lines+markers',
                name='Спрос', line=dict(color='#2E86AB', width=2),
                marker=dict(size=4, color='#2E86AB')
            ))
            fig_demand.add_hline(y=base_demand, line_dash="dash", line_color="red",
                                annotation_text=f"Базовый: {base_demand}")
            fig_demand.update_layout(
                title="Сгенерированный спрос (100 дней)",
                xaxis_title="День", yaxis_title="Спрос (ед/день)",
                template='plotly_white', height=350
            )
            st.plotly_chart(fig_demand, use_container_width=True)
        
        st.markdown("---")
        st.markdown("""
        **Как это работает в программе:**
        - **Равномерный спрос** — значение может быть любым в указанном диапазоне с равной вероятностью
        - **Нормальный спрос** — значения группируются вокруг среднего, выбросы редки
        - Реальные данные из Excel имеют приоритет над генерацией
        """)
    
    # ========== ВКЛАДКА 4: КАК ПОЛЬЗОВАТЬСЯ ==========
    with tab4:
        st.markdown("### 🚀 Пошаговая инструкция")
        st.markdown("---")
        
        st.markdown("""
        #### Шаг 1. Добавьте товар в базу данных
        
        1. Перейдите на вкладку **«База данных»**
        2. Нажмите кнопку **«➕ Добавить товар»**
        3. Заполните форму (название, цены, срок годности, базовый спрос)
        4. Нажмите **«Сохранить»**
        
        ---
        
        #### Шаг 2. Настройте симуляцию
        
        1. Перейдите на вкладку **«Симуляция»**
        2. Выберите продукт из списка
        3. Выберите **источник данных спроса**:
           - 🎲 «Генерировать случайно» — для теоретических экспериментов
           - 📁 «Загрузить из Excel» — для симуляции на реальных данных
        4. Настройте параметры симуляции:
           - Количество дней
           - Целевой уровень запаса
           - Тип порчи и соответствующий коэффициент
        5. При необходимости откройте **«Настройки»** (⚙️) для изменения законов спроса и поставок
        
        ---
        
        #### Шаг 3. Запустите симуляцию
        
        1. Нажмите **«🚀 Запустить симуляцию»**
        2. Дождитесь окончания расчётов
        3. Изучите результаты:
           - Метрики (выручка, прибыль, потери, средний остаток)
           - Графики спроса, продаж, остатков, порчи
           - Детальную таблицу по дням
        
        ---
        
        #### Шаг 4. Сохраните результаты
        
        1. Нажмите **«💾 Сохранить результат в историю»**
        2. Просмотреть сохранённые эксперименты можно во вкладке **«База данных» → «История экспериментов»**
        
        ---
        
        #### 📥 Импорт реальных данных из Excel
        
        1. В разделе «Источник данных спроса» выберите **«Загрузить из Excel»**
        2. Нажмите **«📥 Шаблон»**, чтобы скачать шаблон
        3. Заполните файл (колонки: `Дата`, `Спрос`)
        4. Загрузите заполненный файл
        5. Запустите симуляцию — программа будет использовать реальный спрос
        
        > **Примечание:** Если в загруженном файле нет данных на какой-то день, будет использован базовый спрос из БД.
        """)
    
    # ========== ВКЛАДКА 5: ЧАСТЫЕ ВОПРОСЫ ==========
    with tab5:
        st.markdown("### ❓ Часто задаваемые вопросы")
        st.markdown("---")
        
        with st.expander("📈 Чем отличаются три модели порчи?"):
            st.markdown("""
            - **Линейная** — товар портится равномерно каждый день.  
              *Пример: картофель, лук, крупы.*
              
            - **Степенная (параболическая)** — товар долго остаётся свежим, затем быстро портится в конце срока.  
              *Пример: помидоры, бананы, клубника.*
              
            - **Логистическая (S-образная)** — товар долго остаётся свежим, затем очень резко портится.  
              *Пример: быстро портящиеся фрукты и ягоды.*
            """)
        
        with st.expander("🎚️ Что такое «степень кривизны (p)»?"):
            st.markdown("""
            Параметр, определяющий **резкость роста порчи** в конце срока.
            - **p = 2** — классическая парабола
            - **p > 2** — ещё более резкий рост в конце
            - Рекомендуемое значение: **p = 2.0**
            """)
        
        with st.expander("📊 Что такое «коэффициент крутизны (k)» для логистической модели?"):
            st.markdown("""
            Параметр, определяющий **резкость перехода** от свежего состояния к испорченному.
            - **Чем больше k** — тем резче переход
            - Рекомендуемое значение: **k = 15**
            """)
        
        with st.expander("💸 Почему прибыль может быть отрицательной?"):
            st.markdown("""
            Отрицательная прибыль (убыток) означает, что **затраты на закупку превысили выручку от продаж**. 
            Это нормально для экспериментов — так вы находите оптимальные параметры.
            
            **Причины убытков:**
            - Слишком большой запас → много порчи
            - Слишком маленький запас → неудовлетворённый спрос
            - Низкая цена продажи относительно закупки
            """)
        
        with st.expander("📦 Что такое «целевой уровень запаса»?"):
            st.markdown("""
            Минимальное количество товара, которое должно быть на складе. 
            При снижении запаса ниже этого уровня происходит **автоматический заказ** новой партии.
            
            **Совет:** Оптимальный запас обычно составляет 2-3 дневных объёма продаж.
            """)
        
        with st.expander("📁 Как загрузить реальные данные из Excel?"):
            st.markdown("""
            1. В разделе «Источник данных спроса» выберите **«Загрузить из Excel»**
            2. Нажмите **«📥 Шаблон»** и скачайте файл
            3. Заполните колонки: `Дата` (в формате ГГГГ-ММ-ДД) и `Спрос` (число)
            4. Загрузите заполненный файл через **file_uploader**
            5. Запустите симуляцию
            """)
        
        with st.expander("📊 Что показывает «средний остаток»?"):
            st.markdown("""
            Средний запас товара на складе за период симуляции.
            
            - **Низкий остаток** → мало замороженных средств, но риск дефицита
            - **Высокий остаток** → больше затрат, но выше доступность товара
            """)
        
        with st.expander("🔄 Как обновить страницу при зависании?"):
            st.markdown("""
            1. Нажмите **F5** или кнопку обновления браузера
            2. Если не помогло, остановите и перезапустите программу:
               ```bash
               python main.py
               streamlit run app.py
            """)