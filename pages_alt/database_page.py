import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_manager import DatabaseManager
from pages_alt.dialogs import (
    add_product_modal,
    edit_product_modal,
    delete_product_modal,
    clear_experiments_modal
)
from pages_alt.simulation_page import export_experiment_to_excel


@st.dialog("📊 Детали эксперимента", width="large")
def view_experiment_dialog(experiment_data: dict, db):
    """Диалоговое окно с детальными метриками эксперимента"""
    
    exp = experiment_data['experiment']
    settings = experiment_data['settings']
    
    st.markdown(f"### Эксперимент #{exp['id_experiment']} | {settings.get('product_name', '-')}")
    st.caption(f"📅 Сохранён: {exp.get('created_at', '-')}")
    
    st.markdown("---")
    
    # ===== ОСНОВНЫЕ МЕТРИКИ =====
    st.markdown("#### 📈 Основные метрики")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Выручка", f"{exp.get('total_revenue', 0):,.2f} руб")
        st.metric("Затраты на закупку", f"{exp.get('total_purchase_cost', 0):,.2f} руб")
        st.metric("Затраты на доставку", f"{exp.get('total_delivery_cost', 0):,.2f} руб")
        st.metric("Затраты на утилизацию", f"{exp.get('total_utilization_cost', 0):,.2f} руб")
        st.metric("Итого затраты", f"{exp.get('total_cost', 0):,.2f} руб")
    
    with col2:
        st.metric("Прибыль", f"{exp.get('profit', 0):,.2f} руб")
        st.metric("Потери от порчи", f"{exp.get('total_spoilage_kg', 0):.2f} кг")
        st.metric("Потери в деньгах", f"{exp.get('total_spoilage_money', 0):,.2f} руб")
        st.metric("Неудовлетворённый спрос", f"{exp.get('total_unmet_demand', 0):.2f} кг")
        st.metric("Средний остаток", f"{exp.get('avg_stock', 0):.2f} кг")
    
    st.markdown("---")
    
    # ===== ПАРАМЕТРЫ ЭКСПЕРИМЕНТА =====
    st.markdown("#### ⚙️ Параметры эксперимента")
    
    strategy_names = {
        "r_s": "(R, S) — периодическая до целевого уровня",
        "r_q": "(R, Q) — фиксированный объём по расписанию",
        "s_s": "(s, S) — двухуровневая (точка заказа)",
        "s_q": "(s, Q) — двухуровневая с фиксированным объёмом",
        "custom": "Пользовательская"
    }
    strategy_display = strategy_names.get(settings.get('strategy_type', 'r_s'), settings.get('strategy_type', '-'))
    
    spoilage_names = {
        "strict": "Строгий срок (мгновенная порча)",
        "linear": "Линейная (равномерное старение)",
        "power": "Степенная (ускорение к концу)",
        "logistic": "Логистическая (S-образная)"
    }
    spoilage_display = spoilage_names.get(settings.get('spoilage_type', 'linear'), settings.get('spoilage_type', '-'))
    
    spoilage_detail = ""
    if settings.get('spoilage_type') == 'power' and settings.get('power_p'):
        spoilage_detail = f" (p={settings['power_p']:.1f})"
    elif settings.get('spoilage_type') == 'logistic' and settings.get('logistic_k'):
        spoilage_detail = f" (k={settings['logistic_k']:.0f})"
    
    dist_names = {
        "uniform": "Равномерный",
        "normal": "Нормальный"
    }
    dist_display = dist_names.get(settings.get('distribution', 'uniform'), settings.get('distribution', '-'))
    
    fifo = settings.get('fifo_percent')
    fifo_display = f"{fifo}% FIFO / {100-fifo}% LIFO" if fifo is not None else "—"
    
    period = f"{settings.get('start_date', '-')} — {settings.get('end_date', '-')} ({settings.get('days', 0)} дней)"
    
    params_data = {
        'Параметр': [
            'Товар',
            'Категория',
            'Стратегия поставок',
            'Закон спроса',
            'Модель порчи',
            'FIFO / LIFO',
            'Цена закупки',
            'Цена продажи',
            'Срок годности',
            'Базовый спрос',
            'Период симуляции',
            'Количество прогонов',
            'Seed'
        ],
        'Значение': [
            settings.get('product_name', '-'),
            "Строгий срок" if settings.get('product_category') == 'strict' else "Постепенная порча",
            strategy_display,
            dist_display,
            spoilage_display + spoilage_detail,
            fifo_display,
            f"{settings.get('purchase_price', 0):.2f} руб",
            f"{settings.get('sale_price', 0):.2f} руб",
            f"{settings.get('shelf_life_days', 0)} дней",
            f"{settings.get('base_demand', 0):.0f} ед/день",
            period,
            str(settings.get('num_simulations', 1)),
            str(settings.get('random_seed', '-'))
        ]
    }
    
    params_df = pd.DataFrame(params_data)
    st.dataframe(params_df, hide_index=True, use_container_width=True)
    
    st.markdown("---")
    
    # ===== КНОПКИ =====
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        try:
            excel_file = export_experiment_to_excel(db, exp['id_experiment'])
            if excel_file:
                st.download_button(
                    label="📊 Выгрузить в Excel",
                    data=excel_file,
                    file_name=f"experiment_{exp['id_experiment']}_{settings.get('product_name', 'export')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_in_dialog_{exp['id_experiment']}",
                    use_container_width=True
                )
            else:
                st.error("❌ Ошибка формирования Excel")
        except Exception as e:
            st.error(f"❌ Ошибка выгрузки: {e}")
    
    with col_btn2:
        if st.button("❌ Закрыть", use_container_width=True):
            # Очищаем состояние диалога
            st.session_state.show_view_dialog = False
            st.session_state.view_experiment_data = None
            st.rerun()


