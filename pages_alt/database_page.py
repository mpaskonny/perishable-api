import streamlit as st
import pandas as pd
import sqlite3
from database.db_manager import DatabaseManager

def show():
    """Страница управления базой данных"""
    
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    db = st.session_state.db_manager

    tab1, tab2 = st.tabs(["📦 Товары", "📊 История экспериментов"])
    
    # ========== ТОВАРЫ ==========
    with tab1:
        st.subheader("📋 Список товаров")
        products_df = db.get_all_products()
        
        if not products_df.empty:
            # Переименовываем колонки на русский язык
            display_df = products_df.rename(columns={
                'id_product': 'ID',
                'name': 'Название',
                'category': 'Категория',
                'purchase_price': 'Цена закупки (руб)',
                'sale_price': 'Цена продажи (руб)',
                'shelf_life_days': 'Срок годности (дн)',
                'base_demand': 'Базовый спрос (ед/день)'
            })
            # Переводим категории
            display_df['Категория'] = display_df['Категория'].map({
                'strict': '🥛 Строгий срок (молоко)',
                'gradual': '🍅 Постепенная порча (овощи/фрукты)'
            })
            st.dataframe(display_df, use_container_width=True)
            
            # Удаление товара
            st.markdown("---")
            st.subheader("🗑️ Удалить товар")
            col1, col2 = st.columns([3, 1])
            with col1:
                product_to_delete = st.selectbox("Выберите товар для удаления", products_df['name'].tolist())
            with col2:
                if st.button("🗑️ Удалить", type="secondary"):
                    product_id = db.get_product_id_by_name(product_to_delete)
                    db.delete_product(product_id)
                    st.rerun()
        
        # Добавление товара
        st.markdown("---")
        st.subheader("➕ Добавить новый товар")
        
        with st.form("add_product_form"):
            name = st.text_input("Название товара", placeholder="Например: Помидоры, Молоко, Бананы...")
            
            # Категория на русском языке
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
            
            # Валидация перед сохранением
            submitted = st.form_submit_button("💾 Сохранить товар", use_container_width=True)
            
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
                    st.rerun()
    
    # ========== ИСТОРИЯ ЭКСПЕРИМЕНТОВ ==========
    with tab2:
        st.subheader("📊 Сохранённые симуляции")
        
        if st.button("🗑️ Очистить всё", type="secondary"):
            with sqlite3.connect("database/perishable.db") as conn:
                conn.execute("DELETE FROM experiments")
                conn.execute("DELETE FROM sqlite_sequence WHERE name='experiments'")
            st.rerun()
        
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
            
            st.dataframe(exp_df_display, use_container_width=True)
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
            st.info("📭 Нет сохранённых экспериментов")
