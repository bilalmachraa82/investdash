"""InvestDash — AI-Powered Personal Investment Dashboard."""

import streamlit as st

from backend.ui_theme import inject_theme

st.set_page_config(
    page_title="InvestDash",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# Sidebar brand mark
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 8px 0 20px 0; border-bottom: 1px solid rgba(148,163,184,0.08); margin-bottom: 16px;">
          <div style="display:flex; align-items:center; gap:10px;">
            <div style="width:32px; height:32px; border-radius:8px;
                        background: linear-gradient(135deg, #3B82F6 0%, #A855F7 100%);
                        display:flex; align-items:center; justify-content:center;
                        box-shadow: 0 4px 12px -4px rgba(59,130,246,0.5);">
              <span style="color:white; font-weight:700; font-size:16px;">I</span>
            </div>
            <div>
              <div style="font-weight:600; color:#E2E8F0; font-size:0.95rem; letter-spacing:-0.01em;">InvestDash</div>
              <div style="font-size:0.7rem; color:#64748B; text-transform:uppercase; letter-spacing:0.08em;">AI Portfolio</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
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
