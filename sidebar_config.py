import streamlit as st

def setup_sidebar():
    """Настройка единой боковой панели для всех страниц"""
    
    # Скрываем стандартную навигацию Streamlit
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none !important;
            }
            [data-testid="collapsedControl"] {
                display: none !important;
            }
            /* Принудительное расширение основного контента */
            .main .block-container {
                max-width: 100% !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🧭 Навигация")
        st.markdown("---")
        
        # Главная
        if st.button("🏠 Главная", use_container_width=True, key="nav_home"):
            st.switch_page("app.py")
        
        # Симуляция
        if st.button("🎮 Симуляция", use_container_width=True, key="nav_simulation"):
            st.switch_page("pages/01_simulation.py")
        
        # База данных
        if st.button("🗄️ База данных", use_container_width=True, key="nav_db"):
            st.switch_page("pages/02_database_manager.py")
        
        st.markdown("---")