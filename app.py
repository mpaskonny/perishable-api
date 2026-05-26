import streamlit as st

st.set_page_config(
    page_title="Симулятор продуктов",
    page_icon="🥛",
    layout="wide"
)

# Фикс ширины страницы и стили
st.markdown("""
    <style>
        /* Убираем боковую панель */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Расширяем основной контент */
        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        
        /* Стили для вкладок - тёмная тема, растянутые */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0 !important;
            background: linear-gradient(135deg, #1a1a2e, #16213e) !important;
            padding: 0.75rem 1.5rem !important;
            margin: 0 !important;
            border-radius: 15px !important;
            border: 1px solid #2a2a4a !important;
            display: flex !important;
            width: 100% !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-size: 1.1rem !important;
            font-weight: 500 !important;
            padding: 0.75rem 0 !important;
            color: #c0c0d0 !important;
            background-color: transparent !important;
            border-radius: 10px !important;
            transition: all 0.2s !important;
            flex: 1 !important;
            text-align: center !important;
        }
        
        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(233, 69, 96, 0.1) !important;
            color: #e94560 !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #e94560, #533483) !important;
            color: white !important;
        }
        
        .simulation-title {
            font-size: 2rem;
            font-weight: bold;
            background: linear-gradient(135deg, #e94560, #533483);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0;
        }
        
        .main-title {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            background: linear-gradient(135deg, #e94560, #533483);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            font-size: 1.1rem;
            text-align: center;
            color: #a0a0b0;
            margin-bottom: 2rem;
        }
        .section-title {
            color: #e94560;
            margin-bottom: 1rem;
            font-size: 1.6rem;
            font-weight: 600;
        }
        .feature-card {
            background-color: #16213e;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            height: 100%;
            transition: transform 0.2s;
            border: 1px solid #2a2a4a;
        }
        .feature-card:hover {
            transform: translateY(-5px);
            border-color: #e94560;
        }
        .feature-title {
            font-size: 1.4rem;
            font-weight: bold;
            margin-bottom: 1rem;
            text-align: center;
            color: #e94560;
        }
        .feature-card ul {
            color: #c0c0d0;
            padding-left: 1.2rem;
        }
        .feature-card li {
            margin-bottom: 0.5rem;
        }
        .step-number {
            display: inline-block;
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #e94560, #533483);
            color: white;
            border-radius: 50%;
            text-align: center;
            line-height: 32px;
            font-weight: bold;
            margin-right: 12px;
        }
        .step-text {
            color: #c0c0d0;
        }
        .steps-container {
            background-color: #16213e;
            padding: 1.5rem;
            border-radius: 15px;
            border: 1px solid #2a2a4a;
        }
        .welcome-banner {
            background: linear-gradient(135deg, #16213e, #1a1a2e);
            padding: 1.2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            border-left: 4px solid #e94560;
            color: #c0c0d0;
        }
        .welcome-banner h3 {
            color: #e94560;
            margin: 0;
        }
        .about-text {
            color: #c0c0d0;
            font-size: 1rem;
            line-height: 1.6;
            background-color: #16213e;
            padding: 1rem;
            border-radius: 10px;
        }
        .footer {
            text-align: center;
            padding: 2rem;
            color: #6a6a80;
            font-size: 0.8rem;
            border-top: 1px solid #2a2a4a;
            margin-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# Загрузка стилей
with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Инициализация общих настроек
if 'settings' not in st.session_state:
    st.session_state.settings = {
        'distribution': 'uniform',
        'weekday_factors': [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1],
        'delivery_type': 'unit',
        'box_size': 20,
        'delivery_frequency': 2,
        'delivery_days': [0, 3],
        'schedule_type': 'frequency',
        'use_custom_bounds': False,
        'demand_min': None,
        'demand_max': None
    }


# ========== МОДАЛЬНОЕ ОКНО НАСТРОЕК ==========
@st.dialog("⚙️ **Настройки симуляции**", width="large")
def settings_dialog():
    """Модальное окно с общими настройками"""
    
    # Получаем базовый спрос из session_state (устанавливается в simulation_page)
    base_demand = st.session_state.get('current_base_demand', 100)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Параметры спроса")
        
        distribution = st.selectbox(
            "Закон распределения",
            options=["uniform", "normal"],
            format_func=lambda x: "📊 Равномерный" if x == "uniform" else "📈 Нормальный",
            index=0 if st.session_state.settings.get('distribution') == 'uniform' else 1,
            key="dialog_distribution"
        )
        
        if distribution == "uniform":
            use_custom_bounds = st.checkbox(
                "🎯 Задать границы спроса вручную",
                value=st.session_state.settings.get('use_custom_bounds', False),
                key="dialog_use_custom_bounds"
            )
            
            if use_custom_bounds:
                col_min, col_max = st.columns(2)
                with col_min:
                    demand_min = st.number_input(
                        "Мин. спрос (ед/день)",
                        min_value=0.0,
                        value=st.session_state.settings.get('demand_min', base_demand * 0.5),
                        step=5.0,
                        key="dialog_demand_min"
                    )
                with col_max:
                    demand_max = st.number_input(
                        "Макс. спрос (ед/день)",
                        min_value=0.0,
                        value=st.session_state.settings.get('demand_max', base_demand * 1.5),
                        step=5.0,
                        key="dialog_demand_max"
                    )
                
                if demand_min is not None and demand_max is not None:
                    if demand_min >= demand_max:
                        st.error("❌ Мин. спрос должен быть меньше макс. спроса")
                    
                    calculated_mean = (demand_min + demand_max) / 2
                    if abs(calculated_mean - base_demand) > 0.1:
                        st.warning(f"⚠️ Среднее значение ({calculated_mean:.1f}) отличается от базового спроса в БД ({base_demand:.1f})")
                        st.caption("Вы можете продолжить или скорректировать границы.")
                
                st.caption(f"📊 Базовый спрос из БД: {base_demand:.0f} ед/день")
            else:
                demand_min = None
                demand_max = None
                st.caption(f"📊 Автоматически: от {base_demand * 0.5:.0f} до {base_demand * 1.5:.0f} ед/день")
        else:
            demand_min = None
            demand_max = None
        
        # Коэффициенты дней недели
        st.markdown("---")
        st.subheader("📅 Коэффициенты спроса по дням недели")
        st.info("Базовый спрос умножается на коэффициент дня недели")
        
        factors = st.session_state.settings.get('weekday_factors', [0.8, 0.6, 0.9, 1.0, 1.3, 1.5, 1.1])
        cols = st.columns(7)
        with cols[0]: mon = st.number_input("Пн", value=factors[0], step=0.1, format="%.1f", key="dialog_mon")
        with cols[1]: tue = st.number_input("Вт", value=factors[1], step=0.1, format="%.1f", key="dialog_tue")
        with cols[2]: wed = st.number_input("Ср", value=factors[2], step=0.1, format="%.1f", key="dialog_wed")
        with cols[3]: thu = st.number_input("Чт", value=factors[3], step=0.1, format="%.1f", key="dialog_thu")
        with cols[4]: fri = st.number_input("Пт", value=factors[4], step=0.1, format="%.1f", key="dialog_fri")
        with cols[5]: sat = st.number_input("Сб", value=factors[5], step=0.1, format="%.1f", key="dialog_sat")
        with cols[6]: sun = st.number_input("Вс", value=factors[6], step=0.1, format="%.1f", key="dialog_sun")
        
        weekday_factors = [mon, tue, wed, thu, fri, sat, sun]
    
    with col2:
        st.subheader("🚚 Параметры поставок")
        delivery_type = st.radio(
            "Способ поставки", 
            options=["unit", "box"], 
            format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками/ящиками",
            horizontal=True,
            index=0 if st.session_state.settings.get('delivery_type') == 'unit' else 1,
            key="dialog_delivery_type"
        )
        
        box_size = st.session_state.settings.get('box_size', 20)
        if delivery_type == "box":
            box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=box_size, step=5, key="dialog_box_size")
        
        st.subheader("📅 Расписание поставок")
        schedule_type = st.radio(
            "Тип расписания",
            options=["frequency", "days"],
            format_func=lambda x: "📅 Периодичность (каждые N дней)" if x == "frequency" else "📅 Конкретные дни недели",
            horizontal=True,
            index=0 if st.session_state.settings.get('schedule_type') == 'frequency' else 1,
            key="dialog_schedule"
        )
        
        if schedule_type == "frequency":
            delivery_frequency = st.number_input(
                "Периодичность поставок (дней)", 
                min_value=1, 
                max_value=365, 
                value=st.session_state.settings.get('delivery_frequency', 2),
                step=1,
                key="dialog_freq"
            )
            delivery_days = []
        else:
            delivery_frequency = 0
            day_map = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
            reverse_map = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}
            current_days = [reverse_map[d] for d in st.session_state.settings.get('delivery_days', [0, 3])]
            selected_days = st.multiselect(
                "Дни поставок", 
                options=["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"], 
                default=current_days,
                key="dialog_days"
            )
            delivery_days = [day_map[d] for d in selected_days]
        
        st.markdown("---")
        st.subheader("💰 Стоимость доставки")

        delivery_cost_type = st.selectbox(
            "Тип расчёта",
            options=["none", "fixed", "rate", "combined"],
            format_func=lambda x: {
                "none": "🚫 Не учитывать",
                "fixed": "📦 Фиксированная (за одну поставку)",
                "rate": "📊 Тариф за кг/шт",
                "combined": "🔧 Комбинированная (фикс + тариф)"
            }[x],
            index=["none", "fixed", "rate", "combined"].index(
                st.session_state.settings.get('delivery_cost_type', 'none')
            ),
            key="dialog_delivery_cost_type"
        )

        delivery_fixed_cost = 0.0
        delivery_rate_cost = 0.0

        if delivery_cost_type in ["fixed", "combined"]:
            delivery_fixed_cost = st.number_input(
                "Фиксированная стоимость (руб)",
                min_value=0.0,
                value=st.session_state.settings.get('delivery_fixed_cost', 500.0),
                step=50.0,
                key="dialog_delivery_fixed"
            )

        if delivery_cost_type in ["rate", "combined"]:
            delivery_rate_cost = st.number_input(
                "Тариф за кг/шт (руб)",
                min_value=0.0,
                value=st.session_state.settings.get('delivery_rate_cost', 5.0),
                step=1.0,
                key="dialog_delivery_rate"
            )

        if delivery_cost_type != "none":
            st.caption(f"📊 Пример: при заказе 100 кг стоимость = "
                    f"{delivery_fixed_cost + delivery_rate_cost * 100:.0f} руб")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ Сохранить настройки", type="primary", use_container_width=True, key="dialog_save"):
            st.session_state.settings = {
                'distribution': distribution,
                'weekday_factors': weekday_factors,
                'delivery_type': delivery_type,
                'box_size': box_size,
                'delivery_frequency': delivery_frequency,
                'delivery_days': delivery_days,
                'schedule_type': schedule_type,
                'use_custom_bounds': use_custom_bounds if distribution == "uniform" else False,
                'demand_min': demand_min if distribution == "uniform" and use_custom_bounds else None,
                'demand_max': demand_max if distribution == "uniform" and use_custom_bounds else None,
                'delivery_cost_type': delivery_cost_type,
                'delivery_fixed_cost': delivery_fixed_cost,
                'delivery_rate_cost': delivery_rate_cost
            }
            st.rerun()


# ========== ОСНОВНОЙ КОНТЕНТ ==========
tab1, tab2, tab3, tab4 = st.tabs(["🏠 **Главная**", "🎮 **Симуляция**", "🗄️ **База данных**", "📖 **Помощь**"])

# ========== ВКЛАДКА 1: ГЛАВНАЯ ==========
with tab1:
    st.markdown('<div class="main-title">🥛 Симулятор продуктов</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">с ограниченным сроком годности</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("""
    <div class="welcome-banner">
        <h3>👋 Добро пожаловать!</h3>
        <p>Это приложение поможет вам проанализировать и оптимизировать управление запасами 
        скоропортящихся товаров. Проводите эксперименты, сравнивайте стратегии и выбирайте 
        оптимальные решения.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<h2 class="section-title">📖 О проекте</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="about-text">
    Разработан в рамках выпускной квалификационной работы по теме:<br>
    <b>«Анализ и совершенствование моделей и алгоритмов управления запасами  
    товаров с ограниченным сроком годности»</b><br><br>
    Проект представляет собой имитационную модель для анализа эффективности  
    различных стратегий управления запасами скоропортящихся товаров.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Возможности
    st.markdown('<h2 class="section-title">🎯 Возможности</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">📦 Два типа товаров</div>
            <ul>
                <li><b>Строгий срок годности</b> (молоко)<br>
                Порча наступает мгновенно после истечения срока</li>
                <li><b>Постепенная порча</b> (овощи/фрукты)<br>
                Порча нарастает по дням (линейно, степенная, логистическая)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">📊 Гибкие настройки</div>
            <ul>
                <li>Три модели порчи</li>
                <li>Два закона распределения спроса</li>
                <li>Стратегии поставок (периодические / по дням)</li>
                <li>Поведение покупателей (FIFO / LIFO)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-title">📈 Визуализация</div>
            <ul>
                <li>Графики спроса, продаж и остатков</li>
                <li>Гистограммы распределений</li>
                <li>Детальные таблицы</li>
                <li>Экспорт результатов в CSV</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Как начать
    st.markdown('<h2 class="section-title">🚀 Как начать</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="steps-container">
        <p><span class="step-number">1</span> <span class="step-text">Перейдите на вкладку <b>«Симуляция»</b> сверху</span></p>
        <p><span class="step-number">2</span> <span class="step-text">Выберите продукт из базы данных</span></p>
        <p><span class="step-number">3</span> <span class="step-text">Настройте параметры симуляции (количество дней, целевой запас, тип порчи)</span></p>
        <p><span class="step-number">4</span> <span class="step-text">При необходимости откройте <b>«Настройки»</b> (⚙️) для изменения законов спроса и поставок</span></p>
        <p><span class="step-number">5</span> <span class="step-text">Нажмите <b>«Запустить симуляцию»</b> и анализируйте результаты</span></p>
        <p style="margin-top: 1rem;"><span class="step-text">🗄️ Для добавления собственных товаров перейдите на вкладку <b>«База данных»</b></span></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Исходный код
    st.markdown('<h2 class="section-title">📁 Исходный код</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="about-text">
    Проект доступен на GitHub:<br>
    <a href="https://github.com/mpaskonny/perishable-api" target="_blank">https://github.com/mpaskonny/perishable-api</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    <div class="footer">
        <b>АлтГТУ, ФИТ</b><br>
        ВКР • 2026<br>
        Авторы: <b>Пасконный Мирон Дмитриевич и Снегирев Александр Сергеевич</b> | Группа: <b>ПИЭ-21</b>
    </div>
    """, unsafe_allow_html=True)


# ========== ВКЛАДКА 2: СИМУЛЯЦИЯ ==========
with tab2:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown('<div class="simulation-title">🎮 Симуляция управления запасами</div>', unsafe_allow_html=True)
    with col2:
        if st.button("⚙️ Настройки", help="Открыть общие настройки", use_container_width=True):
            settings_dialog()
    
    st.markdown("---")
    
    from pages_alt import simulation_page
    simulation_page.show()


# ========== ВКЛАДКА 3: БАЗА ДАННЫХ ==========
with tab3:
    st.markdown('<div class="simulation-title">🗄️ Управление базой данных</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    from pages_alt import database_page
    database_page.show()


# ========== ВКЛАДКА 4: ПОМОЩЬ ==========
with tab4:
    from pages_alt.help_page import show as help_page_show
    help_page_show()
