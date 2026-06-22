import streamlit as st
from backend.database import init_db, seed_from_csv
import backend.config as cfg

st.set_page_config(
    page_title="Structured Products Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def startup():
    init_db()
    seed_from_csv()
    return True


startup()

primary = cfg.get("primary_color") or "#2563EB"
secondary = cfg.get("secondary_color") or "#DC2626"
accent1 = cfg.get("accent_color_1") or "#F59E0B"

st.markdown(f"""
<style>
    /* ── Tabs ─────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        border-bottom: 2px solid #2d2d4e;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 42px;
        padding: 0 18px;
        border-radius: 6px 6px 0 0;
        font-weight: 600;
        font-size: 13px;
        color: #a0aec0;
        background: #1c1c2e;
        border: 1px solid #2d2d4e;
    }}
    .stTabs [aria-selected="true"] {{
        background: {primary} !important;
        color: white !important;
        border-color: {primary} !important;
    }}

    /* ── KPI metric cards ─────────────────────── */
    [data-testid="stMetric"] {{
        background: #1c1c2e;
        border-left: 4px solid {primary};
        border-radius: 8px;
        padding: 14px 18px;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.5rem;
        font-weight: 700;
        color: #f0f2f6;
    }}
    [data-testid="stMetricLabel"] {{
        color: #a0aec0;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    /* ── Buttons ──────────────────────────────── */
    .stButton>button[kind="primary"] {{
        background: {primary};
        border: none;
        color: white;
        font-weight: 600;
        border-radius: 6px;
    }}
    .stButton>button[kind="primary"]:hover {{
        background: {secondary};
    }}

    /* ── DataFrames ───────────────────────────── */
    [data-testid="stDataFrame"] {{
        border: 1px solid #2d2d4e;
        border-radius: 6px;
    }}

    /* ── Section headings ─────────────────────── */
    h1, h2, h3 {{ color: #f0f2f6; }}

    /* ── Dividers ─────────────────────────────── */
    hr {{ border-color: #2d2d4e; }}

    /* ── Sidebar ──────────────────────────────── */
    [data-testid="stSidebar"] {{ background: #12121f; }}

    /* ── Header accent bar ────────────────────── */
    .app-header {{
        background: linear-gradient(135deg, {primary} 0%, #12121f 60%);
        padding: 16px 24px 12px;
        border-radius: 10px;
        margin-bottom: 12px;
        border-left: 5px solid {accent1};
    }}
    .app-header h2 {{
        margin: 0;
        font-size: 1.35rem;
        font-weight: 700;
        color: white !important;
    }}
    .app-header p {{
        margin: 2px 0 0;
        font-size: 0.8rem;
        color: #a0aec0;
    }}
</style>
""", unsafe_allow_html=True)

# Header
company_name = cfg.get("company_name") or "My Company"
st.markdown(f"""
<div class="app-header">
    <h2>📊 {company_name} — Structured Products Manager</h2>
    <p>Investment Products Data Manager &nbsp;|&nbsp; Portfolio · Events · Factsheets · Reports</p>
</div>
""", unsafe_allow_html=True)

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
