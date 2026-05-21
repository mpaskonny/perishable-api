import streamlit as st
import pandas as pd
import sqlite3
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

tab1, tab2 = st.tabs(["📦 Товары", "📊 История экспериментов"])

# ==================================================
# ТАБ 1: ТОВАРЫ
# ==================================================
with tab1:
    st.subheader("Список товаров")
    products_df = db.get_all_products()
    
    if not products_df.empty:
        # Отображаем таблицу товаров
        display_df = products_df.rename(columns={
            'id_product': 'ID',
            'name': 'Название',
            'category': 'Категория',
            'purchase_price': 'Цена закупки (руб)',
            'sale_price': 'Цена продажи (руб)',
            'shelf_life_days': 'Срок годности (дн)',
            'base_demand': 'Базовый спрос (ед/день)'
        })
        display_df['Категория'] = display_df['Категория'].map({
            'strict': 'Строгий срок (молоко)',
            'gradual': 'Постепенная порча (овощи/фрукты)'
        })
        st.dataframe(display_df, use_container_width=True)
        
        # Кнопка удаления товара
        st.markdown("---")
        st.subheader("🗑️ Удалить товар")
        col1, col2 = st.columns([3, 1])
        with col1:
            product_to_delete = st.selectbox(
                "Выберите товар для удаления",
                options=products_df['name'].tolist(),
                key="delete_product_select"
            )
        with col2:
            if st.button("🗑️ Удалить", type="secondary", key="delete_product_btn"):
                product_id = db.get_product_id_by_name(product_to_delete)
                if product_id:
                    db.delete_product(product_id)
                    st.success(f"✅ Товар '{product_to_delete}' удалён!")
                    st.rerun()
    
    else:
        st.info("📭 Нет товаров в базе данных. Добавьте первый товар ниже.")
    
    st.markdown("---")
    st.subheader("➕ Добавить новый товар")
    
    with st.form("add_product_form"):
        name = st.text_input("Название товара", key="add_name")
        
        cat = st.selectbox(
            "Категория", 
            ["strict", "gradual"], 
            format_func=lambda x: "🥛 Строгий срок (молоко, йогурт...)" if x == "strict" else "🍅 Постепенная порча (помидоры, бананы, лук...)",
            key="add_category"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            purchase = st.number_input("💰 Цена закупки (руб)", min_value=0.0, step=10.0, key="add_purchase")
        with col2:
            sale = st.number_input("💰 Цена продажи (руб)", min_value=0.0, step=10.0, key="add_sale")
        
        col1, col2 = st.columns(2)
        with col1:
            shelf = st.number_input("📅 Срок годности (дней)", min_value=1, value=30, step=1, key="add_shelf")
        with col2:
            base_demand = st.number_input(
                "📊 Базовый дневной спрос (ед/день)", 
                min_value=1.0, 
                value=100.0, 
                step=10.0, 
                key="add_demand",
                help="Средний спрос в день. В симуляции будет умножен на коэффициенты дней недели и закон распределения"
            )
        
        submitted = st.form_submit_button("💾 Сохранить товар", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("❌ Введите название товара")
            elif purchase <= 0 or sale <= 0:
                st.error("❌ Цены должны быть больше 0")
            elif purchase >= sale:
                st.warning("⚠️ Цена закупки выше или равна цене продажи. Вы будете в убытке.")
                if st.button("Всё равно добавить"):
                    cat_id = 1 if cat == "strict" else 2
                    db.add_product(name, cat_id, purchase, sale, shelf, base_demand)
                    st.success(f"✅ Товар '{name}' добавлен!")
                    st.rerun()
            else:
                cat_id = 1 if cat == "strict" else 2
                db.add_product(name, cat_id, purchase, sale, shelf, base_demand)
                st.success(f"✅ Товар '{name}' добавлен!")
                st.rerun()

# ==================================================
# ТАБ 2: ИСТОРИЯ ЭКСПЕРИМЕНТОВ
# ==================================================
with tab2:
    st.subheader("Сохранённые симуляции")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    with col2:
        if st.button("🗑️ Очистить всё", type="secondary", key="clear_all"):
            with sqlite3.connect("database/perishable.db") as conn:
                conn.execute("DELETE FROM experiments")
                conn.execute("DELETE FROM sqlite_sequence WHERE name='experiments'")
            st.success("✅ Все эксперименты удалены!")
            st.rerun()
    
    exp_df = db.get_all_experiments()
    
    if not exp_df.empty:
        # Переименовываем колонки на русский язык
        exp_df_display = exp_df.rename(columns={
            'id_experiment': 'ID',
            'product_name': 'Товар',
            'distribution': 'Закон спроса',
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
        exp_df_display['Тип поставок'] = exp_df_display['Тип поставок'].map({
            'periodic': 'Периодические',
            'days_of_week': 'По дням недели'
        })
        exp_df_display['Тип упаковки'] = exp_df_display['Тип упаковки'].map({
            'unit': 'Штучно',
            'box': 'Коробками/ящиками'
        })
        exp_df_display['Закон спроса'] = exp_df_display['Закон спроса'].map({
            'uniform': 'Равномерный',
            'normal': 'Нормальный'
        })
        exp_df_display['Тип порчи'] = exp_df_display['Тип порчи'].map({
            'strict': 'Строгая',
            'linear': 'Линейная',
            'exponential': 'Экспоненциальная'
        })
        
        # Сортируем по ID в обратном порядке (сначала новые)
        exp_df_display = exp_df_display.sort_values('ID', ascending=False)
        
        # Отображаем таблицу
        st.dataframe(exp_df_display, use_container_width=True, height=400)
        
        # Показываем количество записей
        st.caption(f"📊 Всего экспериментов: {len(exp_df_display)}")
        
        # Кнопка экспорта в CSV
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
