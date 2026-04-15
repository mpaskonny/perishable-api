import streamlit as st

def setup_sidebar():
    """Настройка единой боковой панели для всех страниц"""
    
    # Получаем текущую страницу (уже установлена до вызова)
    current_page = st.query_params.get("page", "home")
    
    # Скрываем стандартную навигацию
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none !important;
            }
            [data-testid="collapsedControl"] {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🧭 Навигация")
        st.markdown("---")
        
        # Главная
        if current_page == "home":
            st.markdown("""
                <button style="width:100%; background: linear-gradient(135deg, #e94560, #533483); color:white; border:none; border-radius:10px; padding:0.5rem; margin-bottom:0.3rem;">
                    🏠 Главная
                </button>
            """, unsafe_allow_html=True)
        else:
            if st.button("🏠 Главная", use_container_width=True, key="nav_home"):
                st.switch_page("app.py")
        
        # Симуляция
        if current_page == "simulation":
            st.markdown("""
                <button style="width:100%; background: linear-gradient(135deg, #e94560, #533483); color:white; border:none; border-radius:10px; padding:0.5rem; margin-bottom:0.3rem;">
                    🎮 Симуляция
                </button>
            """, unsafe_allow_html=True)
        else:
            if st.button("🎮 Симуляция", use_container_width=True, key="nav_simulation"):
                st.switch_page("pages/01_simulation.py")
        
        # База данных
        if current_page == "database":
            st.markdown("""
                <button style="width:100%; background: linear-gradient(135deg, #e94560, #533483); color:white; border:none; border-radius:10px; padding:0.5rem; margin-bottom:0.3rem;">
                    🗄️ База данных
                </button>
            """, unsafe_allow_html=True)
        else:
            if st.button("🗄️ База данных", use_container_width=True, key="nav_db"):
                st.switch_page("pages/02_database_manager.py")
        
        st.markdown("---")
