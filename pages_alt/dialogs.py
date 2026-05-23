import streamlit as st
import sqlite3
from database.db_manager import DatabaseManager

@st.dialog("➕ Добавление нового товара", width="large")
def add_product_modal():
    db = DatabaseManager()
    
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
            purchase = st.number_input("💰 Цена закупки (руб)", min_value=0.0, value=None, step=10.0, placeholder="220")
        with col2:
            sale = st.number_input("💰 Цена продажи (руб)", min_value=0.0, value=None, step=10.0, placeholder="295")
        
        col1, col2 = st.columns(2)
        with col1:
            shelf = st.number_input("📅 Срок годности (дней)", min_value=1, value=None, step=1, placeholder="30")
        with col2:
            base_demand = st.number_input("📊 Базовый спрос (ед/день)", min_value=1.0, value=None, step=10.0, placeholder="35")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True)
        with col2:
            if st.form_submit_button("❌ Отмена", use_container_width=True):
                st.session_state.show_add_modal = False
                st.rerun()
        
        if submitted:
            errors = []
            if not name:
                errors.append("Введите название товара")
            if purchase is None or purchase <= 0:
                errors.append("Введите цену закупки (>0)")
            if sale is None or sale <= 0:
                errors.append("Введите цену продажи (>0)")
            if shelf is None or shelf <= 0:
                errors.append("Введите срок годности (>0)")
            if base_demand is None or base_demand <= 0:
                errors.append("Введите базовый спрос (>0)")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                db.add_product(name, cat_id, purchase, sale, shelf, base_demand)
                st.success(f"✅ Товар '{name}' добавлен!")
                st.session_state.show_add_modal = False
                st.rerun()


@st.dialog("✏️ Редактирование товара", width="large")
def edit_product_modal():
    db = DatabaseManager()
    product = st.session_state.editing_product
    
    if product is None:
        st.error("Ошибка: товар не выбран")
        return
    
    with st.form("edit_product_form"):
        name = st.text_input("Название товара", value=product['name'])
        
        current_cat = "strict" if product['category'] == "strict" else "gradual"
        cat_ru = st.selectbox(
            "Категория", 
            options=["strict", "gradual"],
            format_func=lambda x: "🥛 Строгий срок" if x == "strict" else "🍅 Постепенная порча",
            index=0 if current_cat == "strict" else 1
        )
        cat_id = 1 if cat_ru == "strict" else 2
        
        col1, col2 = st.columns(2)
        with col1:
            purchase = st.number_input("💰 Цена закупки (руб)", min_value=0.0, value=product['purchase_price'], step=10.0)
        with col2:
            sale = st.number_input("💰 Цена продажи (руб)", min_value=0.0, value=product['sale_price'], step=10.0)
        
        col1, col2 = st.columns(2)
        with col1:
            shelf = st.number_input("📅 Срок годности (дней)", min_value=1, value=int(product['shelf_life_days']), step=1)
        with col2:
            base_demand = st.number_input("📊 Базовый спрос (ед/день)", min_value=1.0, value=product['base_demand'], step=10.0)
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("💾 Сохранить", type="primary", use_container_width=True)
        with col2:
            if st.form_submit_button("❌ Отмена", use_container_width=True):
                st.session_state.show_edit_modal = False
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
            st.session_state.show_edit_modal = False
            st.session_state.editing_product = None
            st.rerun()


@st.dialog("🗑️ Подтверждение удаления", width="small")
def delete_product_modal():
    db = DatabaseManager()
    product_name = st.session_state.delete_product_name
    product_id = st.session_state.delete_product_id
    
    st.warning(f"⚠️ Вы действительно хотите удалить товар **«{product_name}»**?")
    st.caption("Это действие невозможно отменить. Все связанные эксперименты также будут удалены.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Да, удалить", type="secondary", use_container_width=True):
            db.delete_product(product_id)
            st.success(f"✅ Товар '{product_name}' удалён!")
            st.session_state.show_delete_modal = False
            st.session_state.delete_product_name = None
            st.session_state.delete_product_id = None
            st.rerun()
    with col2:
        if st.button("❌ Отмена", type="primary", use_container_width=True):
            st.session_state.show_delete_modal = False
            st.session_state.delete_product_name = None
            st.session_state.delete_product_id = None
            st.rerun()


@st.dialog("🗑️ Подтверждение очистки", width="small")
def clear_experiments_modal():
    st.warning("⚠️ Вы действительно хотите удалить **ВСЕ** сохранённые эксперименты?")
    st.caption("Это действие невозможно отменить.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Да, очистить всё", type="secondary", use_container_width=True):
            with sqlite3.connect("database/perishable.db") as conn:
                conn.execute("DELETE FROM experiments")
                conn.execute("DELETE FROM sqlite_sequence WHERE name='experiments'")
            st.success("✅ Все эксперименты удалены!")
            st.session_state.show_clear_modal = False
            st.rerun()
    with col2:
        if st.button("❌ Отмена", type="primary", use_container_width=True):
            st.session_state.show_clear_modal = False
            st.rerun()
