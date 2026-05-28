import streamlit as st
import glob
import os
import pandas as pd
from datetime import datetime, timedelta

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
        'spoilage_type': 'linear',
        'power_p': 2.0,
        'logistic_k': 15.0,
        'fifo_percent': 75,
        'use_custom_bounds': False,
        'demand_min': None,
        'demand_max': None,
        'delivery_cost_type': 'none',
        'delivery_fixed_cost': 0.0,
        'delivery_rate_cost': 0.0,
        'strategy_type': 'r_s',
        'delivery_type': 'unit',
        'box_size': 20,
        'fixed_quantity': None,
        'delivery_frequency': 2,
        'delivery_days': [0, 3],
        'schedule_type': 'frequency',
        'reorder_point': None,
        'max_stock': None,
        'min_stock': 300
    }

# Инициализация для реальных данных
if 'use_real_demand' not in st.session_state:
    st.session_state.use_real_demand = False
if 'real_demand_dates' not in st.session_state:
    st.session_state.real_demand_dates = None
if 'real_demand_values' not in st.session_state:
    st.session_state.real_demand_values = None
if 'real_start_date' not in st.session_state:
    st.session_state.real_start_date = None


# ========== МОДАЛЬНОЕ ОКНО НАСТРОЕК ==========
@st.dialog("⚙️ **Настройки симуляции**", width="large")
def settings_dialog():
    """Модальное окно с общими настройками"""
    
    # Очищаем временные результаты при открытии окна
    if 'calculated_factors' in st.session_state:
        st.session_state.calculated_factors = None
    
    # Получаем базовый спрос и категорию продукта из session_state
    base_demand = st.session_state.get('current_base_demand', 100)
    product_category = st.session_state.get('current_product_category', 'gradual')
    
    # Создаём вкладки внутри модального окна
    tab1, tab2, tab3 = st.tabs(["📊 Общие настройки", "🎮 Стратегия поставок", "💰 Доставка"])
    
    # ========== ВКЛАДКА 1: ОБЩИЕ НАСТРОЙКИ ==========
    with tab1:
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
        
        with col2:
            # Условное отображение: для строгих товаров - FIFO/LIFO, для gradual - параметры порчи
            if product_category == "strict":
                st.subheader("👥 Распределение покупателей (для молока)")
                fifo_percent = st.slider(
                    "FIFO % (остальные LIFO)",
                    min_value=0,
                    max_value=100,
                    value=st.session_state.settings.get('fifo_percent', 75),
                    step=5,
                    key="dialog_fifo_percent"
                )
                # Сохраняем значения порчи (не используются, но нужны для сохранения)
                spoilage_type = st.session_state.settings.get('spoilage_type', 'linear')
                power_p = st.session_state.settings.get('power_p', 2.0)
                logistic_k = st.session_state.settings.get('logistic_k', 15.0)
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
                    index=0 if st.session_state.settings.get('spoilage_type') == 'linear' 
                          else 1 if st.session_state.settings.get('spoilage_type') == 'power'
                          else 2,
                    key="dialog_spoilage_type"
                )
                
                power_p = 2.0
                logistic_k = 15.0
                
                if spoilage_type == "power":
                    power_p = st.slider(
                        "Степень кривизны (p)", 
                        min_value=1.5, 
                        max_value=4.0, 
                        value=st.session_state.settings.get('power_p', 2.0),
                        step=0.1,
                        help="Чем больше p, тем резче рост порчи в конце срока",
                        key="dialog_power_p"
                    )
                elif spoilage_type == "logistic":
                    logistic_k = st.slider(
                        "Коэффициент крутизны (k)", 
                        min_value=5.0, 
                        max_value=30.0, 
                        value=st.session_state.settings.get('logistic_k', 15.0),
                        step=1.0,
                        help="Чем больше k, тем резче переход от свежего к испорченному",
                        key="dialog_logistic_k"
                    )
                
                # Сохраняем FIFO (не используется)
                fifo_percent = st.session_state.settings.get('fifo_percent', 75)
        
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

                # ========== БЛОК ВЫБОРА ДАТ ==========
        st.markdown("---")
        st.subheader("📅 Период симуляции")
        
        # Получаем текущие даты из session_state или значения по умолчанию
        sim_start_date = st.session_state.settings.get('sim_start_date', '2026-02-01')
        sim_end_date = st.session_state.settings.get('sim_end_date', '2026-03-03')
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input(
                "Дата начала",
                value=datetime.strptime(sim_start_date, '%Y-%m-%d').date(),
                key="dialog_start_date"
            )
        with col_date2:
            end_date = st.date_input(
                "Дата окончания",
                value=datetime.strptime(sim_end_date, '%Y-%m-%d').date(),
                key="dialog_end_date"
            )
        
        if start_date and end_date:
            days_count = (end_date - start_date).days + 1
            if days_count < 1:
                st.error("❌ Дата окончания должна быть позже даты начала")
            else:
                st.caption(f"📊 Длительность симуляции: {days_count} дней")
        
        # Источник данных спроса
        st.markdown("---")
        st.subheader("📁 Источник данных спроса")
        
        demand_source = st.radio(
            "Выберите источник",
            options=["generated", "excel"],
            format_func=lambda x: "🎲 Генерировать случайно" if x == "generated" else "📁 Загрузить из Excel (реальные данные)",
            horizontal=True,
            key="dialog_demand_source"
        )
        
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
                        key="dialog_download_template",
                        help="Скачать шаблон Excel для заполнения"
                    )
            
            st.caption("📝 Заполните шаблон и загрузите ниже:")
            
            uploaded_file = st.file_uploader(
                "Загрузите файл",
                type=['xlsx', 'xls'],
                help="Файл должен содержать колонки: 'Дата' и 'Спрос'",
                key="dialog_demand_file",
                label_visibility="collapsed"
            )
            
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    
                    has_date = any(col in df.columns for col in ['Дата', 'Date', 'ДАТА', 'date'])
                    has_demand = any(col in df.columns for col in ['Спрос', 'Demand', 'demand', 'СПРОС'])
                    
                    if has_date and has_demand:
                        date_col = None
                        for col in ['Дата', 'Date', 'ДАТА', 'date']:
                            if col in df.columns:
                                date_col = col
                                break
                        
                        dates = pd.to_datetime(df[date_col])
                        start_date_dt = dates.min()
                        end_date_dt = dates.max()
                        days_count = (end_date_dt - start_date_dt).days + 1
                        
                        st.session_state.real_demand_dates = dates.dt.strftime('%Y-%m-%d').tolist()
                        st.session_state.real_demand_values = df['Спрос'].tolist()
                        st.session_state.real_start_date = start_date_dt.isoformat()
                        st.session_state.use_real_demand = True
                        
                        st.success(f"✅ Загружено {len(df)} записей. Период: {start_date_dt.strftime('%d.%m.%Y')} — {end_date_dt.strftime('%d.%m.%Y')}")
                        st.info(f"📅 Количество дней симуляции: {days_count}")
                    else:
                        st.error("❌ Файл должен содержать колонки 'Дата' и 'Спрос'")
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
        else:
            st.session_state.use_real_demand = False
            st.session_state.real_demand_dates = None
            st.session_state.real_demand_values = None
            st.session_state.real_start_date = None
    
    # ========== ВКЛАДКА 2: СТРАТЕГИЯ ПОСТАВОК ==========
    with tab2:
        st.markdown("### 🎯 Выберите стратегию")
        
        strategy_type = st.radio(
            "Стратегия",
            options=["r_s", "r_q", "s_s", "custom"],
            format_func=lambda x: {
                "r_s": "📅 (R, S) — Периодическая до целевого уровня",
                "r_q": "📦 (R, Q) — Фиксированный объём по расписанию",
                "s_s": "📊 (s, S) — Двухуровневая (точка заказа)",
                "custom": "🔧 Пользовательская (конструктор)"
            }[x],
            key="dialog_strategy_type",
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### 📋 Параметры стратегии")
        
        # ===== (R, S) =====
        if strategy_type == "r_s":
            delivery_type = st.radio(
                "Способ поставки",
                options=["unit", "box"],
                format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками/ящиками",
                horizontal=True,
                key="dialog_r_s_delivery_type"
            )
            
            box_size = 0
            if delivery_type == "box":
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=20, step=5, key="dialog_r_s_box_size")
            
            st.subheader("📅 Расписание поставок")
            schedule_type = st.radio(
                "Тип расписания",
                options=["frequency", "days"],
                format_func=lambda x: "Периодичность (каждые N дней)" if x == "frequency" else "Конкретные дни недели",
                horizontal=True,
                key="dialog_r_s_schedule"
            )
            
            if schedule_type == "frequency":
                delivery_frequency = st.number_input("Периодичность (дней)", min_value=1, value=2, step=1, key="dialog_r_s_freq")
                delivery_days = []
            else:
                delivery_frequency = 0
                day_map = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
                selected_days = st.multiselect("Дни поставок", ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"], default=["Пн","Чт"], key="dialog_r_s_days")
                delivery_days = [day_map[d] for d in selected_days]
            
            min_stock = st.number_input("📦 Целевой уровень запаса", min_value=0.0, value=300.0, step=50.0, key="dialog_r_s_min_stock")
            
            fixed_quantity = None
            reorder_point = None
            max_stock = None
        
        # ===== (R, Q) =====
        elif strategy_type == "r_q":
            fixed_quantity = st.number_input("📦 Фиксированный объём поставки (шт/кг)", min_value=1, value=100, step=10, key="dialog_r_q_fixed")
            
            st.subheader("📅 Расписание поставок")
            schedule_type = st.radio(
                "Тип расписания",
                options=["frequency", "days"],
                format_func=lambda x: "Периодичность (каждые N дней)" if x == "frequency" else "Конкретные дни недели",
                horizontal=True,
                key="dialog_r_q_schedule"
            )
            
            if schedule_type == "frequency":
                delivery_frequency = st.number_input("Периодичность (дней)", min_value=1, value=2, step=1, key="dialog_r_q_freq")
                delivery_days = []
            else:
                delivery_frequency = 0
                day_map = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
                selected_days = st.multiselect("Дни поставок", ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"], default=["Пн","Чт"], key="dialog_r_q_days")
                delivery_days = [day_map[d] for d in selected_days]
            
            delivery_type = "fixed"
            box_size = 0
            min_stock = 0
            reorder_point = None
            max_stock = None
        
        # ===== (s, S) =====
        elif strategy_type == "s_s":
            delivery_type = st.radio(
                "Способ поставки",
                options=["unit", "box"],
                format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками/ящиками",
                horizontal=True,
                key="dialog_s_s_delivery_type"
            )
            
            box_size = 0
            if delivery_type == "box":
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=20, step=5, key="dialog_s_s_box_size")
            
            col1, col2 = st.columns(2)
            with col1:
                reorder_point = st.number_input("📉 Точка заказа (s)", min_value=0.0, value=100.0, step=10.0, key="dialog_s_s_reorder")
            with col2:
                max_stock = st.number_input("📈 Максимальный запас (S)", min_value=0.0, value=300.0, step=50.0, key="dialog_s_s_max")
            
            st.caption("⚡ Поставка происходит при остатке ниже s, независимо от расписания")
            
            fixed_quantity = None
            delivery_frequency = 0
            delivery_days = []
            min_stock = max_stock
        
        # ===== Пользовательская =====
        else:  # custom
            st.info("🔧 Конструктор стратегии: выберите, как будет работать пополнение запасов")
            
            st.subheader("⏰ Когда делать заказ?")
            trigger_type = st.radio(
                "Триггер заказа",
                options=["schedule", "reorder_point"],
                format_func=lambda x: "📅 По расписанию" if x == "schedule" else "📉 При остатке ниже s",
                horizontal=True,
                key="dialog_custom_trigger"
            )
            
            if trigger_type == "schedule":
                schedule_type = st.radio(
                    "Тип расписания",
                    options=["frequency", "days"],
                    format_func=lambda x: "Периодичность (каждые N дней)" if x == "frequency" else "Конкретные дни недели",
                    horizontal=True,
                    key="dialog_custom_schedule"
                )
                
                if schedule_type == "frequency":
                    delivery_frequency = st.number_input("Периодичность (дней)", min_value=1, value=2, step=1, key="dialog_custom_freq")
                    delivery_days = []
                else:
                    delivery_frequency = 0
                    day_map = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
                    selected_days = st.multiselect("Дни поставок", ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"], default=["Пн","Чт"], key="dialog_custom_days")
                    delivery_days = [day_map[d] for d in selected_days]
                
                reorder_point = None
            else:
                delivery_frequency = 0
                delivery_days = []
                reorder_point = st.number_input("📉 Точка заказа (s)", min_value=0.0, value=100.0, step=10.0, key="dialog_custom_reorder")
                schedule_type = None
            
            st.subheader("📦 Что заказываем?")
            order_type = st.radio(
                "Тип заказа",
                options=["to_level", "fixed_quantity"],
                format_func=lambda x: "📈 До целевого уровня S" if x == "to_level" else "📦 Фиксированный объём Q",
                horizontal=True,
                key="dialog_custom_order"
            )
            
            if order_type == "to_level":
                max_stock = st.number_input("📈 Максимальный запас (S)", min_value=0.0, value=300.0, step=50.0, key="dialog_custom_max")
                fixed_quantity = None
                min_stock = max_stock
            else:
                fixed_quantity = st.number_input("📦 Фиксированный объём Q", min_value=1, value=100, step=10, key="dialog_custom_fixed")
                max_stock = None
                min_stock = 0
            
            delivery_type = st.radio(
                "Способ поставки (для штучных заказов)",
                options=["unit", "box"],
                format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками/ящиками",
                horizontal=True,
                key="dialog_custom_delivery"
            )
            
            box_size = 0
            if delivery_type == "box":
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=20, step=5, key="dialog_custom_box_size")
    
    # ========== ВКЛАДКА 3: ДОСТАВКА ==========
    with tab3:
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
    
    # ========== КНОПКИ СОХРАНЕНИЯ ==========
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ Сохранить настройки", type="primary", use_container_width=True, key="dialog_save"):
            # Получаем значения в зависимости от выбранной стратегии
            if strategy_type == "r_s":
                final_delivery_type = delivery_type
                final_box_size = box_size
                final_fixed_quantity = None
                final_delivery_frequency = delivery_frequency
                final_delivery_days = delivery_days
                final_schedule_type = schedule_type
                final_reorder_point = None
                final_max_stock = None
                final_min_stock = min_stock
            elif strategy_type == "r_q":
                final_delivery_type = "fixed"
                final_box_size = 0
                final_fixed_quantity = fixed_quantity
                final_delivery_frequency = delivery_frequency
                final_delivery_days = delivery_days
                final_schedule_type = schedule_type
                final_reorder_point = None
                final_max_stock = None
                final_min_stock = 0
            elif strategy_type == "s_s":
                final_delivery_type = delivery_type
                final_box_size = box_size
                final_fixed_quantity = None
                final_delivery_frequency = 0
                final_delivery_days = []
                final_schedule_type = None
                final_reorder_point = reorder_point
                final_max_stock = max_stock
                final_min_stock = max_stock
            else:  # custom
                final_delivery_type = delivery_type
                final_box_size = box_size
                final_fixed_quantity = fixed_quantity if 'fixed_quantity' in dir() else None
                final_delivery_frequency = delivery_frequency if 'delivery_frequency' in dir() else 0
                final_delivery_days = delivery_days if 'delivery_days' in dir() else []
                final_schedule_type = schedule_type if 'schedule_type' in dir() else None
                final_reorder_point = reorder_point if 'reorder_point' in dir() else None
                final_max_stock = max_stock if 'max_stock' in dir() else None
                final_min_stock = min_stock if 'min_stock' in dir() else 0
            
            st.session_state.settings = {
                # Общие настройки
                'distribution': distribution,
                'weekday_factors': weekday_factors,
                'spoilage_type': spoilage_type,
                'power_p': power_p,
                'logistic_k': logistic_k,
                'fifo_percent': fifo_percent,
                'use_custom_bounds': use_custom_bounds if distribution == "uniform" else False,
                'demand_min': demand_min if distribution == "uniform" and use_custom_bounds else None,
                'demand_max': demand_max if distribution == "uniform" and use_custom_bounds else None,
                # Даты симуляции (ДОБАВЛЕНО)
                'sim_start_date': start_date.strftime('%Y-%m-%d'),
                'sim_end_date': end_date.strftime('%Y-%m-%d'),
                # Доставка
                'delivery_cost_type': delivery_cost_type,
                'delivery_fixed_cost': delivery_fixed_cost,
                'delivery_rate_cost': delivery_rate_cost,
                # Стратегия
                'strategy_type': strategy_type,
                'delivery_type': final_delivery_type,
                'box_size': final_box_size,
                'fixed_quantity': final_fixed_quantity,
                'delivery_frequency': final_delivery_frequency,
                'delivery_days': final_delivery_days,
                'schedule_type': final_schedule_type,
                'reorder_point': final_reorder_point,
                'max_stock': final_max_stock,
                'min_stock': final_min_stock
            }
            st.success("✅ Настройки сохранены!")
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
                <li>Четыре стратегии поставок</li>
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
        <p><span class="step-number">3</span> <span class="step-text">Нажмите <b>«Настройки»</b> (⚙️) для выбора параметров симуляции</span></p>
        <p><span class="step-number">4</span> <span class="step-text">Выберите стратегию поставок и настройте параметры</span></p>
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
