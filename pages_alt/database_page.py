import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from pages_alt.dialogs import (
    add_product_modal,
    edit_product_modal,
    delete_product_modal,
    clear_experiments_modal
)


def show():
    """Страница управления базой данных"""
    
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    db = st.session_state.db_manager
    
    # Инициализация состояния для модальных окон
    if 'show_add_modal' not in st.session_state:
        st.session_state.show_add_modal = False
    if 'show_edit_modal' not in st.session_state:
        st.session_state.show_edit_modal = False
    if 'show_delete_modal' not in st.session_state:
        st.session_state.show_delete_modal = False
    if 'show_clear_modal' not in st.session_state:
        st.session_state.show_clear_modal = False
    if 'editing_product' not in st.session_state:
        st.session_state.editing_product = None
    if 'delete_product_name' not in st.session_state:
        st.session_state.delete_product_name = None
    if 'delete_product_id' not in st.session_state:
        st.session_state.delete_product_id = None
    
    st.title("🗄️ Управление базой данных")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📦 Товары", "📊 История экспериментов"])
    
    # ========== ТОВАРЫ ==========
    with tab1:
        st.subheader("📋 Список товаров")
        
        # Кнопка добавления
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("➕ Добавить товар", type="primary", use_container_width=True):
                st.session_state.show_edit_modal = False
                st.session_state.show_delete_modal = False
                st.session_state.show_clear_modal = False
                st.session_state.show_add_modal = True
        
        # Получаем список товаров
        products_df = db.get_all_products()
        
        if not products_df.empty:
            # Заголовки таблицы
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([2, 1.5, 1.2, 1.2, 0.8, 1, 0.5, 0.5])
            with col1:
                st.write("**Название**")
            with col2:
                st.write("**Категория**")
            with col3:
                st.write("**Цена закупки**")
            with col4:
                st.write("**Цена продажи**")
            with col5:
                st.write("**Срок годности**")
            with col6:
                st.write("**Базовый спрос**")
            with col7:
                st.write("")
            with col8:
                st.write("")
            
            st.divider()
            
            # Строки товаров
            for idx, row in products_df.iterrows():
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([2, 1.5, 1.2, 1.2, 0.8, 1, 0.5, 0.5])
                
                with col1:
                    st.write(f"{row['name']}")
                with col2:
                    cat_name = "🥛 Строгий срок" if row['category'] == "strict" else "🍅 Постепенная порча"
                    st.write(cat_name)
                with col3:
                    st.write(f"{row['purchase_price']:.2f} руб")
                with col4:
                    st.write(f"{row['sale_price']:.2f} руб")
                with col5:
                    st.write(f"{row['shelf_life_days']} дн")
                with col6:
                    st.write(f"{row['base_demand']:.0f} ед/день")
                with col7:
                    if st.button("✏️", key=f"edit_{row['id_product']}", help="Редактировать"):
                        st.session_state.show_add_modal = False
                        st.session_state.show_delete_modal = False
                        st.session_state.show_clear_modal = False
                        st.session_state.editing_product = {
                            'id_product': row['id_product'],
                            'name': row['name'],
                            'category': row['category'],
                            'purchase_price': row['purchase_price'],
                            'sale_price': row['sale_price'],
                            'shelf_life_days': row['shelf_life_days'],
                            'base_demand': row['base_demand']
                        }
                        st.session_state.show_edit_modal = True
                with col8:
                    if st.button("🗑️", key=f"delete_{row['id_product']}", help="Удалить"):
                        st.session_state.show_add_modal = False
                        st.session_state.show_edit_modal = False
                        st.session_state.show_clear_modal = False
                        st.session_state.delete_product_name = row['name']
                        st.session_state.delete_product_id = row['id_product']
                        st.session_state.show_delete_modal = True
                
                st.divider()
        else:
            st.info("📭 Нет товаров в базе данных. Нажмите «➕ Добавить товар», чтобы добавить первый товар.")
    
    # ========== ИСТОРИЯ ЭКСПЕРИМЕНТОВ ==========
    with tab2:
        st.subheader("📊 Сохранённые симуляции")
        
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🗑️ Очистить всё", type="secondary", use_container_width=True):
                st.session_state.show_add_modal = False
                st.session_state.show_edit_modal = False
                st.session_state.show_delete_modal = False
                st.session_state.show_clear_modal = True
        
        exp_df = db.get_all_experiments()
        if not exp_df.empty:
            exp_df_display = exp_df.rename(columns={
                'id_experiment': 'ID',
                'product_name': 'Товар',
                'distribution': 'Распределение',
                'days': 'Дни',
                'profit': 'Прибыль',
                'avg_stock': 'Ср. остаток'
            })
            st.dataframe(exp_df_display[['ID', 'Товар', 'Распределение', 'Дни', 'Прибыль', 'Ср. остаток']], 
                        use_container_width=True)
            st.caption(f"📊 Всего экспериментов: {len(exp_df)}")
        else:
            st.info("📭 Нет сохранённых экспериментов")
    
    # ========== ВЫЗОВ МОДАЛЬНЫХ ОКОН ==========
    if st.session_state.get('show_add_modal', False):
        add_product_modal()
    elif st.session_state.get('show_edit_modal', False) and st.session_state.get('editing_product'):
        edit_product_modal()
    elif st.session_state.get('show_delete_modal', False):
        delete_product_modal()
    elif st.session_state.get('show_clear_modal', False):
        clear_experiments_modal()
