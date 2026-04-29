import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from sidebar_config import setup_sidebar

st.query_params["page"] = "database"

# Фикс ширины страницы через JavaScript
st.markdown("""
    <script>
        function fixWidth() {
            const container = document.querySelector('.main .block-container');
            if (container) {
                container.style.maxWidth = '100%';
                container.style.paddingLeft = '2rem';
                container.style.paddingRight = '2rem';
            }
            const sidebar = document.querySelector('section[data-testid="stSidebar"]');
            if (sidebar) {
                sidebar.style.width = '280px';
            }
        }
        setTimeout(fixWidth, 100);
        setTimeout(fixWidth, 300);
        setTimeout(fixWidth, 600);
    </script>
""", unsafe_allow_html=True)

with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


setup_sidebar()

st.title("🗄️ Управление базой данных")
st.markdown("---")

if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager()
db = st.session_state.db_manager

tab1, tab2, tab3 = st.tabs(["📦 Товары", "🥀 Параметры порчи", "📊 История экспериментов"])

# --------------------------------------------------
# ТОВАРЫ
with tab1:
    st.subheader("Список товаров")
    products_df = db.get_all_products()
    if not products_df.empty:
        display_df = products_df.rename(columns={
            'id_product': 'ID',
            'name': 'Название',
            'category': 'Категория',
            'purchase_price': 'Цена закупки (руб)',
            'sale_price': 'Цена продажи (руб)',
            'shelf_life_days': 'Срок годности (дн)'
        })
        display_df['Категория'] = display_df['Категория'].map({
            'strict': 'Строгий срок',
            'gradual': 'Постепенная порча'
        })
        st.dataframe(display_df, use_container_width=True)

    with st.expander("➕ Добавить новый товар"):
        name = st.text_input("Название товара", key="add_name")
        cat = st.selectbox("Категория", ["strict", "gradual"], 
                          format_func=lambda x: "Строгий срок" if x == "strict" else "Постепенная порча",
                          key="add_category")
        purchase = st.number_input("Цена закупки (руб)", min_value=0.0, step=10.0, key="add_purchase")
        sale = st.number_input("Цена продажи (руб)", min_value=0.0, step=10.0, key="add_sale")
        shelf = st.number_input("Срок годности (дней)", min_value=1, value=10, step=1, key="add_shelf") if cat == "strict" else None
        if st.button("💾 Сохранить товар", key="save_product"):
            cat_id = 1 if cat == "strict" else 2
            db.add_product(name, cat_id, purchase, sale, shelf)
            st.rerun()

    if not products_df.empty:
        with st.expander("✏️ Редактировать / удалить товар"):
            selected = st.selectbox("Выберите товар", products_df['name'].tolist(), key="edit_select")
            prod = db.get_product_by_name(selected)
            if prod:
                new_name = st.text_input("Название", prod['name'], key="edit_name")
                new_pur = st.number_input("Цена закупки", value=prod['purchase_price'], step=10.0, key="edit_purchase")
                new_sale = st.number_input("Цена продажи", value=prod['sale_price'], step=10.0, key="edit_sale")
                new_shelf = st.number_input("Срок годности (дней)", value=prod['shelf_life_days'] or 10, step=1, key="edit_shelf") if prod['id_category'] == 1 else None
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Сохранить изменения", key="update_product"):
                        db.update_product(prod['id_product'], name=new_name, purchase_price=new_pur, sale_price=new_sale, shelf_life_days=new_shelf)
                        st.rerun()
                with col2:
                    if st.button("🗑️ Удалить товар", key="delete_product"):
                        db.delete_product(prod['id_product'])
                        st.rerun()

# --------------------------------------------------
# ПАРАМЕТРЫ ПОРЧИ
with tab2:
    st.subheader("Параметры порчи по неделям")
    products_df = db.get_all_products()
    gradual = products_df[products_df['category'] == 'gradual']
    if not gradual.empty:
        selected = st.selectbox("Выберите товар", gradual['name'].tolist(), key="spoilage_product")
        pid = db.get_product_id_by_name(selected)
        rates = db.get_spoilage_rates(pid)
        if not rates.empty:
            st.dataframe(rates.rename(columns={'week_number': 'Неделя', 'rate': 'Процент порчи (%)'}))

        with st.expander("➕ Добавить / изменить параметр порчи"):
            week = st.number_input("Номер недели", min_value=1, max_value=10, step=1, key="add_week")
            rate = st.number_input("Процент порчи (%)", min_value=0.0, max_value=100.0, step=5.0, key="add_rate")
            if st.button("💾 Сохранить", key="save_spoilage"):
                db.add_spoilage_rate(pid, week, rate)
                st.rerun()

        with st.expander("🗑️ Удалить параметр порчи"):
            week_del = st.number_input("Номер недели для удаления", min_value=1, max_value=10, step=1, key="del_week")
            if st.button("🗑️ Удалить", key="delete_spoilage"):
                db.delete_spoilage_rate(pid, week_del)
                st.rerun()
    else:
        st.info("Нет товаров с категорией «gradual»")

# --------------------------------------------------
# ИСТОРИЯ ЭКСПЕРИМЕНТОВ
with tab3:
    st.subheader("Сохранённые симуляции")
    exp_df = db.get_all_experiments()
    if not exp_df.empty:
        st.dataframe(exp_df.drop(columns=['id_experiment'], errors='ignore'), use_container_width=True)
    else:
        st.info("Нет сохранённых экспериментов. После симуляции нажмите «Сохранить результат».")
