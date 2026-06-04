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
        'min_stock': 300,
        'utilization_price': 5.0, 
        'sim_start_date': '2026-02-01',
        'sim_end_date': '2026-03-03'
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
        # ========== ДОБАВИТЬ ПОСЛЕ БЛОКА УТИЛИЗАЦИИ ==========
        st.markdown("---")
        st.subheader("🔄 Усреднение результатов")
        
        num_simulations = st.number_input(
            "Количество симуляций для усреднения",
            min_value=1,
            max_value=50,
            value=st.session_state.settings.get('num_simulations', 1),
            step=1,
            key="dialog_num_simulations",
            help="Прогон нескольких симуляций с разными случайными значениями и усреднение результатов"
        )
        # ====================================================
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

        # ========== ДОБАВИТЬ ЭТОТ БЛОК ==========
        st.markdown("---")
        st.subheader("🗑️ Утилизация просроченного товара")
        
        utilization_price = st.number_input(
            "Стоимость утилизации (руб/кг или руб/шт)",
            min_value=0.0,
            value=st.session_state.settings.get('utilization_price', 5.0),
            step=1.0,
            key="dialog_utilization_price",
            help="Затраты на утилизацию единицы просроченного товара. Для товаров с постепенной порчей можно оставить 0."
        )
        # =====================================

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
        # Загружаем сохранённые значения (с защитой от 0 для box_size)
        saved_strategy_type = st.session_state.settings.get('strategy_type', 'r_s')
        saved_delivery_type = st.session_state.settings.get('delivery_type', 'unit')
        box_size_val = st.session_state.settings.get('box_size', 20)
        saved_box_size = max(1, int(box_size_val) if box_size_val is not None else 20)
        delivery_freq_val = st.session_state.settings.get('delivery_frequency', 2)
        saved_delivery_frequency = int(delivery_freq_val) if delivery_freq_val is not None and int(delivery_freq_val) >= 1 else 2
        fixed_q_val = st.session_state.settings.get('fixed_quantity', 100)
        saved_fixed_quantity = float(fixed_q_val) if fixed_q_val is not None else 100.0
        reorder_val = st.session_state.settings.get('reorder_point', 100)
        saved_reorder_point = float(reorder_val) if reorder_val is not None else 100.0
        max_stock_val = st.session_state.settings.get('max_stock', 300)
        saved_max_stock = float(max_stock_val) if max_stock_val is not None else 300.0
        min_stock_val = st.session_state.settings.get('min_stock', 300)
        saved_min_stock = float(min_stock_val) if min_stock_val is not None else 300.0
        saved_schedule_type = st.session_state.settings.get('schedule_type', 'frequency')
        saved_delivery_days = st.session_state.settings.get('delivery_days', [0, 3])
        
        st.markdown("### 🎯 Выберите стратегию")
        
        strategy_type = st.radio(
            "Стратегия",
            options=["r_s", "r_q", "s_s", "s_q", "custom"],
            format_func=lambda x: {
                "r_s": "📅 (R, S) — Периодическая до целевого уровня",
                "r_q": "📦 (R, Q) — Фиксированный объём по расписанию",
                "s_s": "📊 (s, S) — Двухуровневая (точка заказа)",
                "s_q": "🎯 (s, Q) — Двухуровневая с фиксированным объёмом",
                "custom": "🔧 Пользовательская (конструктор)"
            }[x],
            index=["r_s", "r_q", "s_s", "s_q", "custom"].index(saved_strategy_type),
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
                index=0 if saved_delivery_type == "unit" else 1,
                key="dialog_r_s_delivery_type"
            )
            
            box_size = 0
            if delivery_type == "box":
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=max(1, saved_box_size), step=1, key="dialog_r_s_box_size")
            
            st.subheader("📅 Расписание поставок")
            schedule_type = st.radio(
                "Тип расписания",
                options=["frequency", "days"],
                format_func=lambda x: "Периодичность (каждые N дней)" if x == "frequency" else "Конкретные дни недели",
                horizontal=True,
                index=0 if saved_schedule_type == "frequency" else 1,
                key="dialog_r_s_schedule"
            )
            
            if schedule_type == "frequency":
                delivery_frequency = st.number_input("Периодичность (дней)", min_value=1, value=max(1, saved_delivery_frequency), step=1, key="dialog_r_s_freq")
                delivery_days = []
            else:
                delivery_frequency = 0
                day_map = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
                default_days = [k for k, v in day_map.items() if v in saved_delivery_days]
                selected_days = st.multiselect("Дни поставок", ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"], default=default_days, key="dialog_r_s_days")
                delivery_days = [day_map[d] for d in selected_days]
            
            min_stock = st.number_input("📦 Целевой уровень запаса", min_value=0.0, value=saved_min_stock, step=50.0, key="dialog_r_s_min_stock")
            
            fixed_quantity = None
            reorder_point = None
            max_stock = None
        
        # ===== (R, Q) =====
        elif strategy_type == "r_q":
            fixed_quantity = st.number_input("📦 Фиксированный объём поставки (шт/кг)", min_value=1.0, value=saved_fixed_quantity, step=10.0, key="dialog_r_q_fixed")
            
            st.subheader("📅 Расписание поставок")
            schedule_type = st.radio(
                "Тип расписания",
                options=["frequency", "days"],
                format_func=lambda x: "Периодичность (каждые N дней)" if x == "frequency" else "Конкретные дни недели",
                horizontal=True,
                index=0 if saved_schedule_type == "frequency" else 1,
                key="dialog_r_q_schedule"
            )
            
            if schedule_type == "frequency":
                delivery_frequency = st.number_input("Периодичность (дней)", min_value=1, value=max(1, saved_delivery_frequency), step=1, key="dialog_r_q_freq")
                delivery_days = []
            else:
                delivery_frequency = 0
                day_map = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
                default_days = [k for k, v in day_map.items() if v in saved_delivery_days]
                selected_days = st.multiselect("Дни поставок", ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"], default=default_days, key="dialog_r_q_days")
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
                index=0 if saved_delivery_type == "unit" else 1,
                key="dialog_s_s_delivery_type"
            )
            
            box_size = 0
            if delivery_type == "box":
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=max(1, saved_box_size), step=1, key="dialog_s_s_box_size")
            
            col1, col2 = st.columns(2)
            with col1:
                reorder_point = st.number_input("📉 Точка заказа (s)", min_value=0.0, value=saved_reorder_point, step=10.0, key="dialog_s_s_reorder")
            with col2:
                max_stock = st.number_input("📈 Максимальный запас (S)", min_value=0.0, value=saved_max_stock, step=50.0, key="dialog_s_s_max")
            
            st.caption("⚡ Поставка происходит при остатке ниже s, независимо от расписания")
            
            fixed_quantity = None
            delivery_frequency = 0
            delivery_days = []
            min_stock = max_stock
        
        # ===== (s, Q) =====
        elif strategy_type == "s_q":
            delivery_type = st.radio(
                "Способ поставки",
                options=["unit", "box"],
                format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками/ящиками",
                horizontal=True,
                index=0 if saved_delivery_type == "unit" else 1,
                key="dialog_s_q_delivery_type"
            )
            
            box_size = 0
            if delivery_type == "box":
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=max(1, saved_box_size), step=1, key="dialog_s_q_box_size")
            
            col1, col2 = st.columns(2)
            with col1:
                reorder_point = st.number_input(
                    "📉 Точка заказа (s)", 
                    min_value=0.0, 
                    value=saved_reorder_point, 
                    step=10.0, 
                    key="dialog_s_q_reorder",
                    help="При остатке ниже этого уровня делается заказ"
                )
            with col2:
                fixed_quantity = st.number_input(
                    "📦 Фиксированный объём заказа (Q)", 
                    min_value=1.0, 
                    value=saved_fixed_quantity, 
                    step=10.0, 
                    key="dialog_s_q_fixed",
                    help="Заказывается всегда одно и то же количество"
                )
            
            st.caption("⚡ Поставка происходит при остатке ниже s, заказывается фиксированное количество Q")
            
            delivery_frequency = 0
            delivery_days = []
            schedule_type = None
            min_stock = 0
            max_stock = None

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
                    index=0 if saved_schedule_type == "frequency" else 1,
                    key="dialog_custom_schedule"
                )
                
                if schedule_type == "frequency":
                    delivery_frequency = st.number_input("Периодичность (дней)", min_value=1, value=max(1, saved_delivery_frequency), step=1, key="dialog_custom_freq")
                    delivery_days = []
                else:
                    delivery_frequency = 0
                    day_map = {"Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3, "Пт": 4, "Сб": 5, "Вс": 6}
                    default_days = [k for k, v in day_map.items() if v in saved_delivery_days]
                    selected_days = st.multiselect("Дни поставок", ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"], default=default_days, key="dialog_custom_days")
                    delivery_days = [day_map[d] for d in selected_days]
                
                reorder_point = None
            else:
                delivery_frequency = 0
                delivery_days = []
                reorder_point = st.number_input("📉 Точка заказа (s)", min_value=0.0, value=saved_reorder_point, step=10.0, key="dialog_custom_reorder")
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
                max_stock = st.number_input("📈 Максимальный запас (S)", min_value=0.0, value=saved_max_stock, step=50.0, key="dialog_custom_max")
                fixed_quantity = None
                min_stock = max_stock
            else:
                fixed_quantity = st.number_input("📦 Фиксированный объём Q", min_value=1.0, value=saved_fixed_quantity, step=10.0, key="dialog_custom_fixed")
                max_stock = None
                min_stock = 0
            
            delivery_type = st.radio(
                "Способ поставки (для штучных заказов)",
                options=["unit", "box"],
                format_func=lambda x: "📦 Штучно" if x == "unit" else "📦 Коробками/ящиками",
                horizontal=True,
                index=0 if saved_delivery_type == "unit" else 1,
                key="dialog_custom_delivery"
            )
            
            box_size = 0
            if delivery_type == "box":
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=max(1, saved_box_size), step=1, key="dialog_custom_box_size")
    
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
                final_min_stock = float(min_stock)
            elif strategy_type == "r_q":
                final_delivery_type = "fixed"
                final_box_size = 0
                final_fixed_quantity = float(fixed_quantity)
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
                final_reorder_point = float(reorder_point)
                final_max_stock = float(max_stock)
                final_min_stock = float(max_stock)
            elif strategy_type == "s_q":
                final_delivery_type = delivery_type
                final_box_size = box_size
                final_fixed_quantity = float(fixed_quantity)
                final_delivery_frequency = 0
                final_delivery_days = []
                final_schedule_type = None
                final_reorder_point = float(reorder_point)
                final_max_stock = None
                final_min_stock = 0
            else:  # custom
                final_delivery_type = delivery_type
                final_box_size = box_size
                final_fixed_quantity = float(fixed_quantity) if fixed_quantity is not None else None
                final_delivery_frequency = delivery_frequency if 'delivery_frequency' in dir() and delivery_frequency is not None else 0
                final_delivery_days = delivery_days if 'delivery_days' in dir() else []
                final_schedule_type = schedule_type if 'schedule_type' in dir() else None
                final_reorder_point = float(reorder_point) if reorder_point is not None else None
                final_max_stock = float(max_stock) if max_stock is not None else None
                final_min_stock = float(min_stock) if 'min_stock' in dir() and min_stock is not None else 0
            
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
                'num_simulations': num_simulations,
                # Утилизация
                'utilization_price': utilization_price,
                # Даты симуляции
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
    st.markdown('<div class="simulation-title">🎮 Симуляция управления запасами</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    from pages_alt import simulation_page
    simulation_page.show(settings_dialog)


# ========== ВКЛАДКА 3: БАЗА ДАННЫХ ==========
with tab3:
    st.markdown('<div class="simulation-title">🗄️ Управление базой данных</div>', unsafe_allow_html=True)
    st.markdown("---")

    from pages_alt import database_page
    database_page.show()


# ========== ВКЛАДКА 4: ПОМОЩЬ ==========
with tab4:
    st.markdown('<div class="simulation-title">📖 Руководство пользователя</div>', unsafe_allow_html=True)
    st.markdown("---")

    from pages_alt.help_page import show as help_page_show
    help_page_show()
