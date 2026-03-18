"""InvestDash — AI-Powered Personal Investment Dashboard."""

import streamlit as st

st.set_page_config(
    page_title="InvestDash",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── FinTech Dark Theme CSS ──────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0D1B2A;
}

/* Metric cards — glassmorphism */
div[data-testid="stMetric"] {
    background: rgba(17, 29, 46, 0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(41, 98, 255, 0.15);
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

/* Positive / Negative delta colors */
div[data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Up"] {
    fill: #00C853;
}
div[data-testid="stMetricDelta"] svg[data-testid="stMetricDeltaIcon-Down"] {
    fill: #FF1744;
}
[data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Up"]) {
    color: #00C853;
}
[data-testid="stMetricDelta"]:has(svg[data-testid="stMetricDeltaIcon-Down"]) {
    color: #FF1744;
}

/* Buttons */
button[kind="primary"], .stButton > button[kind="primary"] {
    background-color: #2962FF;
    border: none;
    border-radius: 8px;
    transition: background-color 0.2s ease;
}
button[kind="primary"]:hover {
    background-color: #1E88E5;
}

/* Dataframe / Table */
div[data-testid="stDataFrame"] {
    background: rgba(17, 29, 46, 0.5);
    border-radius: 10px;
    border: 1px solid rgba(41, 98, 255, 0.1);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

/* Containers */
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
    gap: 1rem;
}

/* Tab styling */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
}

/* Expander */
details {
    background: rgba(17, 29, 46, 0.4);
    border: 1px solid rgba(41, 98, 255, 0.1);
    border-radius: 8px;
}
</style>""", unsafe_allow_html=True)

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
