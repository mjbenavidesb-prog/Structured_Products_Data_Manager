import streamlit as st
from backend.database import init_db, seed_from_csv
import backend.config as cfg

st.set_page_config(
    page_title="Structured Products Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize DB and seed data on first run
@st.cache_resource
def startup():
    init_db()
    seed_from_csv()
    return True

startup()

# Apply company colors from config
primary = cfg.get("primary_color") or "#003087"
secondary = cfg.get("secondary_color") or "#E31837"

st.markdown(f"""
<style>
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [data-baseweb="tab"] {{
        height: 44px;
        padding: 0 20px;
        border-radius: 6px 6px 0 0;
        font-weight: 600;
        font-size: 14px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {primary};
        color: white;
    }}
    .metric-card {{
        background: #f8f9fa;
        border-left: 4px solid {primary};
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 8px;
    }}
    h1 {{ color: {primary}; }}
    h2 {{ color: {primary}; }}
</style>
""", unsafe_allow_html=True)

# Header
company_name = cfg.get("company_name") or "Structured Products Manager"
col_logo, col_title = st.columns([1, 6])
with col_title:
    st.markdown(f"## 📊 {company_name} — Structured Products Manager")

st.divider()

# Navigation tabs
tabs = st.tabs([
    "📁 Load Product",
    "📈 Portfolio",
    "📅 Maturities & Autocalls",
    "📄 Generate Factsheet",
    "📊 Reports",
    "⚙️ Settings",
])

with tabs[0]:
    from pages.tab_upload import render
    render()

with tabs[1]:
    from pages.tab_portfolio import render
    render()

with tabs[2]:
    from pages.tab_events import render
    render()

with tabs[3]:
    from pages.tab_factsheet import render
    render()

with tabs[4]:
    from pages.tab_reports import render
    render()

with tabs[5]:
    from pages.tab_config import render
    render()