@st.dialog("🗑️ Удаление эксперимента", width="small")
def confirm_delete_experiment(exp_id: int, exp_name: str, db):
    """Диалог подтверждения удаления эксперимента"""
    
    st.warning(f"⚠️ Вы действительно хотите удалить эксперимент **#{exp_id}** ({exp_name})?")
    st.caption("Это действие невозможно отменить. Все данные эксперимента будут удалены из базы данных.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Да, удалить", type="secondary", use_container_width=True):
            try:
                db.delete_experiment(exp_id)
                st.success(f"✅ Эксперимент #{exp_id} удалён!")
                # Очищаем состояние удаления
                st.session_state.show_delete_modal = False
                st.session_state.delete_exp_id = None
                st.session_state.delete_exp_name = None
                st.rerun()
            except Exception as e:
                st.error(f"❌ Ошибка удаления: {e}")
    with col2:
        if st.button("❌ Отмена", type="primary", use_container_width=True):
            st.session_state.show_delete_modal = False
            st.session_state.delete_exp_id = None
            st.session_state.delete_exp_name = None
            st.rerun()


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
    if 'show_view_dialog' not in st.session_state:
        st.session_state.show_view_dialog = False
    if 'view_experiment_data' not in st.session_state:
        st.session_state.view_experiment_data = None
    if 'delete_exp_id' not in st.session_state:
        st.session_state.delete_exp_id = None
    if 'delete_exp_name' not in st.session_state:
        st.session_state.delete_exp_name = None
    if 'editing_product' not in st.session_state:
        st.session_state.editing_product = None
    if 'delete_product_name' not in st.session_state:
        st.session_state.delete_product_name = None
    if 'delete_product_id' not in st.session_state:
        st.session_state.delete_product_id = None

    
    tab1, tab2 = st.tabs(["📦 Товары", "📊 История экспериментов"])
    
    # ========== ТОВАРЫ ==========
    with tab1:
        st.subheader("📋 Список товаров")
        
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("➕ Добавить товар", type="primary", use_container_width=True):
                st.session_state.show_edit_modal = False
                st.session_state.show_delete_modal = False
                st.session_state.show_clear_modal = False
                st.session_state.show_view_dialog = False
                st.session_state.show_add_modal = True
        
        products_df = db.get_all_products()
        
        if not products_df.empty:
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
                        st.session_state.show_view_dialog = False
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
                        st.session_state.show_view_dialog = False
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
                st.session_state.show_view_dialog = False
                st.session_state.show_clear_modal = True
        
        exp_df = db.get_all_experiments()
        
        if not exp_df.empty:
            # Заголовки таблицы
            col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11 = st.columns(
                [0.5, 1.2, 1.0, 1.0, 1.0, 0.8, 0.8, 0.8, 1.0, 0.5, 0.5]
            )
            with col1:
                st.write("**ID**")
            with col2:
                st.write("**Товар**")
            with col3:
                st.write("**Стратегия**")
            with col4:
                st.write("**Прибыль**")
            with col5:
                st.write("**Выручка**")
            with col6:
                st.write("**Затраты**")
            with col7:
                st.write("**Потери**")
            with col8:
                st.write("**Неуд.спрос**")
            with col9:
                st.write("**Дата**")
            with col10:
                st.write("")
            with col11:
                st.write("")
            
            st.divider()
            
            for idx, row in exp_df.iterrows():
                col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11 = st.columns(
                    [0.5, 1.2, 1.0, 1.0, 1.0, 0.8, 0.8, 0.8, 1.0, 0.5, 0.5]
                )
                
                with col1:
                    st.write(f"{row['id_experiment']}")
                with col2:
                    st.write(f"{row['product_name'][:20]}")
                with col3:
                    strategy = row.get('strategy_type', 'r_s')
                    strategy_short = {
                        "r_s": "(R,S)",
                        "r_q": "(R,Q)",
                        "s_s": "(s,S)",
                        "s_q": "(s,Q)"
                    }.get(strategy, strategy)
                    st.write(strategy_short)
                with col4:
                    profit = row.get('profit', 0)
                    color = "green" if profit >= 0 else "red"
                    st.markdown(f"<span style='color:{color}'>{profit:,.0f}</span>", unsafe_allow_html=True)
                with col5:
                    st.write(f"{row.get('total_revenue', 0):,.0f}")
                with col6:
                    st.write(f"{row.get('total_cost', 0):,.0f}")
                with col7:
                    st.write(f"{row.get('total_spoilage_kg', 0):.1f}")
                with col8:
                    st.write(f"{row.get('total_unmet_demand', 0):.0f}")
                with col9:
                    created = row.get('created_at', '')
                    if created:
                        try:
                            if isinstance(created, str):
                                created = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
                            st.write(created.strftime('%d.%m.%Y'))
                        except:
                            st.write(str(created)[:10])
                    else:
                        st.write("-")
                with col10:
                    if st.button("📊", key=f"view_{row['id_experiment']}", help="Просмотреть детали"):
                        exp_data = db.get_full_experiment_data(row['id_experiment'])
                        if exp_data:
                            st.session_state.show_view_dialog = True
                            st.session_state.view_experiment_data = exp_data
                            st.rerun()
                        else:
                            st.error("❌ Не удалось загрузить данные эксперимента")
                with col11:
                    if st.button("🗑️", key=f"del_exp_{row['id_experiment']}", help="Удалить эксперимент"):
                        st.session_state.show_view_dialog = False
                        st.session_state.view_experiment_data = None
                        st.session_state.delete_exp_id = row['id_experiment']
                        st.session_state.delete_exp_name = row['product_name']
                        st.session_state.show_delete_modal = True
                        st.rerun()
                
                st.divider()
            
            st.caption(f"📊 Всего экспериментов: {len(exp_df)}")
        else:
            st.info("📭 Нет сохранённых экспериментов")
    
    # ========== ВЫЗОВ МОДАЛЬНЫХ ОКОН ==========
    
    # Модальное окно просмотра эксперимента
    if st.session_state.get('show_view_dialog', False) and st.session_state.get('view_experiment_data'):
        view_experiment_dialog(st.session_state.view_experiment_data, db)
    
    # Модальное окно удаления эксперимента
    if st.session_state.get('show_delete_modal', False):
        confirm_delete_experiment(
            st.session_state.delete_exp_id,
            st.session_state.delete_exp_name,
            db
        )
    
    # Остальные модальные окна
    if st.session_state.get('show_add_modal', False):
        add_product_modal()
    elif st.session_state.get('show_edit_modal', False) and st.session_state.get('editing_product'):
        edit_product_modal()
    elif st.session_state.get('show_clear_modal', False):
        clear_experiments_modal()