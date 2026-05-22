import streamlit as st
import pandas as pd
import sqlite3
from database.db_manager import DatabaseManager

def show():
    """Страница управления базой данных"""
    
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    db = st.session_state.db_manager
    
    # Инициализация состояния для форм
    if 'show_add_form' not in st.session_state:
        st.session_state.show_add_form = False
    if 'show_edit_form' not in st.session_state:
        st.session_state.show_edit_form = False
    if 'editing_product' not in st.session_state:
        st.session_state.editing_product = None
    
    st.title("🗄️ Управление базой данных")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📦 Товары", "📊 История экспериментов"])
    
    # ========== ТОВАРЫ ==========
    with tab1:
        st.subheader("📋 Список товаров")
        
        # Кнопка добавления товара
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("➕ Добавить", type="primary", use_container_width=True):
                st.session_state.show_add_form = True
                st.session_state.show_edit_form = False
        
        # Форма добавления товара
        if st.session_state.show_add_form:
            with st.expander("➕ Добавление нового товара", expanded=True):
                with st.form("add_product_form"):
                    name = st.text_input("Название товара", placeholder="Например: Помидоры, Молоко, Бананы...")
                    
                    cat_ru = st.selectbox(
                        "Категория", 
                        options=["strict", "gradual"],
                        format_func=lambda x: "🥛 Строгий срок (молоко, йогурт...)" if x == "strict" else "🍅 Постепенная порча (овощи, фрукты...)"
                    )
                    cat_id = 1 if cat_ru == "strict" else 2
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        purchase = st.number_input(
                            "💰 Цена закупки (руб)", 
                            min_value=0.0, 
                            value=None,
                            step=10.0,
                            placeholder="Например: 220"
                        )
                    with col2:
                        sale = st.number_input(
                            "💰 Цена продажи (руб)", 
                            min_value=0.0, 
                            value=None,
                            step=10.0,
                            placeholder="Например: 295"
                        )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        shelf = st.number_input(
                            "📅 Срок годности (дней)", 
                            min_value=1, 
                            value=None,
                            step=1,
                            placeholder="Например: 30"
                        )
                    with col2:
                        base_demand = st.number_input(
                            "📊 Базовый дневной спрос (ед/день)", 
                            min_value=1.0, 
                            value=None,
                            step=10.0,
                            placeholder="Например: 175"
                        )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True)
                    with col2:
                        if st.form_submit_button("❌ Отмена", use_container_width=True):
                            st.session_state.show_add_form = False
                            st.rerun()
                    
                    if submitted:
                        errors = []
                        if not name:
                            errors.append("Введите название товара")
                        if purchase is None or purchase <= 0:
                            errors.append("Введите корректную цену закупки (>0)")
                        if sale is None or sale <= 0:
                            errors.append("Введите корректную цену продажи (>0)")
                        if shelf is None or shelf <= 0:
                            errors.append("Введите корректный срок годности (>0)")
                        if base_demand is None or base_demand <= 0:
                            errors.append("Введите корректный базовый спрос (>0)")
                        
                        if errors:
                            for error in errors:
                                st.error(error)
                        else:
                            db.add_product(name, cat_id, purchase, sale, shelf, base_demand)
                            st.success(f"✅ Товар '{name}' добавлен!")
                            st.session_state.show_add_form = False
                            st.rerun()
        
        # Форма редактирования товара
        if st.session_state.show_edit_form and st.session_state.editing_product:
            product = st.session_state.editing_product
            with st.expander(f"✏️ Редактирование товара: {product['name']}", expanded=True):
                with st.form("edit_product_form"):
                    name = st.text_input("Название товара", value=product['name'])
                    
                    current_cat = "strict" if product['category'] == "strict" else "gradual"
                    cat_ru = st.selectbox(
                        "Категория", 
                        options=["strict", "gradual"],
                        format_func=lambda x: "🥛 Строгий срок (молоко, йогурт...)" if x == "strict" else "🍅 Постепенная порча (овощи, фрукты...)",
                        index=0 if current_cat == "strict" else 1
                    )
                    cat_id = 1 if cat_ru == "strict" else 2
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        purchase = st.number_input(
                            "💰 Цена закупки (руб)", 
                            min_value=0.0, 
                            value=product['purchase_price'],
                            step=10.0
                        )
                    with col2:
                        sale = st.number_input(
                            "💰 Цена продажи (руб)", 
                            min_value=0.0, 
                            value=product['sale_price'],
                            step=10.0
                        )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        shelf = st.number_input(
                            "📅 Срок годности (дней)", 
                            min_value=1, 
                            value=int(product['shelf_life_days']),
                            step=1
                        )
                    with col2:
                        base_demand = st.number_input(
                            "📊 Базовый дневной спрос (ед/день)", 
                            min_value=1.0, 
                            value=product['base_demand'],
                            step=10.0
                        )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        submitted = st.form_submit_button("💾 Сохранить изменения", type="primary", use_container_width=True)
                    with col2:
                        if st.form_submit_button("❌ Отмена", use_container_width=True):
                            st.session_state.show_edit_form = False
                            st.session_state.editing_product = None
                            st.rerun()
                    
                    if submitted:
                        db.update_product(
                            product['id_product'],
                            name=name,
                            id_category=cat_id,
                            purchase_price=purchase,
                            sale_price=sale,
                            shelf_life_days=shelf,
                            base_demand=base_demand
                        )
                        st.success(f"✅ Товар '{name}' обновлён!")
                        st.session_state.show_edit_form = False
                        st.session_state.editing_product = None
                        st.rerun()
        
        # Таблица товаров с кнопками действий
        products_df = db.get_all_products()
        
        if not products_df.empty:
            # Подготавливаем данные для отображения
            display_df = products_df.copy()
            display_df = display_df.rename(columns={
                'id_product': 'ID',
                'name': 'Название',
                'category': 'Категория',
                'purchase_price': 'Цена закупки',
                'sale_price': 'Цена продажи',
                'shelf_life_days': 'Срок годности',
                'base_demand': 'Базовый спрос'
            })
            
            # Переводим категории
            display_df['Категория'] = display_df['Категория'].map({
                'strict': '🥛 Строгий срок',
                'gradual': '🍅 Постепенная порча'
            })
            
            # Форматируем цены
            display_df['Цена закупки'] = display_df['Цена закупки'].apply(lambda x: f"{x:.2f} руб")
            display_df['Цена продажи'] = display_df['Цена продажи'].apply(lambda x: f"{x:.2f} руб")
            display_df['Срок годности'] = display_df['Срок годности'].apply(lambda x: f"{x} дн")
            display_df['Базовый спрос'] = display_df['Базовый спрос'].apply(lambda x: f"{x:.0f} ед/день")
            
            # Отображаем таблицу без колонки ID
            display_cols = ['Название', 'Категория', 'Цена закупки', 'Цена продажи', 'Срок годности', 'Базовый спрос']
            st.dataframe(display_df[display_cols], use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔧 Управление товарами")
            
            # Выбор товара для редактирования/удаления
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                selected_product_name = st.selectbox(
                    "Выберите товар для управления",
                    options=products_df['name'].tolist(),
                    key="manage_product"
                )
            
            selected_product = products_df[products_df['name'] == selected_product_name].iloc[0]
            
            with col2:
                if st.button("✏️ Редактировать", use_container_width=True):
                    st.session_state.editing_product = {
                        'id_product': selected_product['id_product'],
                        'name': selected_product['name'],
                        'category': selected_product['category'],
                        'purchase_price': selected_product['purchase_price'],
                        'sale_price': selected_product['sale_price'],
                        'shelf_life_days': selected_product['shelf_life_days'],
                        'base_demand': selected_product['base_demand']
                    }
                    st.session_state.show_edit_form = True
                    st.session_state.show_add_form = False
                    st.rerun()
            
            with col3:
                if st.button("🗑️ Удалить", type="secondary", use_container_width=True):
                    if st.session_state.get('confirm_delete', False):
                        db.delete_product(selected_product['id_product'])
                        st.success(f"✅ Товар '{selected_product_name}' удалён!")
                        st.session_state.confirm_delete = False
                        st.rerun()
                    else:
                        st.session_state.confirm_delete = True
                        st.warning(f"⚠️ Нажмите ещё раз для подтверждения удаления товара '{selected_product_name}'")
        else:
            st.info("📭 Нет товаров в базе данных. Нажмите «➕ Добавить», чтобы добавить первый товар.")
    
    # ========== ИСТОРИЯ ЭКСПЕРИМЕНТОВ ==========
    with tab2:
        st.subheader("📊 Сохранённые симуляции")
        
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🗑️ Очистить всё", type="secondary", use_container_width=True):
                if st.session_state.get('confirm_clear', False):
                    with sqlite3.connect("database/perishable.db") as conn:
                        conn.execute("DELETE FROM experiments")
                        conn.execute("DELETE FROM sqlite_sequence WHERE name='experiments'")
                    st.success("✅ Все эксперименты удалены!")
                    st.session_state.confirm_clear = False
                    st.rerun()
                else:
                    st.session_state.confirm_clear = True
                    st.warning("⚠️ Нажмите ещё раз для подтверждения удаления ВСЕХ экспериментов")
        
        exp_df = db.get_all_experiments()
        if not exp_df.empty:
            # Переименовываем колонки на русский язык
            exp_df_display = exp_df.rename(columns={
                'id_experiment': 'ID',
                'product_name': 'Товар',
                'distribution': 'Распределение',
                'days': 'Дни',
                'fifo_percent': 'FIFO %',
                'min_stock': 'Мин. запас',
                'purchase_price': 'Цена закупки',
                'sale_price': 'Цена продажи',
                'shelf_life_days': 'Срок годности',
                'spoilage_type': 'Тип порчи',
                'delivery_type': 'Тип поставок',
                'delivery_frequency': 'Периодичность',
                'delivery_days': 'Дни поставок',
                'packing_type': 'Тип упаковки',
                'box_size': 'Размер упаковки',
                'total_revenue': 'Выручка',
                'total_cost': 'Затраты',
                'total_spoilage_kg': 'Потери (кг)',
                'total_spoilage_money': 'Потери (руб)',
                'profit': 'Прибыль',
                'total_unmet_demand': 'Неудовлетворённый спрос',
                'avg_stock': 'Ср. остаток'
            })
            
            # Преобразуем значения для читаемости
            if 'Тип поставок' in exp_df_display.columns:
                exp_df_display['Тип поставок'] = exp_df_display['Тип поставок'].map({
                    'periodic': 'Периодические',
                    'days_of_week': 'По дням недели'
                })
            if 'Тип упаковки' in exp_df_display.columns:
                exp_df_display['Тип упаковки'] = exp_df_display['Тип упаковки'].map({
                    'unit': 'Штучно',
                    'box': 'Коробками/ящиками'
                })
            if 'Распределение' in exp_df_display.columns:
                exp_df_display['Распределение'] = exp_df_display['Распределение'].map({
                    'uniform': 'Равномерный',
                    'normal': 'Нормальный'
                })
            if 'Тип порчи' in exp_df_display.columns:
                exp_df_display['Тип порчи'] = exp_df_display['Тип порчи'].map({
                    'strict': 'Строгая',
                    'linear': 'Линейная',
                    'exponential': 'Экспоненциальная'
                })
            
            # Сортируем по ID в обратном порядке
            exp_df_display = exp_df_display.sort_values('ID', ascending=False)
            
            st.dataframe(exp_df_display, use_container_width=True, height=400)
            st.caption(f"📊 Всего экспериментов: {len(exp_df_display)}")
            
            # Экспорт
            csv = exp_df_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Экспорт всех экспериментов в CSV",
                data=csv,
                file_name="experiments_export.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("📭 Нет сохранённых экспериментов. После симуляции нажмите «Сохранить результат».")
