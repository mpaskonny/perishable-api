import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from sidebar_config import setup_sidebar

# Устанавливаем параметр ДО загрузки боковой панели
st.query_params["page"] = "database"

# Загрузка единых стилей
with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Настройка боковой панели
setup_sidebar()

st.title("🗄️ Управление базой данных")
st.markdown("---")

# Инициализация менеджера БД
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager()

db = st.session_state.db_manager

# Вкладки
tab1, tab2, tab3, tab4 = st.tabs(["📦 Товары", "🥀 Параметры порчи", "🚚 Поставщики", "🔗 Связи товаров"])


# ========== ВКЛАДКА 1: ТОВАРЫ ==========
with tab1:
    st.subheader("Список товаров")
    
    products_df = db.get_all_products()
    products_df_display = products_df.rename(columns={
        'id_product': 'ID',
        'name': 'Название',
        'category': 'Категория',
        'purchase_price': 'Цена закупки (руб)',
        'sale_price': 'Цена продажи (руб)',
        'min_stock': 'Мин. запас',
        'shelf_life_days': 'Срок годности (дн)'
    })

    # Преобразуем значения категории из английского в русский
    products_df_display['Категория'] = products_df_display['Категория'].map({
        'strict': 'Строгий срок',
        'gradual': 'Постепенная порча'
    })

    st.dataframe(products_df_display, use_container_width=True)
    
    st.markdown("---")
    
    # Форма добавления товара
    with st.expander("➕ Добавить новый товар"):
        st.markdown("**Основные параметры**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("Название товара", placeholder="Например: Помидоры", key="new_name")
            new_category = st.selectbox("Категория", ["strict", "gradual"], 
                                        format_func=lambda x: "Строгий срок (молоко)" if x == "strict" else "Постепенная порча (помидоры)",
                                        key="new_category")
        
        with col2:
            new_purchase_price = st.number_input("Цена закупки (руб)", min_value=0.0, value=0.0, step=10.0, key="new_purchase")
            new_sale_price = st.number_input("Цена продажи (руб)", min_value=0.0, value=0.0, step=10.0, key="new_sale")
            new_min_stock = st.number_input("Минимальный запас", min_value=0.0, value=0.0, step=50.0, key="new_min_stock")
        
        st.markdown("**Параметры для категории «Строгий срок»**")
        
        with st.container():
            if new_category == "strict":
                new_shelf_life = st.number_input("Срок годности (дней)", min_value=1, value=10, step=1, key="new_shelf_life")
            else:
                new_shelf_life = None
                st.info("Для категории «Постепенная порча» срок годности не применяется")
        
        if st.button("💾 Сохранить товар", key="save_product"):
            if not new_name:
                st.error("❌ Введите название товара")
            elif new_purchase_price <= 0:
                st.error("❌ Цена закупки должна быть больше 0")
            elif new_sale_price <= 0:
                st.error("❌ Цена продажи должна быть больше 0")
            elif new_min_stock <= 0:
                st.error("❌ Минимальный запас должен быть больше 0")
            elif new_category == "strict" and new_shelf_life is None:
                st.error("❌ Для категории «Строгий срок» укажите срок годности")
            else:
                category_id = 1 if new_category == "strict" else 2
                product_id = db.add_product(new_name, category_id, new_purchase_price, 
                                            new_sale_price, new_min_stock, new_shelf_life)
                st.success(f"✅ Товар '{new_name}' добавлен с ID = {product_id}")
                st.rerun()
    
    # Форма редактирования/удаления
    with st.expander("✏️ Редактировать / удалить товар"):
        if not products_df.empty:
            selected_product = st.selectbox("Выберите товар", products_df['name'].tolist(), key="edit_select")
            product_data = db.get_product_by_name(selected_product)
            
            if product_data:
                st.markdown(f"**Редактирование товара: {selected_product}**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    edit_name = st.text_input("Название", product_data['name'], key="edit_name")
                    edit_purchase = st.number_input("Цена закупки (руб)", value=product_data['purchase_price'], step=10.0, key="edit_purchase")
                    edit_sale = st.number_input("Цена продажи (руб)", value=product_data['sale_price'], step=10.0, key="edit_sale")
                
                with col2:
                    edit_min_stock = st.number_input("Минимальный запас", value=product_data['min_stock'], step=50.0, key="edit_min_stock")
                    
                    if product_data['id_category'] == 1:
                        edit_shelf_life = st.number_input("Срок годности (дней)", value=product_data['shelf_life_days'] or 10, step=1, key="edit_shelf_life")
                    else:
                        edit_shelf_life = None
                        st.info("Для товаров с постепенной порчей срок годности не применяется")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Сохранить изменения", key="update_product"):
                        db.update_product(product_data['id_product'], 
                                         name=edit_name, 
                                         purchase_price=edit_purchase,
                                         sale_price=edit_sale, 
                                         min_stock=edit_min_stock,
                                         shelf_life_days=edit_shelf_life)
                        st.success("✅ Изменения сохранены")
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Удалить товар", type="secondary", key="delete_product"):
                        db.delete_product(product_data['id_product'])
                        st.warning(f"⚠️ Товар '{selected_product}' удалён")
                        st.rerun()
        else:
            st.info("Нет товаров в базе данных")


# ========== ВКЛАДКА 2: ПАРАМЕТРЫ ПОРЧИ ==========
with tab2:
    st.subheader("Параметры порчи по неделям")
    st.caption("Процент порчи за неделю. Например, 10% означает, что за неделю испортится 10% партии.")
    
    products_df = db.get_all_products()
    if not products_df.empty:
        gradual_products = products_df[products_df['category'] == 'gradual']
        
        if not gradual_products.empty:
            product_options = {row['name']: row['id_product'] for _, row in gradual_products.iterrows()}
            selected_product_name = st.selectbox("Выберите товар", list(product_options.keys()), key="spoilage_product")
            selected_product_id = product_options[selected_product_name]
            
            spoilage_df = db.get_spoilage_rates(selected_product_id)
            if not spoilage_df.empty:
                spoilage_df_display = spoilage_df.rename(columns={
                    'week_number': 'Неделя',
                    'rate': 'Процент порчи (%)'
                })
                st.dataframe(spoilage_df_display, use_container_width=True)
            else:
                st.info("Нет данных о порче для этого товара")
            
            st.markdown("---")
            
            with st.expander("➕ Добавить / изменить параметр порчи"):
                week_num = st.number_input("Номер недели", min_value=1, max_value=10, step=1, key="week_num")
                rate = st.number_input("Процент порчи (%)", min_value=0.0, max_value=100.0, step=5.0, key="rate")
                
                if st.button("💾 Сохранить параметр порчи", key="save_spoilage"):
                    db.add_spoilage_rate(selected_product_id, week_num, rate)
                    st.success(f"✅ Параметр порчи для недели {week_num} сохранён")
                    st.rerun()
            
            with st.expander("🗑️ Удалить параметр порчи"):
                week_to_delete = st.number_input("Номер недели для удаления", min_value=1, max_value=10, step=1, key="week_delete")
                if st.button("Удалить", key="delete_spoilage"):
                    db.delete_spoilage_rate(selected_product_id, week_to_delete)
                    st.warning(f"⚠️ Параметр порчи для недели {week_to_delete} удалён")
                    st.rerun()
        else:
            st.info("Нет товаров с категорией «Постепенная порча»")
    else:
        st.info("Сначала добавьте товары")

# ========== ВКЛАДКА 3: ПОСТАВЩИКИ ==========
with tab3:
    st.subheader("🚚 Управление поставщиками")
    
    suppliers_df = db.get_all_suppliers()
    
    if not suppliers_df.empty:
        suppliers_df_display = suppliers_df.rename(columns={
            'id_supplier': 'ID',
            'name': 'Название',
            'delivery_type': 'Тип поставок',
            'packing_type': 'Тип упаковки',
            'box_size': 'Размер упаковки',
            'delivery_interval': 'Интервал (дней)',
            'delivery_days': 'Дни поставок',
            'description': 'Описание'
        })
        
        # Преобразуем типы в читаемый вид
        suppliers_df_display['Тип поставок'] = suppliers_df_display['Тип поставок'].map({
            'periodic': 'Периодические',
            'days_of_week': 'По дням недели'
        })
        suppliers_df_display['Тип упаковки'] = suppliers_df_display['Тип упаковки'].map({
            'unit': 'Штучно',
            'box': 'Коробками/ящиками'
        })
        
        st.dataframe(suppliers_df_display, use_container_width=True)
    else:
        st.info("Нет поставщиков в базе данных")
    
    st.markdown("---")
    
    # Форма добавления поставщика
    with st.expander("➕ Добавить нового поставщика"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_supplier_name = st.text_input("Название поставщика", placeholder="Например: ООО МолокоТрейд", key="new_supplier_name")
            new_delivery_type = st.selectbox("Тип поставок", ["periodic", "days_of_week"], 
                                              format_func=lambda x: "Периодические (каждые N дней)" if x == "periodic" else "По дням недели",
                                              key="new_delivery_type")
        
        with col2:
            new_packing_type = st.radio("Тип упаковки", ["unit", "box"], 
                                         format_func=lambda x: "Штучно (кг/пакеты)" if x == "unit" else "Коробками/ящиками",
                                         horizontal=True, key="new_packing_type")
            
            new_box_size = 1
            if new_packing_type == "box":
                new_box_size = st.number_input("Размер упаковки (кг/пакетов)", min_value=1, value=20, step=5, key="new_box_size")
        
        new_description = st.text_area("Описание", placeholder="Дополнительная информация о поставщике", key="new_description")
        
        # Поля в зависимости от типа поставок
        if new_delivery_type == "periodic":
            new_delivery_interval = st.number_input("Интервал поставок (дней)", min_value=1, max_value=30, value=3, step=1, key="new_interval")
            new_delivery_days = None
        else:
            new_delivery_interval = None
            days_options = {
                "Понедельник": 0, "Вторник": 1, "Среда": 2,
                "Четверг": 3, "Пятница": 4, "Суббота": 5, "Воскресенье": 6
            }
            selected_days = st.multiselect("Выберите дни поставок", list(days_options.keys()), default=["Понедельник", "Четверг"], key="new_days")
            new_delivery_days = ",".join(str(days_options[day]) for day in selected_days)
        
        if st.button("💾 Сохранить поставщика", key="save_supplier"):
            if not new_supplier_name:
                st.error("❌ Введите название поставщика")
            else:
                id_type = 1 if new_delivery_type == "periodic" else 2
                id_pack_type = 1 if new_packing_type == "unit" else 2
                
                supplier_id = db.add_supplier(new_supplier_name, id_type, id_pack_type, 
                                              new_box_size, new_delivery_interval, 
                                              new_delivery_days, new_description)
                st.success(f"✅ Поставщик '{new_supplier_name}' добавлен")
                st.rerun()
    
    # Форма редактирования/удаления
    with st.expander("✏️ Редактировать / удалить поставщика"):
        suppliers_df = db.get_all_suppliers()
        if not suppliers_df.empty:
            selected_supplier_name = st.selectbox("Выберите поставщика", suppliers_df['name'].tolist(), key="edit_supplier_select")
            supplier_data = db.get_supplier_by_name(selected_supplier_name)
            
            if supplier_data:
                st.markdown(f"**Редактирование поставщика: {selected_supplier_name}**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    edit_name = st.text_input("Название", supplier_data['name'], key="edit_supplier_name")
                    edit_delivery_type = st.selectbox("Тип поставок", ["periodic", "days_of_week"],
                                                       index=0 if supplier_data['id_type'] == 1 else 1,
                                                       format_func=lambda x: "Периодические (каждые N дней)" if x == "periodic" else "По дням недели",
                                                       key="edit_delivery_type")
                
                with col2:
                    edit_packing_type = st.radio("Тип упаковки", ["unit", "box"],
                                                  index=0 if supplier_data['id_pack_type'] == 1 else 1,
                                                  format_func=lambda x: "Штучно (кг/пакеты)" if x == "unit" else "Коробками/ящиками",
                                                  horizontal=True, key="edit_packing_type")
                    
                    edit_box_size = supplier_data['box_size'] or 1
                    if edit_packing_type == "box":
                        edit_box_size = st.number_input("Размер упаковки (кг/пакетов)", value=edit_box_size, min_value=1, step=5, key="edit_box_size")
                
                edit_description = st.text_area("Описание", supplier_data['description'] or "", key="edit_description")
                
                # Поля в зависимости от типа поставок
                if edit_delivery_type == "periodic":
                    edit_interval = st.number_input("Интервал поставок (дней)", value=supplier_data['delivery_interval'] or 3, min_value=1, max_value=30, step=1, key="edit_interval")
                    edit_days = None
                else:
                    edit_interval = None
                    days_options_reverse = {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"}
                    current_days = [days_options_reverse[int(d)] for d in supplier_data['delivery_days'].split(",")] if supplier_data['delivery_days'] else []
                    selected_edit_days = st.multiselect("Выберите дни поставок", list(days_options_reverse.values()), default=current_days, key="edit_days")
                    edit_days = ",".join(str(list(days_options_reverse.keys())[list(days_options_reverse.values()).index(day)]) for day in selected_edit_days)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Сохранить изменения", key="update_supplier"):
                        id_type = 1 if edit_delivery_type == "periodic" else 2
                        id_pack_type = 1 if edit_packing_type == "unit" else 2
                        
                        db.update_supplier(supplier_data['id_supplier'],
                                          name=edit_name,
                                          id_type=id_type,
                                          id_pack_type=id_pack_type,
                                          box_size=edit_box_size,
                                          delivery_interval=edit_interval,
                                          delivery_days=edit_days,
                                          description=edit_description)
                        st.success("✅ Изменения сохранены")
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Удалить поставщика", type="secondary", key="delete_supplier"):
                        db.delete_supplier(supplier_data['id_supplier'])
                        st.warning(f"⚠️ Поставщик '{selected_supplier_name}' удалён")
                        st.rerun()
        else:
            st.info("Нет поставщиков для редактирования")

# ========== ВКЛАДКА 4: СВЯЗИ ТОВАРОВ И ПОСТАВЩИКОВ ==========
with tab4:
    st.subheader("🔗 Связи товаров и поставщиков")
    
    products_df = db.get_all_products()
    suppliers_df = db.get_all_suppliers()
    
    if products_df.empty:
        st.info("Сначала добавьте товары")
    elif suppliers_df.empty:
        st.info("Сначала добавьте поставщиков")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_product = st.selectbox("Выберите товар", products_df['name'].tolist(), key="link_product")
            product_id = db.get_product_id_by_name(selected_product)
        
        with col2:
            # Показываем только не связанных поставщиков
            existing_suppliers = db.get_product_suppliers(product_id)
            existing_ids = existing_suppliers['id_supplier'].tolist() if not existing_suppliers.empty else []
            
            available_suppliers = suppliers_df[~suppliers_df['id_supplier'].isin(existing_ids)]
            
            if not available_suppliers.empty:
                selected_supplier = st.selectbox("Выберите поставщика", available_suppliers['name'].tolist(), key="link_supplier")
                supplier_id = db.get_supplier_id_by_name(selected_supplier)
                box_size = st.number_input("Размер упаковки (шт/кг)", min_value=1, value=1, step=1, key="link_box_size")
                
                if st.button("➕ Добавить связь", key="add_link"):
                    db.add_product_supplier(product_id, supplier_id)
                    st.success(f"✅ Поставщик '{selected_supplier}' связан с товаром '{selected_product}'")
                    st.rerun()
            else:
                st.info("Все поставщики уже связаны с этим товаром")
        
        st.markdown("---")
        
        # Отображение текущих связей
        st.subheader(f"📋 Поставщики для товара «{selected_product}»")
        
        product_suppliers = db.get_product_suppliers(product_id)
        
        if not product_suppliers.empty:
            display_df = product_suppliers.rename(columns={
                'id_supplier': 'ID',
                'name': 'Поставщик',
                'delivery_type': 'Тип поставок',
                'delivery_interval': 'Интервал',
                'delivery_days': 'Дни поставок',
                'box_size': 'Размер упаковки'
            })
            
            # Преобразуем тип поставок в читаемый вид
            display_df['Тип поставок'] = display_df['Тип поставок'].map({
                'periodic': 'Периодические',
                'days_of_week': 'По дням недели'
            })
            
            st.dataframe(display_df, use_container_width=True)
            
            # Удаление связи
            st.markdown("---")
            st.subheader("🗑️ Удалить связь")
            
            supplier_to_remove = st.selectbox("Выберите поставщика для удаления", 
                                               product_suppliers['name'].tolist(), 
                                               key="remove_supplier")
            supplier_id_remove = db.get_supplier_id_by_name(supplier_to_remove)
            
            if st.button("🗑️ Удалить связь", key="remove_link"):
                db.delete_product_supplier(product_id, supplier_id_remove)
                st.warning(f"⚠️ Связь с поставщиком '{supplier_to_remove}' удалена")
                st.rerun()
        else:
            st.info("Нет связанных поставщиков")
