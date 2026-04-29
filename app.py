import streamlit as st

st.set_page_config(
    page_title="Симулятор продуктов",
    page_icon="🥛",
    layout="wide"
)

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

# Устанавливаем параметр ДО загрузки боковой панели
if "page" not in st.query_params:
    st.query_params["page"] = "home"

from sidebar_config import setup_sidebar



# Загрузка единых стилей
with open("styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Настройка боковой панели
setup_sidebar()
# Заголовок
st.markdown('<div class="main-title">🥛 Симулятор продуктов</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">с ограниченным сроком годности</div>', unsafe_allow_html=True)

st.markdown("---")

# Приветствие
st.markdown("""
<div class="welcome-banner">
    <h3>👋 Добро пожаловать!</h3>
    <p>Это приложение поможет вам проанализировать и оптимизировать управление запасами 
    скоропортящихся товаров. Проводите эксперименты, сравнивайте стратегии и выбирайте 
    оптимальные решения.</p>
</div>
""", unsafe_allow_html=True)

# О проекте
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

# Возможности (3 колонки)
st.markdown('<h2 class="section-title">🎯 Возможности</h2>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">📦 Два типа товаров</div>
        <ul>
            <li><b>Строгий срок годности</b> (молоко)<br>
            Порча наступает мгновенно после истечения срока</li>
            <li><b>Постепенная порча</b> (помидоры)<br>
            Порча нарастает по дням</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">📊 Гибкие настройки</div>
        <ul>
            <li>Два закона распределения спроса</li>
            <li>Стратегии поставок (периодические / по дням)</li>
            <li>Поведение покупателей (FIFO / LIFO)</li>
            <li>Поставки штучно или коробками/ящиками</li>
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

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    <div class="steps-container">
        <p><span class="step-number">1</span> <span class="step-text">Перейдите на вкладку <b>«Симуляция»</b> в боковой панели</span></p>
        <p><span class="step-number">2</span> <span class="step-text">Выберите продукт (Молоко / Помидоры)</span></p>
        <p><span class="step-number">3</span> <span class="step-text">Настройте параметры спроса, цен и поставок</span></p>
        <p><span class="step-number">4</span> <span class="step-text">Нажмите <b>«Запустить симуляцию»</b></span></p>
        <p><span class="step-number">5</span> <span class="step-text">Анализируйте графики, таблицы и метрики</span></p>
        <p style="margin-top: 1rem;"><span class="step-text">🗄️ Для добавления собственных товаров перейдите на вкладку <b>«Управление БД»</b></span></p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="stat-demo">
        <div style="font-size: 2rem;">📊</div>
        <div style="font-size: 1.1rem;">Пример результатов</div>
        <hr>
        <div>Выручка: <span class="stat-value">372 000 ₽</span></div>
        <div>Прибыль: <span class="stat-value">87 000 ₽</span></div>
        <div>Потери: <span class="stat-value">5.2 кг</span></div>
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

# Подвал (футер)
st.markdown("""
<div class="footer">
    <b>АлтГТУ, кафедра ИСЭ</b><br>
    Курсовой проект • 2025<br>
    Автор: <b>Авдеев Александр Сергеевич</b> | Группа: <b>ПИЭ-81</b>
</div>
""", unsafe_allow_html=True)
