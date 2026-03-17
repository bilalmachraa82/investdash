"""InvestDash — AI-Powered Personal Investment Dashboard."""

import streamlit as st

st.set_page_config(
    page_title="InvestDash",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigation
pages = {
    "Dashboard": [st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊")],
    "Portfolio": [st.Page("pages/2_Portfolio.py", title="Portfolio", icon="💼")],
    "Research": [st.Page("pages/5_Research.py", title="Research", icon="🔍")],
    "AI Chat": [st.Page("pages/3_AI_Chat.py", title="AI Chat", icon="🤖")],
    "Trading": [st.Page("pages/4_Trading.py", title="Trading", icon="📉")],
}

nav = st.navigation(pages)
nav.run()
