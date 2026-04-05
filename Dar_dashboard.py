# ================================
# 🕌 دار روضة القرآن — لوحة التحكم
# ================================
import streamlit as st

st.set_page_config(
    page_title="دار روضة القرآن",
    layout="wide",
    page_icon="🕌",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# دار روضة القرآن\nنظام إدارة الطلاب والمحفظين"
    }
)

# ================================
# 📦 IMPORTS
# ================================
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import os
import gc
import hmac
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta, date
import warnings
warnings.filterwarnings('ignore')

# ================================
# ⚙️ LOGGING
# ================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================================
# 🎨 THEME — دار روضة القرآن
# ================================
class DarTheme:
    PRIMARY        = "#1B6B5A"
    PRIMARY_DARK   = "#134E41"
    PRIMARY_LIGHT  = "#2A8C75"
    PRIMARY_GLOW   = "rgba(27,107,90,0.25)"
    GOLD           = "#C9A84C"
    GOLD_DARK      = "#A8892E"
    GOLD_LIGHT     = "#E2C06A"
    GOLD_GLOW      = "rgba(201,168,76,0.25)"
    SECONDARY      = "#1A1A1A"
    SECONDARY_SOFT = "#2C2C2C"
    ACCENT_EMERALD  = "#10B981"
    ACCENT_AMBER    = "#F59E0B"
    ACCENT_CRIMSON  = "#EF4444"
    ACCENT_SAPPHIRE = "#3B82F6"
    ACCENT_VIOLET   = "#8B5CF6"
    ACCENT_ROSE     = "#F43F5E"
    ACCENT_TEAL     = "#14B8A6"
    ACCENT_ORANGE   = "#F97316"
    BG_WHITE        = "#FFFFFF"
    BG_LIGHT        = "#F0F7F5"
    BG_CARD         = "#F7FBF9"
    BG_DARK         = "#0A1A16"
    TEXT_PRIMARY    = "#1A1A1A"
    TEXT_SECONDARY  = "#6B7280"
    TEXT_LIGHT      = "#FFFFFF"
    TEXT_TEAL       = "#1B6B5A"
    TEXT_GOLD       = "#C9A84C"
    BORDER_RADIUS        = "14px"
    BORDER_RADIUS_LARGE  = "22px"
    BORDER_RADIUS_PILL   = "50px"
    SHADOW_SMALL  = "0 2px 8px rgba(27,107,90,0.12)"
    SHADOW_MEDIUM = "0 6px 20px rgba(27,107,90,0.18)"
    SHADOW_LARGE  = "0 12px 40px rgba(27,107,90,0.22)"
    SHADOW_HOVER  = "0 20px 60px rgba(27,107,90,0.30)"
    SHADOW_GLOW   = "0 0 30px rgba(27,107,90,0.35)"
    SHADOW_GOLD   = "0 0 30px rgba(201,168,76,0.35)"
    FONT_FAMILY   = "'Cairo', 'Tajawal', 'Arial', sans-serif"

    @staticmethod
    def gradient(c1, c2, angle=135):
        return f"linear-gradient({angle}deg, {c1} 0%, {c2} 100%)"

    @staticmethod
    def teal_gradient(angle=135):
        return DarTheme.gradient(DarTheme.PRIMARY_DARK, DarTheme.PRIMARY_LIGHT, angle)

    @staticmethod
    def gold_gradient(angle=135):
        return DarTheme.gradient(DarTheme.GOLD_DARK, DarTheme.GOLD_LIGHT, angle)

    @staticmethod
    def hero_gradient(angle=135):
        return DarTheme.gradient(DarTheme.PRIMARY_DARK, DarTheme.PRIMARY, angle)

T = DarTheme

# ================================
# 🖼️ LOGO HELPER
# ================================
def get_logo_base64():
    try:
        logo_path = Path(__file__).parent / "Dar Logo.png"
        if logo_path.exists():
            with open(logo_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        return None
    except Exception as e:
        logger.warning(f"Logo not found: {e}")
        return None

LOGO_B64 = get_logo_base64()

# ================================
# 🔢 UTILITY FUNCTIONS
# ================================
def fmt_num(n):
    if pd.isna(n): return "0"
    n = float(n)
    if abs(n) >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:     return f"{n/1_000:.1f}K"
    return f"{int(n):,}"

def fmt_pct(n, dp=1):
    if pd.isna(n): return "0.0%"
    return f"{float(n):.{dp}f}%"

def fmt_currency(n):
    if pd.isna(n) or n == 0: return "—"
    return f"{int(float(n)):,} ج.م"

# ================================
# 🔐 AUTHENTICATION
# ================================
def check_password():
    try:
        VALID_USER = st.secrets["auth"]["username"]
        VALID_PASS = st.secrets["auth"]["password"]
    except Exception:
        VALID_USER = "admin"
        VALID_PASS = "dar2026"

    def _verify():
        try:
            u_ok = hmac.compare_digest(st.session_state.get("username", ""), VALID_USER)
            p_ok = hmac.compare_digest(st.session_state.get("password", ""), VALID_PASS)
            st.session_state["auth_ok"] = u_ok and p_ok
            if u_ok and p_ok:
                st.session_state.pop("password", None)
                st.session_state.pop("username", None)
        except Exception:
            st.session_state["auth_ok"] = False

    if st.session_state.get("auth_ok", False):
        return True

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800;900&family=Tajawal:wght@300;400;500;700;800&display=swap');
    * {{ font-family: {T.FONT_FAMILY}; direction: rtl; }}
    #MainMenu, footer, header {{ visibility: hidden; }}
    .stApp {{
        background: {T.gradient("#0A1A16", "#0F2E24", 160)};
        background-size: 400% 400%;
        animation: bgShift 12s ease infinite;
    }}
    @keyframes bgShift {{
        0%   {{ background-position: 0% 50%; }}
        50%  {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    .login-wrap {{ max-width: 460px; margin: 5vh auto 0; }}
    .login-logo-card {{
        background: {T.gradient("#0F2E24","#1B4A3A",160)};
        border-radius: 22px 22px 0 0;
        padding: 2.8rem 2rem 2rem;
        text-align: center;
        border: 1px solid {T.PRIMARY};
        border-bottom: none;
        box-shadow: {T.SHADOW_GLOW};
    }}
    .login-title {{ color: {T.GOLD_LIGHT}; font-size: 1.6rem; font-weight: 800; margin: 1.2rem 0 0.3rem; }}
    .login-sub {{ color: {T.TEXT_SECONDARY}; font-size: 0.95rem; font-weight: 500; }}
    .login-form-card {{
        background: {T.BG_CARD};
        border-radius: 0 0 22px 22px;
        padding: 2rem;
        border: 1px solid {T.PRIMARY};
        border-top: none;
        box-shadow: {T.SHADOW_LARGE};
    }}
    .stTextInput > label {{ color: {T.PRIMARY} !important; font-weight: 700 !important; font-size: 0.9rem !important; }}
    .stTextInput > div > div > input {{
        background: #F7FBF9; border: 2px solid #C8E0DA;
        border-radius: {T.BORDER_RADIUS}; padding: 13px 16px;
        font-size: 1rem; font-weight: 500; color: {T.TEXT_PRIMARY};
        transition: all 0.3s ease; text-align: right;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {T.PRIMARY}; box-shadow: 0 0 0 4px {T.PRIMARY_GLOW};
    }}
    .stButton > button {{
        width: 100%; background: {T.teal_gradient()}; color: {T.TEXT_LIGHT};
        border: none; border-radius: {T.BORDER_RADIUS}; padding: 14px 20px;
        font-size: 1.05rem; font-weight: 700; cursor: pointer;
        transition: all 0.3s ease; box-shadow: {T.SHADOW_MEDIUM}; margin-top: 1rem;
    }}
    .stButton > button:hover {{ transform: translateY(-3px); box-shadow: {T.SHADOW_HOVER}; }}
    .login-footer {{ text-align: center; color: rgba(255,255,255,0.5); margin-top: 1.8rem; font-size: 0.85rem; font-weight: 500; }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    logo_html = (f'<img src="data:image/png;base64,{LOGO_B64}" style="max-width:160px;height:auto;filter:drop-shadow(0 4px 12px rgba(27,107,90,0.5));">'
                 if LOGO_B64 else '<div style="font-size:3rem;">🕌</div>')
    st.markdown(f"""
    <div class="login-logo-card">
        {logo_html}
        <div class="login-title">دار روضة القرآن</div>
        <div class="login-sub">نظام إدارة الطلاب والمحفظين</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="login-form-card">', unsafe_allow_html=True)
    with st.form("login_form"):
        st.text_input("👤 اسم المستخدم", key="username", placeholder="أدخل اسم المستخدم")
        st.text_input("🔑 كلمة المرور", type="password", key="password", placeholder="أدخل كلمة المرور")
        if st.form_submit_button("🚀 تسجيل الدخول"):
            _verify()
            if st.session_state.get("auth_ok"):
                st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة. حاول مرة أخرى.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-footer">🔒 دخول آمن &nbsp;|&nbsp; دار روضة القرآن</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()

# ================================
# 🎨 GLOBAL CSS
# ================================
def inject_global_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800;900&family=Tajawal:wght@300;400;500;700;800&display=swap');
    * {{ font-family: {T.FONT_FAMILY}; }}
    #MainMenu, footer {{ visibility: hidden; }}
    .stApp {{
        background: linear-gradient(160deg, #F0F7F5 0%, #E8F4F0 50%, #DFF0EA 100%);
        background-size: 400% 400%;
        animation: bgPulse 20s ease infinite;
        direction: rtl;
    }}
    @keyframes bgPulse {{ 0%,100% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} }}
    .block-container {{
        padding: 1.5rem 2.5rem;
        background: rgba(255,255,255,0.97);
        border-radius: {T.BORDER_RADIUS_LARGE};
        box-shadow: 0 20px 60px rgba(27,107,90,0.10);
        backdrop-filter: blur(20px);
        max-width: 1600px;
        border: 1px solid rgba(27,107,90,0.12);
    }}
    section[data-testid="stSidebar"] {{ background: {T.gradient("#0A1A16","#0F2E24",180)} !important; direction: rtl; }}
    section[data-testid="stSidebar"] * {{ color: {T.TEXT_LIGHT} !important; }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label {{ color: {T.GOLD_LIGHT} !important; font-weight: 600 !important; }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px; background: {T.teal_gradient(90)};
        padding: 12px 16px; border-radius: {T.BORDER_RADIUS_LARGE};
        box-shadow: {T.SHADOW_MEDIUM}; direction: rtl;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: rgba(255,255,255,0.15); color: white !important;
        border-radius: {T.BORDER_RADIUS}; padding: 10px 18px;
        font-weight: 700; font-size: 0.9rem; border: 2px solid transparent; transition: all 0.3s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{ background: rgba(255,255,255,0.28); transform: translateY(-2px); }}
    .stTabs [aria-selected="true"] {{
        background: white !important; color: {T.PRIMARY_DARK} !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.2); transform: translateY(-2px);
    }}
    .stButton > button {{
        background: {T.teal_gradient()}; color: white; border: none;
        border-radius: {T.BORDER_RADIUS}; padding: 10px 22px;
        font-weight: 700; font-size: 0.92rem; transition: all 0.3s ease; box-shadow: {T.SHADOW_SMALL};
    }}
    .stButton > button:hover {{ transform: translateY(-3px); box-shadow: {T.SHADOW_HOVER}; }}
    div.stDownloadButton > button {{
        background: {T.gold_gradient()} !important; color: white !important;
        border: none !important; border-radius: {T.BORDER_RADIUS} !important;
        font-weight: 700 !important; transition: all 0.3s ease !important;
    }}
    [data-testid="stMetric"] {{
        background: {T.BG_CARD}; border: 1px solid rgba(27,107,90,0.2);
        border-radius: {T.BORDER_RADIUS}; padding: 14px; box-shadow: {T.SHADOW_SMALL};
    }}
    .main-header {{
        text-align: center; padding: 2.5rem 2rem;
        background: {T.hero_gradient(135)}; border-radius: {T.BORDER_RADIUS_LARGE};
        margin-bottom: 2rem; box-shadow: {T.SHADOW_GLOW};
        position: relative; overflow: hidden; animation: slideDown 0.8s ease-out; direction: rtl;
    }}
    .main-header::before {{
        content: ''; position: absolute; top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(201,168,76,0.15) 0%, transparent 70%);
        animation: rotate 18s linear infinite;
    }}
    @keyframes rotate  {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    @keyframes slideDown {{ from {{ opacity:0; transform:translateY(-50px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes fadeInUp  {{ from {{ opacity:0; transform:translateY(30px); }} to {{ opacity:1; transform:translateY(0); }} }}
    .main-header h1 {{
        color: white; font-size: 2.4rem; font-weight: 900; margin: 0;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.3); position: relative; z-index: 1;
    }}
    .main-header p {{ color: rgba(255,255,255,0.92); font-size: 1.05rem; margin-top: 0.6rem; font-weight: 400; position: relative; z-index: 1; }}
    .main-header .gold-text {{ color: {T.GOLD_LIGHT}; font-weight: 800; }}
    .kpi-card {{
        background: {T.teal_gradient(135)}; padding: 1.6rem 1.2rem;
        border-radius: {T.BORDER_RADIUS_LARGE}; box-shadow: 0 10px 30px rgba(27,107,90,0.35);
        text-align: center; transition: all 0.4s cubic-bezier(0.175,0.885,0.32,1.275);
        animation: fadeInUp 0.6s ease-out; color: white; position: relative; overflow: hidden;
        cursor: pointer; min-height: 145px; display: flex; flex-direction: column;
        justify-content: center; align-items: center; direction: rtl;
    }}
    .kpi-card::before {{
        content: ''; position: absolute; top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.18), transparent);
        transition: left 0.55s;
    }}
    .kpi-card:hover::before {{ left: 100%; }}
    .kpi-card:hover {{ transform: translateY(-12px) scale(1.03); box-shadow: 0 22px 55px rgba(27,107,90,0.50); }}
    .kpi-card .kpi-icon  {{ font-size: 2.2rem; margin-bottom: 0.4rem; }}
    .kpi-card .kpi-value {{ font-size: 2rem; font-weight: 900; line-height:1.1; }}
    .kpi-card .kpi-label {{ font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.92; margin-top: 0.3rem; }}
    .kpi-card .kpi-sub   {{ font-size: 0.78rem; opacity: 0.8; margin-top: 0.2rem; }}
    .kpi-gold    {{ background: {T.gold_gradient(135)}; box-shadow: 0 10px 30px rgba(201,168,76,0.35); }}
    .kpi-emerald {{ background: linear-gradient(135deg, #059669 0%, #10B981 100%); box-shadow: 0 10px 30px rgba(16,185,129,0.35); }}
    .kpi-amber   {{ background: linear-gradient(135deg, #D97706 0%, #F59E0B 100%); box-shadow: 0 10px 30px rgba(245,158,11,0.35); }}
    .kpi-crimson {{ background: linear-gradient(135deg, #DC2626 0%, #EF4444 100%); box-shadow: 0 10px 30px rgba(239,68,68,0.35); }}
    .kpi-sapphire{{ background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%); box-shadow: 0 10px 30px rgba(59,130,246,0.35); }}
    .kpi-violet  {{ background: linear-gradient(135deg, #6D28D9 0%, #8B5CF6 100%); box-shadow: 0 10px 30px rgba(139,92,246,0.35); }}
    .kpi-teal    {{ background: linear-gradient(135deg, #0D9488 0%, #14B8A6 100%); box-shadow: 0 10px 30px rgba(20,184,166,0.35); }}
    .kpi-rose    {{ background: linear-gradient(135deg, #BE185D 0%, #F43F5E 100%); box-shadow: 0 10px 30px rgba(244,63,94,0.35); }}
    .insight-box {{ padding: 1.2rem 1.4rem; border-radius: {T.BORDER_RADIUS}; margin-bottom: 1rem; box-shadow: {T.SHADOW_SMALL}; animation: fadeInUp 0.5s ease-out; direction: rtl; }}
    .insight-success {{ background: rgba(16,185,129,0.08); border-right: 5px solid {T.ACCENT_EMERALD}; }}
    .insight-warning {{ background: rgba(245,158,11,0.08); border-right: 5px solid {T.ACCENT_AMBER}; }}
    .insight-danger  {{ background: rgba(239,68,68,0.08);  border-right: 5px solid {T.ACCENT_CRIMSON}; }}
    .insight-info    {{ background: rgba(59,130,246,0.08); border-right: 5px solid {T.ACCENT_SAPPHIRE}; }}
    .insight-teal    {{ background: rgba(27,107,90,0.08);  border-right: 5px solid {T.PRIMARY}; }}
    .insight-gold    {{ background: rgba(201,168,76,0.08); border-right: 5px solid {T.GOLD}; }}
    .schedule-card {{
        background: white; border: 1px solid rgba(27,107,90,0.2);
        border-radius: {T.BORDER_RADIUS}; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
        box-shadow: {T.SHADOW_SMALL}; transition: all 0.3s ease; direction: rtl;
    }}
    .schedule-card:hover {{ border-color: {T.PRIMARY}; box-shadow: {T.SHADOW_MEDIUM}; transform: translateX(-4px); }}
    .badge-active   {{ background: rgba(16,185,129,0.15); color: #059669; padding: 3px 10px; border-radius: 50px; font-size: 0.8rem; font-weight: 700; }}
    .badge-frozen   {{ background: rgba(59,130,246,0.15); color: #1D4ED8; padding: 3px 10px; border-radius: 50px; font-size: 0.8rem; font-weight: 700; }}
    .badge-inactive {{ background: rgba(239,68,68,0.15);  color: #DC2626; padding: 3px 10px; border-radius: 50px; font-size: 0.8rem; font-weight: 700; }}
    .salary-card {{
        background: {T.gradient("rgba(27,107,90,0.05)","rgba(201,168,76,0.05)",135)};
        border: 1px solid rgba(27,107,90,0.2); border-radius: {T.BORDER_RADIUS_LARGE};
        padding: 1.5rem; margin-bottom: 1rem; box-shadow: {T.SHADOW_SMALL}; direction: rtl;
    }}
    .stTextInput input, .stSelectbox select, .stNumberInput input {{ text-align: right !important; direction: rtl !important; }}
    .section-header {{
        padding: 1.2rem 1.6rem;
        background: {T.gradient("rgba(27,107,90,0.08)","rgba(27,107,90,0.02)",135)};
        border-radius: {T.BORDER_RADIUS}; border-right: 5px solid {T.PRIMARY};
        margin-bottom: 1.2rem; box-shadow: {T.SHADOW_SMALL}; direction: rtl;
    }}
    .dar-table {{ width:100%; border-collapse:collapse; font-size:13px; background:white; direction:rtl; }}
    .dar-table thead tr {{ background: {T.teal_gradient(135)}; color: white; position: sticky; top: 0; z-index: 10; }}
    .dar-table th {{ padding: 10px 12px; border: 1px solid {T.PRIMARY_DARK}; font-size: 12px; font-weight: 700; white-space: nowrap; text-align: center; }}
    .dar-table tbody tr:nth-child(odd)  {{ background: #F7FBF9; }}
    .dar-table tbody tr:nth-child(even) {{ background: #EEF7F3; }}
    .dar-table tbody tr:hover {{ background: rgba(27,107,90,0.10) !important; }}
    .dar-table td {{ padding: 8px 11px; border: 1px solid rgba(27,107,90,0.15); color: {T.TEXT_PRIMARY}; font-size: 12px; font-weight: 500; text-align: center; vertical-align: middle; }}
    </style>
    """, unsafe_allow_html=True)

inject_global_css()

# ================================
# 📊 GOOGLE SHEETS DATA LOADER
# ================================
SHEET_ID = "1u2oSOwtn9Qaz0rAzQxqCual_T1mcu8D2WBeTGAHB0YI"

SHEET_NAMES = {
    "students_full":  "الطلاب بينات كاملة",
    "students_month": "الطلاب شهر 3",
    "teachers":       "المحفظين",
    "dropdowns":      "Dropdown",
    "salary":         "اسلام وتقفيل المرتبات",
    "students_basic": "الطلاب",
}

def build_csv_url(sheet_id, sheet_name):
    encoded = sheet_name.replace(" ", "%20")
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded}"

@st.cache_data(ttl=300, show_spinner=False)
def load_all_data():
    results = {}
    for key, name in SHEET_NAMES.items():
        try:
            import urllib.parse
            encoded_name = urllib.parse.quote(name)
            url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={encoded_name}"
            df = pd.read_csv(url, encoding="utf-8")
            df.columns = df.columns.str.strip()
            df.dropna(how="all", inplace=True)
            df.reset_index(drop=True, inplace=True)
            results[key] = df
            logger.info(f"✅ Loaded '{name}': {len(df)} rows, {len(df.columns)} cols")
        except Exception as e:
            logger.error(f"❌ Failed to load '{name}': {e}")
            results[key] = pd.DataFrame()
    return results

def reload_data():
    load_all_data.clear()
    st.session_state["data_loaded"] = False

# ── Initial load ──────────────────────────────────────────────────────────────
if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False

with st.spinner("⏳ جاري تحميل البيانات..."):
    try:
        DATA = load_all_data()
        st.session_state["data_loaded"] = True
    except Exception as e:
        st.error(f"❌ فشل تحميل البيانات: {e}")
        DATA = {key: pd.DataFrame() for key in SHEET_NAMES}

students_df = DATA.get("students_full",  pd.DataFrame())
month_df    = DATA.get("students_month", pd.DataFrame())
teachers_df = DATA.get("teachers",       pd.DataFrame())

with st.sidebar.expander("🔧 تشخيص البيانات", expanded=True):
    for key, name in SHEET_NAMES.items():
        df_check = DATA.get(key, pd.DataFrame())
        if df_check.empty:
            st.sidebar.error(f"❌ {name} → فارغ")
        else:
            st.sidebar.success(f"✅ {name} → {len(df_check)} صف")

# ================================
# 🔧 DATA PROCESSING HELPERS
# ================================

# ── Constants ─────────────────────────────────────────────────────────────────
HOURLY_RATE       = 40     # fallback default — used in salary calculator UI
VODAFONE_CASH_FEE = 1.01   # 1% Vodafone Cash transfer fee multiplier

# ── Sidebar filter state (initialized once) ───────────────────────────────────
if "date_filter_mode" not in st.session_state:
    st.session_state["date_filter_mode"] = "الكل"
if "sel_month_year" not in st.session_state:
    st.session_state["sel_month_year"] = (datetime.now().month, datetime.now().year)
if "sel_date_from" not in st.session_state:
    st.session_state["sel_date_from"] = date(datetime.now().year, datetime.now().month, 1)
if "sel_date_to" not in st.session_state:
    st.session_state["sel_date_to"] = date.today()
if "sel_teacher_filter" not in st.session_state:
    st.session_state["sel_teacher_filter"] = "الكل"
if "sel_status_filter" not in st.session_state:
    st.session_state["sel_status_filter"] = "الكل"

def clean_students(df):
    if df.empty:
        return df
    df = df.copy()
    df.columns = df.columns.str.strip()
    for col in ["مدة الحصة (دقائق)", "مدة الحصة (ساعة)",
                "عدد الحصص الأسبوعية", "عدد الحصص الشهرية",
                "عدد الحصص الملغية", "قيمة الاشتراك الشهري", "العمر"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "حالة الاشتراك" in df.columns:
        df["حالة الاشتراك"] = df["حالة الاشتراك"].fillna("غير محدد").str.strip()
    return df

def clean_teachers(df):
    if df.empty:
        return df
    df = df.copy()
    for col in ["سنوات الخبرة", "سعر الساعة"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

students_df = clean_students(students_df)
teachers_df = clean_teachers(teachers_df)

def get_teacher_rate(teacher_name):
    if teachers_df.empty or "الاسم" not in teachers_df.columns:
        return 40
    mask  = teachers_df["الاسم"].astype(str).str.strip() == teacher_name.strip()
    match = teachers_df[mask]
    if match.empty:
        return 40
    rate = pd.to_numeric(match.iloc[0].get("سعر الساعة", 40), errors="coerce")
    return float(rate) if not pd.isna(rate) else 40

def compute_student_teacher_cost(row):
    def safe_num(val, default=0.0):
        result = pd.to_numeric(val, errors="coerce")
        return float(default) if (result is None or pd.isna(result)) else float(result)

    total_sessions = safe_num(row.get("عدد الحصص الشهرية", 0))
    cancelled      = safe_num(row.get("عدد الحصص الملغية",  0))
    net_sessions   = max(0.0, total_sessions - cancelled)

    duration_hr = safe_num(row.get("مدة الحصة (ساعة)", 0))
    if duration_hr == 0:
        duration_min = safe_num(row.get("مدة الحصة (دقائق)", 0))
        duration_hr  = duration_min / 60.0

    teacher_name = str(row.get("اسم المحفظ/ة", "")).strip()
    rate         = get_teacher_rate(teacher_name)
    cost         = round(net_sessions * duration_hr * rate, 2)

    return {
        "net_sessions":   int(net_sessions),
        "total_sessions": int(total_sessions),
        "cancelled":      int(cancelled),
        "duration_hr":    round(duration_hr, 4),
        "rate":           rate,
        "cost":           cost,
    }

def compute_teacher_salary_new(teacher_name, df):
    """Returns (total_hours, total_salary, breakdown_df, total_cost_with_fee)"""
    if df.empty:
        return 0, 0, pd.DataFrame(), 0

    mask       = df.get("اسم المحفظ/ة", pd.Series(dtype=str)).astype(str).str.strip() == teacher_name.strip()
    t_students = df[mask].copy()
    if t_students.empty:
        return 0, 0, pd.DataFrame(), 0

    rows         = []
    total_hours  = 0
    total_salary = 0

    for _, row in t_students.iterrows():
        calc       = compute_student_teacher_cost(row)
        hours_this = round(calc["net_sessions"] * calc["duration_hr"], 2)
        total_hours  += hours_this
        total_salary += calc["cost"]
        rows.append({
            "كود الطالب":       str(row.get("كود الطالب", "—")),
            "اسم الطالب":       str(row.get("الاسم بالكامل", "—")),
            "إجمالي الحصص":     calc["total_sessions"],
            "الحصص الملغية":    calc["cancelled"],
            "الحصص الفعلية":    calc["net_sessions"],
            "مدة الحصة (ساعة)": calc["duration_hr"],
            "ساعات الطالب":     hours_this,
            "سعر الساعة":       f"{calc['rate']:.0f} ج.م",
            "تكلفة الطالب":     f"{calc['cost']:,.0f} ج.م",
            "حالة الاشتراك":    str(row.get("حالة الاشتراك", "—")),
        })

    total_cost_with_fee = round(total_salary * VODAFONE_CASH_FEE, 2)
    return round(total_hours, 2), round(total_salary, 2), pd.DataFrame(rows), total_cost_with_fee

def compute_teacher_salary(teacher_name, df, rate=None):
    """Backward-compatible wrapper — returns (hours, salary)."""
    hours, salary, _, _ = compute_teacher_salary_new(teacher_name, df)
    return hours, salary

def compute_center_revenue(df):
    if df.empty:
        return 0
    active = df[df.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)]
    total  = pd.to_numeric(active.get("قيمة الاشتراك الشهري", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    return round(total, 2)

def compute_total_salaries(df_students, df_teachers):
    if df_teachers.empty:
        return 0
    total = 0
    for _, t in df_teachers.iterrows():
        name = str(t.get("الاسم", "")).strip()
        if name:
            _, salary, _, _ = compute_teacher_salary_new(name, df_students)
            total += salary
    return round(total, 2)

def get_session_dates(row, max_sessions=17):
    sessions = []
    for i in range(1, max_sessions + 1):
        date_col = f"تاريخ الحصة {i}"
        time_col = "وقت الحصة" if i == 1 else f"وقت الحصة.{i-1}"
        if date_col not in row.index:
            continue
        d = str(row.get(date_col, "")).strip()
        t = str(row.get(time_col, "")).strip()
        if d and d not in ("nan", "NaN", "", "////", "/////", "None"):
            sessions.append({"رقم الحصة": i, "التاريخ": d, "الوقت": t})
    return sessions

def get_next_week_schedule(student_code_or_name, df, weeks_ahead=1):
    if df.empty:
        return pd.DataFrame()
    mask = (
        df.get("كود الطالب", pd.Series(dtype=str)).astype(str).str.strip().str.upper()
        == str(student_code_or_name).strip().upper()
    ) | (
        df.get("الاسم بالكامل", pd.Series(dtype=str)).astype(str).str.strip()
        .str.contains(str(student_code_or_name).strip(), na=False)
    )
    found = df[mask]
    if found.empty:
        return pd.DataFrame()
    row      = found.iloc[0]
    sessions = get_session_dates(row)
    if not sessions:
        return pd.DataFrame()
    result = []
    for s in sessions:
        result.append({
            "كود الطالب":    str(row.get("كود الطالب", "")),
            "اسم الطالب":    str(row.get("الاسم بالكامل", "")),
            "المحفظ/ة":      str(row.get("اسم المحفظ/ة", "")),
            "التاريخ":        s["التاريخ"],
            "الوقت":          s["الوقت"],
            "مدة الحصة":     f"{row.get('مدة الحصة (دقائق)', row.get('مدة الحصة (ساعة)', '—'))}",
            "السورة الحالية": str(row.get("السورة الحالية", "")),
        })
    return pd.DataFrame(result)

def get_teacher_schedule(teacher_name, df):
    if df.empty:
        return pd.DataFrame()
    mask = df.get("اسم المحفظ/ة", pd.Series(dtype=str)).astype(str).str.strip().str.contains(
        str(teacher_name).strip(), na=False
    )
    teacher_students = df[mask]
    if teacher_students.empty:
        return pd.DataFrame()
    all_sessions = []
    for _, row in teacher_students.iterrows():
        for s in get_session_dates(row):
            all_sessions.append({
                "كود الطالب":    str(row.get("كود الطالب", "")),
                "اسم الطالب":    str(row.get("الاسم بالكامل", "")),
                "الفئة":         str(row.get("الفئة", "")),
                "التاريخ":        s["التاريخ"],
                "الوقت":          s["الوقت"],
                "مدة الحصة":     f"{row.get('مدة الحصة (دقائق)', row.get('مدة الحصة (ساعة)', '—'))}",
                "نظام الاشتراك": str(row.get("نظام الاشتراك", "")),
            })
    return pd.DataFrame(all_sessions) if all_sessions else pd.DataFrame()

def apply_global_filters(df):
    if df.empty:
        return df
    filtered  = df.copy()
    date_mode = st.session_state.get("date_filter_mode", "الكل")

    if date_mode == "اختيار شهر" and "تاريخ آخر تجديد" in filtered.columns:
        sel_m, sel_y = st.session_state.get("sel_month_year", (datetime.now().month, datetime.now().year))

        def matches_month_year(val):
            s = str(val).strip()
            if not s or s in ("nan", "NaN", "None", "—"):
                return False
            for fmt in ("%m/%Y", "%m-%Y", "%d/%m/%Y", "%d-%m-%Y",
                        "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%y", "%m-%d-%y"):
                try:
                    d = datetime.strptime(s, fmt)
                    return d.month == sel_m and d.year == sel_y
                except ValueError:
                    pass
            y2 = str(sel_y)[-2:]
            return (f"{sel_m:02d}" in s or f"/{sel_m}/" in s) and (y2 in s or str(sel_y) in s)

        filtered = filtered[filtered["تاريخ آخر تجديد"].apply(matches_month_year)]

    elif date_mode == "نطاق مخصص" and "تاريخ آخر تجديد" in filtered.columns:
        sel_from = st.session_state.get("sel_date_from", date(2020, 1, 1))
        sel_to   = st.session_state.get("sel_date_to",   date.today())

        def in_date_range(val):
            s = str(val).strip()
            if not s or s in ("nan", "NaN", "None", "—"):
                return False
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y",
                        "%d-%m-%y", "%m-%d-%y", "%m/%Y", "%m-%Y"):
                try:
                    d = datetime.strptime(s, fmt).date()
                    return sel_from <= d <= sel_to
                except ValueError:
                    pass
            return False

        filtered = filtered[filtered["تاريخ آخر تجديد"].apply(in_date_range)]

    sel_tf = st.session_state.get("sel_teacher_filter", "الكل")
    if sel_tf != "الكل" and "اسم المحفظ/ة" in filtered.columns:
        filtered = filtered[filtered["اسم المحفظ/ة"].astype(str).str.strip() == sel_tf]

    sel_sf = st.session_state.get("sel_status_filter", "الكل")
    if sel_sf != "الكل" and "حالة الاشتراك" in filtered.columns:
        filtered = filtered[filtered["حالة الاشتراك"].str.contains(sel_sf, na=False)]

    return filtered

# ================================
# 🧩 UI COMPONENTS
# ================================
def kpi_card(icon, value, label, variant="teal", subtitle=None):
    sub_html = f'<div class="kpi-sub">{subtitle}</div>' if subtitle else ""
    return f"""
    <div class="kpi-card {variant}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {sub_html}
    </div>"""

def section_header(title, subtitle="", icon=""):
    sub = f'<p style="color:{T.TEXT_SECONDARY};margin:0.3rem 0 0;font-size:0.9rem;">{subtitle}</p>' if subtitle else ""
    return f"""
    <div class="section-header">
        <h3 style="color:{T.PRIMARY_DARK};margin:0;font-size:1.25rem;font-weight:800;">{icon} {title}</h3>
        {sub}
    </div>"""

def display_table(df, title=None, download_name=None, max_height="480px", max_rows=None):
    if df is None or df.empty:
        st.warning("⚠️ لا توجد بيانات للعرض.")
        return
    display_df = df.head(max_rows).copy() if max_rows else df.copy()
    if title:
        st.markdown(f'<h4 style="color:{T.PRIMARY_DARK};font-weight:800;margin-bottom:0.5rem;direction:rtl;">{title}</h4>',
                    unsafe_allow_html=True)
    html = f"""
    <div style="overflow-x:auto;overflow-y:auto;max-height:{max_height};
                border:2px solid {T.PRIMARY};border-radius:{T.BORDER_RADIUS};
                box-shadow:{T.SHADOW_MEDIUM};">
    <table class="dar-table">
    <thead><tr>{"".join(f"<th>{c}</th>" for c in display_df.columns)}</tr></thead>
    <tbody>
    """
    for _, row in display_df.iterrows():
        html += "<tr>"
        for val in row:
            cell = "" if pd.isna(val) else str(val)
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)
    if max_rows and len(df) > max_rows:
        st.caption(f"📊 يعرض {max_rows} من {len(df):,} سجل")
    if download_name:
        st.download_button(
            f"📥 تحميل {download_name}",
            data=df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            file_name=download_name,
            mime="text/csv",
            key=f"dl_{download_name}_{id(df)}"
        )

def plotly_layout(fig, title="", height=420):
    fig.update_layout(
        title=dict(text=f'<b style="color:{T.PRIMARY_DARK};font-size:16px;">{title}</b>', x=0.5, xanchor="center"),
        plot_bgcolor="rgba(240,247,245,0.7)",
        paper_bgcolor="rgba(247,251,249,0.9)",
        font=dict(color=T.TEXT_PRIMARY, family=T.FONT_FAMILY, size=12),
        height=height,
        margin=dict(l=40, r=40, t=60, b=50),
        hovermode="x unified",
        legend=dict(bgcolor="rgba(255,255,255,0.92)", bordercolor=T.PRIMARY_LIGHT, borderwidth=1, font=dict(size=11))
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(27,107,90,0.10)", linecolor=T.PRIMARY_LIGHT, tickfont=dict(size=10))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(27,107,90,0.10)", linecolor=T.PRIMARY_LIGHT, tickfont=dict(size=10))
    return fig

CHART_COLORS = [
    T.PRIMARY, T.GOLD, T.ACCENT_EMERALD, T.ACCENT_SAPPHIRE,
    T.ACCENT_VIOLET, T.ACCENT_AMBER, T.ACCENT_ROSE, T.ACCENT_TEAL,
    T.ACCENT_ORANGE, T.ACCENT_CRIMSON, "#06B6D4", "#84CC16"
]

# ================================
# 🗂️ SIDEBAR
# ================================
def render_sidebar():
    logo_html = (f'<img src="data:image/png;base64,{LOGO_B64}" '
                 f'style="max-width:140px;height:auto;display:block;margin:0 auto 0.8rem;'
                 f'filter:drop-shadow(0 3px 10px rgba(27,107,90,0.5));">'
                 if LOGO_B64 else '<div style="font-size:2.5rem;text-align:center;">🕌</div>')

    st.sidebar.markdown(f"""
    <div style="background:{T.gradient('#0F2E24','#1B4A3A',160)};border:1px solid {T.PRIMARY};
        border-radius:{T.BORDER_RADIUS_LARGE};padding:1.5rem 1rem;text-align:center;
        margin-bottom:1rem;box-shadow:{T.SHADOW_GLOW};direction:rtl;">
        {logo_html}
        <div style="color:{T.GOLD_LIGHT};font-size:1rem;font-weight:800;">دار روضة القرآن</div>
        <div style="color:rgba(255,255,255,0.5);font-size:0.75rem;margin-top:0.2rem;">نظام الإدارة المتكامل</div>
    </div>
    """, unsafe_allow_html=True)

    active_count  = students_df["حالة الاشتراك"].str.contains("نشط", na=False).sum() if not students_df.empty and "حالة الاشتراك" in students_df.columns else 0
    frozen_count  = students_df["حالة الاشتراك"].str.contains("تجميد", na=False).sum() if not students_df.empty and "حالة الاشتراك" in students_df.columns else 0
    teacher_count = len(teachers_df) if not teachers_df.empty else 0
    total_rev_sb  = compute_center_revenue(students_df)

    st.sidebar.markdown(f"""
    <div style="background:rgba(27,107,90,0.15);border:1px solid {T.PRIMARY};
        border-radius:{T.BORDER_RADIUS};padding:0.9rem;margin-bottom:0.8rem;direction:rtl;">
        <div style="color:{T.GOLD_LIGHT};font-size:0.78rem;font-weight:700;margin-bottom:0.5rem;">📊 ملخص سريع</div>
        <div style="color:rgba(255,255,255,0.85);font-size:0.78rem;line-height:2;">
            ✅ <b style="color:#10B981;">طلاب نشطون:</b> {active_count}<br>
            🔵 <b style="color:#3B82F6;">تجميد مؤقت:</b> {frozen_count}<br>
            👩‍🏫 <b style="color:{T.GOLD_LIGHT};">المحفظون:</b> {teacher_count}<br>
            💰 <b style="color:{T.GOLD_LIGHT};">الإيرادات:</b> {fmt_currency(total_rev_sb)}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(f"""
    <div style="color:{T.GOLD_LIGHT};font-size:0.82rem;font-weight:700;margin:0.8rem 0 0.4rem;direction:rtl;">🔽 فلاتر عامة</div>
    """, unsafe_allow_html=True)

    date_mode = st.sidebar.radio(
        "📅 فلتر التاريخ",
        options=["الكل", "اختيار شهر", "نطاق مخصص"],
        index=["الكل", "اختيار شهر", "نطاق مخصص"].index(st.session_state.get("date_filter_mode", "الكل")),
        key="sb_date_mode",
        horizontal=False,
    )
    st.session_state["date_filter_mode"] = date_mode

    if date_mode == "اختيار شهر":
        ARABIC_MONTHS = {
            1:"يناير", 2:"فبراير", 3:"مارس",   4:"أبريل",
            5:"مايو",  6:"يونيو",  7:"يوليو",  8:"أغسطس",
            9:"سبتمبر",10:"أكتوبر",11:"نوفمبر",12:"ديسمبر",
        }
        current_m, current_y = st.session_state["sel_month_year"]
        col_m, col_y = st.sidebar.columns(2)
        with col_m:
            sel_m = st.selectbox("الشهر", options=list(ARABIC_MONTHS.keys()),
                                 format_func=lambda x: ARABIC_MONTHS[x],
                                 index=current_m - 1, key="sb_month_num")
        with col_y:
            year_opts = list(range(2023, datetime.now().year + 2))
            sel_y = st.selectbox("السنة", options=year_opts,
                                 index=year_opts.index(current_y) if current_y in year_opts else 0,
                                 key="sb_year_num")
        st.session_state["sel_month_year"] = (sel_m, sel_y)
        st.sidebar.markdown(f"""
        <div style="background:rgba(201,168,76,0.2);border:1px solid {T.GOLD};border-radius:8px;
            padding:0.4rem 0.7rem;margin-top:0.3rem;color:{T.GOLD_LIGHT};font-size:0.78rem;font-weight:700;direction:rtl;">
            🗓️ الفلتر النشط: {ARABIC_MONTHS[sel_m]} {sel_y}
        </div>
        """, unsafe_allow_html=True)

    elif date_mode == "نطاق مخصص":
        sel_from = st.sidebar.date_input("📆 من تاريخ", value=st.session_state["sel_date_from"],
                                         key="sb_date_from", format="YYYY/MM/DD")
        sel_to   = st.sidebar.date_input("📆 إلى تاريخ", value=st.session_state["sel_date_to"],
                                         key="sb_date_to",   format="YYYY/MM/DD")
        if sel_from > sel_to:
            st.sidebar.warning("⚠️ تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
            sel_from, sel_to = sel_to, sel_from
        st.session_state["sel_date_from"] = sel_from
        st.session_state["sel_date_to"]   = sel_to
        st.sidebar.markdown(f"""
        <div style="background:rgba(59,130,246,0.15);border:1px solid {T.ACCENT_SAPPHIRE};border-radius:8px;
            padding:0.4rem 0.7rem;margin-top:0.3rem;color:rgba(255,255,255,0.9);font-size:0.78rem;font-weight:700;direction:rtl;">
            📅 {sel_from.strftime('%Y/%m/%d')} → {sel_to.strftime('%Y/%m/%d')}
        </div>
        """, unsafe_allow_html=True)

    teacher_opts = ["الكل"]
    if not teachers_df.empty and "الاسم" in teachers_df.columns:
        teacher_opts += sorted(teachers_df["الاسم"].dropna().unique().tolist())
    sel_tf = st.sidebar.selectbox(
        "👩‍🏫 المحفظ/ة", teacher_opts,
        index=teacher_opts.index(st.session_state["sel_teacher_filter"]) if st.session_state["sel_teacher_filter"] in teacher_opts else 0,
        key="sb_teacher")
    st.session_state["sel_teacher_filter"] = sel_tf

    status_opts = ["الكل", "نشط", "تجميد مؤقت", "موقوف"]
    sel_sf = st.sidebar.selectbox(
        "📌 حالة الاشتراك", status_opts,
        index=status_opts.index(st.session_state["sel_status_filter"]) if st.session_state["sel_status_filter"] in status_opts else 0,
        key="sb_status")
    st.session_state["sel_status_filter"] = sel_sf

    if st.sidebar.button("🔁 إعادة ضبط الفلاتر", use_container_width=True):
        st.session_state["date_filter_mode"]   = "الكل"
        st.session_state["sel_month_year"]     = (datetime.now().month, datetime.now().year)
        st.session_state["sel_date_from"]      = date(datetime.now().year, datetime.now().month, 1)
        st.session_state["sel_date_to"]        = date.today()
        st.session_state["sel_teacher_filter"] = "الكل"
        st.session_state["sel_status_filter"]  = "الكل"
        st.rerun()

    st.sidebar.markdown("---")

    if st.sidebar.button("🔄 تحديث البيانات", use_container_width=True):
        load_all_data.clear()
        st.session_state["data_loaded"] = False
        st.rerun()

    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.clear()
        st.rerun()

render_sidebar()
filtered_students_df = apply_global_filters(students_df)

# ================================
# 📊 MAIN HEADER
# ================================
logo_html_header = (
    f'<img src="data:image/png;base64,{LOGO_B64}" '
    f'style="max-height:70px;width:auto;vertical-align:middle;'
    f'filter:drop-shadow(0 2px 8px rgba(0,0,0,0.3));">'
    if LOGO_B64 else "🕌"
)

total_students = len(students_df) if not students_df.empty else 0
total_revenue  = compute_center_revenue(students_df)

st.markdown(f"""
<div class="main-header">
    <div style="position:relative;z-index:1;">
        {logo_html_header}
        <h1 style="margin-top:0.6rem;">دار روضة القرآن</h1>
        <p>نظام إدارة الطلاب والمحفظين &nbsp;•&nbsp;
           <span class="gold-text">{total_students}</span> طالب مسجّل &nbsp;•&nbsp;
           إيرادات شهرية: <span class="gold-text">{fmt_currency(total_revenue)}</span>
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# ================================
# 📑 TABS
# ================================
(tab_overview,
 tab_students,
 tab_teachers,
 tab_schedule,
 tab_finance,
 tab_search) = st.tabs([
    "📊 لوحة المتابعة",
    "👨‍🎓 الطلاب",
    "👩‍🏫 المحفظون",
    "📅 الجداول",
    "💰 المالية",
    "🔍 البحث والأتمتة",
])

# ============================================================
# TAB 1 — لوحة المتابعة
# ============================================================
with tab_overview:
    st.markdown(section_header("لوحة المتابعة الرئيسية", "نظرة شاملة على أداء الدار", "📊"), unsafe_allow_html=True)

    if not students_df.empty:
        active_students = students_df["حالة الاشتراك"].str.contains("نشط", na=False).sum() if "حالة الاشتراك" in students_df.columns else 0
        frozen_students = students_df["حالة الاشتراك"].str.contains("تجميد", na=False).sum() if "حالة الاشتراك" in students_df.columns else 0
        total_salary    = compute_total_salaries(students_df, teachers_df)
        net_profit      = total_revenue - total_salary
    else:
        active_students = frozen_students = 0
        total_salary = net_profit = 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.markdown(kpi_card("👨‍🎓", fmt_num(total_students),    "إجمالي الطلاب",      "teal"),    unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("✅",   fmt_num(active_students),   "طلاب نشطون",         "emerald"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("⏸️",  fmt_num(frozen_students),   "تجميد مؤقت",         "sapphire"),unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("💰",   fmt_currency(total_revenue),"الإيرادات الشهرية",  "gold"),    unsafe_allow_html=True)
    with c5: st.markdown(kpi_card("💸",   fmt_currency(total_salary), "رواتب المحفظين",     "amber"),   unsafe_allow_html=True)
    with c6: st.markdown(kpi_card("📈",   fmt_currency(net_profit),   "صافي الربح",
                                  "emerald" if net_profit >= 0 else "crimson"), unsafe_allow_html=True)

    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if not students_df.empty and "حالة الاشتراك" in students_df.columns:
            status_counts = students_df["حالة الاشتراك"].value_counts()
            fig_status = go.Figure(go.Pie(
                labels=status_counts.index.tolist(),
                values=status_counts.values.tolist(),
                hole=0.55,
                marker=dict(colors=[T.ACCENT_EMERALD, T.ACCENT_SAPPHIRE, T.ACCENT_CRIMSON, T.ACCENT_AMBER]),
                textinfo="label+percent",
                textfont=dict(size=11, family=T.FONT_FAMILY),
            ))
            plotly_layout(fig_status, "توزيع حالات الاشتراك", 340)
            fig_status.update_layout(showlegend=False)
            st.plotly_chart(fig_status, use_container_width=True)

    with col_b:
        if not students_df.empty and "الفئة" in students_df.columns:
            cat_counts = students_df["الفئة"].value_counts()
            fig_cat = go.Figure(go.Bar(
                x=cat_counts.values.tolist(),
                y=cat_counts.index.tolist(),
                orientation="h",
                marker=dict(color=CHART_COLORS[:len(cat_counts)], line=dict(color="white", width=1)),
                text=cat_counts.values.tolist(),
                textposition="outside",
            ))
            plotly_layout(fig_cat, "الطلاب حسب الفئة", 340)
            fig_cat.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_cat, use_container_width=True)

    with col_c:
        if not students_df.empty and "نظام الاشتراك" in students_df.columns:
            sub_counts = students_df["نظام الاشتراك"].value_counts()
            fig_sub = go.Figure(go.Pie(
                labels=sub_counts.index.tolist(),
                values=sub_counts.values.tolist(),
                hole=0.5,
                marker=dict(colors=[T.PRIMARY, T.GOLD, T.ACCENT_TEAL]),
                textinfo="label+value",
                textfont=dict(size=11),
            ))
            plotly_layout(fig_sub, "نظام الدراسة", 340)
            fig_sub.update_layout(showlegend=False)
            st.plotly_chart(fig_sub, use_container_width=True)

    col_d, col_e = st.columns([1.4, 0.6])

    with col_d:
        if not students_df.empty and "اسم المحفظ/ة" in students_df.columns:
            teacher_load = students_df[
                students_df.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)
            ]["اسم المحفظ/ة"].value_counts()
            fig_load = go.Figure(go.Bar(
                x=teacher_load.index.tolist(),
                y=teacher_load.values.tolist(),
                marker=dict(color=CHART_COLORS[:len(teacher_load)], line=dict(color="white", width=1)),
                text=teacher_load.values.tolist(),
                textposition="outside",
            ))
            plotly_layout(fig_load, "عدد الطلاب النشطين لكل محفظ/ة", 360)
            st.plotly_chart(fig_load, use_container_width=True)

    with col_e:
        if not students_df.empty and "المستوى" in students_df.columns:
            level_counts = students_df["المستوى"].dropna().value_counts()
            if not level_counts.empty:
                fig_level = go.Figure(go.Pie(
                    labels=level_counts.index.tolist(),
                    values=level_counts.values.tolist(),
                    hole=0.45,
                    marker=dict(colors=CHART_COLORS[:len(level_counts)]),
                    textinfo="label+percent",
                    textfont=dict(size=10),
                ))
                plotly_layout(fig_level, "توزيع المستويات", 360)
                fig_level.update_layout(showlegend=False)
                st.plotly_chart(fig_level, use_container_width=True)

    if not students_df.empty:
        st.markdown(section_header("الإيرادات حسب المحفظ/ة", "مجموع اشتراكات الطلاب النشطين لكل محفظ", "💰"), unsafe_allow_html=True)
        active_df = students_df[students_df.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)].copy()
        if not active_df.empty and "اسم المحفظ/ة" in active_df.columns:
            active_df["قيمة الاشتراك الشهري"] = pd.to_numeric(active_df.get("قيمة الاشتراك الشهري", 0), errors="coerce").fillna(0)
            rev_by_teacher = active_df.groupby("اسم المحفظ/ة")["قيمة الاشتراك الشهري"].sum().sort_values(ascending=False)
            fig_rev = go.Figure(go.Bar(
                x=rev_by_teacher.index.tolist(),
                y=rev_by_teacher.values.tolist(),
                marker=dict(color=T.GOLD, line=dict(color=T.GOLD_DARK, width=1)),
                text=[fmt_currency(v) for v in rev_by_teacher.values],
                textposition="outside",
            ))
            plotly_layout(fig_rev, "الإيرادات الشهرية حسب المحفظ/ة (ج.م)", 360)
            st.plotly_chart(fig_rev, use_container_width=True)

# ============================================================
# TAB 2 — الطلاب
# ============================================================
with tab_students:
    st.markdown(section_header("بيانات الطلاب", "عرض وتصفية بيانات جميع الطلاب المسجلين", "👨‍🎓"), unsafe_allow_html=True)

    if students_df.empty:
        st.error("❌ لم يتم تحميل بيانات الطلاب. اضغط 'تحديث البيانات' في الشريط الجانبي.")
    else:
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            status_options = ["الكل"] + sorted(students_df["حالة الاشتراك"].dropna().unique().tolist()) if "حالة الاشتراك" in students_df.columns else ["الكل"]
            sel_status = st.selectbox("حالة الاشتراك", status_options)
        with fc2:
            teacher_options = ["الكل"] + sorted(students_df["اسم المحفظ/ة"].dropna().unique().tolist()) if "اسم المحفظ/ة" in students_df.columns else ["الكل"]
            sel_teacher = st.selectbox("المحفظ/ة", teacher_options)
        with fc3:
            cat_options = ["الكل"] + sorted(students_df["الفئة"].dropna().unique().tolist()) if "الفئة" in students_df.columns else ["الكل"]
            sel_cat = st.selectbox("الفئة", cat_options)
        with fc4:
            sub_options = ["الكل"] + sorted(students_df["نظام الاشتراك"].dropna().unique().tolist()) if "نظام الاشتراك" in students_df.columns else ["الكل"]
            sel_sub = st.selectbox("نظام الدراسة", sub_options)

        filtered = students_df.copy()
        if sel_status != "الكل" and "حالة الاشتراك" in filtered.columns:
            filtered = filtered[filtered["حالة الاشتراك"].str.contains(sel_status, na=False)]
        if sel_teacher != "الكل" and "اسم المحفظ/ة" in filtered.columns:
            filtered = filtered[filtered["اسم المحفظ/ة"].str.strip() == sel_teacher]
        if sel_cat != "الكل" and "الفئة" in filtered.columns:
            filtered = filtered[filtered["الفئة"].str.strip() == sel_cat]
        if sel_sub != "الكل" and "نظام الاشتراك" in filtered.columns:
            filtered = filtered[filtered["نظام الاشتراك"].str.contains(sel_sub, na=False)]

        st.markdown(f"""
        <div class="insight-box insight-teal" style="margin-bottom:1rem;">
            <b>📊 نتائج التصفية:</b> {len(filtered)} طالب &nbsp;|&nbsp; إجمالي الاشتراكات:
            <b>{fmt_currency(pd.to_numeric(filtered.get('قيمة الاشتراك الشهري', pd.Series(dtype=float)), errors='coerce').fillna(0).sum())}</b>
        </div>
        """, unsafe_allow_html=True)

        display_cols = [c for c in [
            "كود الطالب", "الاسم بالكامل", "الفئة", "العمر", "النوع",
            "اسم المحفظ/ة", "المستوى", "السورة الحالية",
            "نظام الاشتراك", "قيمة الاشتراك الشهري",
            "عدد الحصص الأسبوعية", "مدة الحصة (دقائق)",
            "حالة الاشتراك", "تاريخ آخر تجديد", "ملاحظات"
        ] if c in filtered.columns]

        display_table(filtered[display_cols], title=f"قائمة الطلاب ({len(filtered)} سجل)",
                      download_name="الطلاب.csv", max_height="520px")

        st.markdown("---")
        st.markdown(section_header("بطاقة الطالب", "اختر طالباً لعرض ملفه الكامل", "🪪"), unsafe_allow_html=True)

        student_names  = students_df["الاسم بالكامل"].dropna().tolist() if "الاسم بالكامل" in students_df.columns else []
        student_codes  = students_df["كود الطالب"].dropna().tolist()    if "كود الطالب"    in students_df.columns else []
        student_labels = [f"{c} — {n}" for c, n in zip(student_codes, student_names)]

        if student_labels:
            sel_student_label = st.selectbox("اختر الطالب", ["— اختر —"] + student_labels)
            if sel_student_label != "— اختر —":
                sel_code = sel_student_label.split(" — ")[0].strip()
                s_row = students_df[students_df.get("كود الطالب", pd.Series(dtype=str)).astype(str).str.strip() == sel_code]
                if not s_row.empty:
                    r          = s_row.iloc[0]
                    status_val = str(r.get("حالة الاشتراك", ""))
                    badge_class = "badge-active" if "نشط" in status_val else ("badge-frozen" if "تجميد" in status_val else "badge-inactive")

                    p1, p2, p3 = st.columns(3)
                    with p1:
                        st.markdown(f"""
                        <div class="salary-card">
                            <h4 style="color:{T.PRIMARY_DARK};margin:0 0 0.8rem;">{r.get('الاسم بالكامل','—')}</h4>
                            <div style="direction:rtl;line-height:2;font-size:0.9rem;">
                                🆔 <b>الكود:</b> {r.get('كود الطالب','—')}<br>
                                👤 <b>الفئة:</b> {r.get('الفئة','—')}<br>
                                🎂 <b>العمر:</b> {r.get('العمر','—')} سنة<br>
                                📍 <b>المنطقة:</b> {r.get('العنوان / المنطقة','—')}<br>
                                📞 <b>الهاتف:</b> {r.get('رقم الهاتف','—')}<br>
                                👨‍👩‍👦 <b>ولي الأمر:</b> {r.get('اسم ولي الأمر','—')} ({r.get('صلة القرابة','—')})
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with p2:
                        st.markdown(f"""
                        <div class="salary-card">
                            <h4 style="color:{T.PRIMARY_DARK};margin:0 0 0.8rem;">📚 بيانات الدراسة</h4>
                            <div style="direction:rtl;line-height:2;font-size:0.9rem;">
                                👩‍🏫 <b>المحفظ/ة:</b> {r.get('اسم المحفظ/ة','—')}<br>
                                📖 <b>السورة الحالية:</b> {r.get('السورة الحالية','—')}<br>
                                📏 <b>مقدار الحفظ:</b> {r.get('مقدار الحفظ الشهري','—')}<br>
                                🎯 <b>المستوى:</b> {r.get('المستوى','—')}<br>
                                💻 <b>نظام الدراسة:</b> {r.get('نظام الاشتراك','—')}<br>
                                ⏱️ <b>مدة الحصة:</b> {r.get('مدة الحصة (دقائق)','—')} دقيقة
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with p3:
                        st.markdown(f"""
                        <div class="salary-card">
                            <h4 style="color:{T.PRIMARY_DARK};margin:0 0 0.8rem;">💰 بيانات الاشتراك</h4>
                            <div style="direction:rtl;line-height:2;font-size:0.9rem;">
                                <span class="{badge_class}">{status_val}</span><br><br>
                                💵 <b>قيمة الاشتراك:</b> {fmt_currency(r.get('قيمة الاشتراك الشهري', 0))}<br>
                                📅 <b>تاريخ البداية:</b> {r.get('تاريخ بداية الاشتراك','—')}<br>
                                🔄 <b>آخر تجديد:</b> {r.get('تاريخ آخر تجديد','—')}<br>
                                📌 <b>مصدر الاشتراك:</b> {r.get('مصدر الاشتراك','—')}<br>
                                📝 <b>ملاحظات:</b> {r.get('ملاحظات','—')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    sessions = get_session_dates(r)
                    if sessions:
                        st.markdown(f"**📅 حصص الشهر الحالي ({len(sessions)} حصة):**")
                        display_table(pd.DataFrame(sessions), max_height="300px")

# ============================================================
# TAB 3 — المحفظون
# ============================================================
with tab_teachers:
    st.markdown(section_header("بيانات المحفظين", "عرض وتحليل بيانات جميع المحفظين", "👩‍🏫"), unsafe_allow_html=True)

    if teachers_df.empty:
        st.error("❌ لم يتم تحميل بيانات المحفظين.")
    else:
        total_teachers  = len(teachers_df)
        female_teachers = teachers_df["النوع"].str.contains("أنثى|انثى", na=False).sum() if "النوع" in teachers_df.columns else 0
        male_teachers   = teachers_df["النوع"].str.contains("ذكر", na=False).sum()        if "النوع" in teachers_df.columns else 0
        licensed        = teachers_df["المؤهل/الإجازة"].str.contains("مجاز|إجازة", na=False).sum() if "المؤهل/الإجازة" in teachers_df.columns else 0

        tc1, tc2, tc3, tc4 = st.columns(4)
        with tc1: st.markdown(kpi_card("👩‍🏫", fmt_num(total_teachers),  "إجمالي المحفظين", "teal"),     unsafe_allow_html=True)
        with tc2: st.markdown(kpi_card("👩",   fmt_num(female_teachers), "محفظات",          "rose"),     unsafe_allow_html=True)
        with tc3: st.markdown(kpi_card("👨",   fmt_num(male_teachers),   "محفظون",          "sapphire"), unsafe_allow_html=True)
        with tc4: st.markdown(kpi_card("📜",   fmt_num(licensed),        "حاملو إجازة",     "gold"),     unsafe_allow_html=True)

        st.markdown("---")

        display_cols_t = [c for c in [
            "ID", "الاسم", "النوع", "المحافظة", "المؤهل/الإجازة", "سنوات الخبرة",
            "الفئة التي يدرّسها", "نظام العمل", "سعر الساعة",
            "التوقيت", "حالة التعاقد", "مميز في", "ملاحظات"
        ] if c in teachers_df.columns]
        display_table(teachers_df[display_cols_t], title="قائمة المحفظين", download_name="المحفظون.csv")

        st.markdown("---")
        st.markdown(section_header("ملف المحفظ/ة", "اختر محفظاً لعرض تفاصيله وعبء عمله", "🪪"), unsafe_allow_html=True)

        teacher_names_list = teachers_df["الاسم"].dropna().tolist() if "الاسم" in teachers_df.columns else []
        sel_t = st.selectbox("اختر المحفظ/ة", ["— اختر —"] + teacher_names_list, key="teacher_profile_sel")

        if sel_t != "— اختر —":
            t_row = teachers_df[teachers_df["الاسم"].astype(str).str.strip() == sel_t.strip()]
            if not t_row.empty:
                tr             = t_row.iloc[0]
                hours, salary  = compute_teacher_salary(sel_t, students_df)
                t_students     = students_df[
                    students_df.get("اسم المحفظ/ة", pd.Series(dtype=str)).astype(str).str.strip().str.contains(sel_t.strip(), na=False)
                ] if not students_df.empty else pd.DataFrame()

                active_t  = t_students[t_students.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)].shape[0] if not t_students.empty else 0
                revenue_t = pd.to_numeric(
                    t_students[t_students.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)]
                    .get("قيمة الاشتراك الشهري", pd.Series(dtype=float)), errors="coerce"
                ).fillna(0).sum() if not t_students.empty else 0

                tp1, tp2, tp3, tp4 = st.columns(4)
                with tp1: st.markdown(kpi_card("👨‍🎓", fmt_num(len(t_students)), "إجمالي الطلاب",  "teal"),     unsafe_allow_html=True)
                with tp2: st.markdown(kpi_card("✅",   fmt_num(active_t),        "طلاب نشطون",     "emerald"),  unsafe_allow_html=True)
                with tp3: st.markdown(kpi_card("⏰",   f"{hours:.1f}",           "ساعات الشهر",    "sapphire"), unsafe_allow_html=True)
                with tp4: st.markdown(kpi_card("💰",   fmt_currency(revenue_t),  "إيرادات طلابه",  "gold"),     unsafe_allow_html=True)

                td1, td2 = st.columns(2)
                with td1:
                    st.markdown(f"""
                    <div class="salary-card">
                        <h4 style="color:{T.PRIMARY_DARK};margin:0 0 0.8rem;">👩‍🏫 {tr.get('الاسم','—')}</h4>
                        <div style="direction:rtl;line-height:2;font-size:0.9rem;">
                            🆔 <b>الكود:</b> {tr.get('ID','—')}<br>
                            📍 <b>المحافظة:</b> {tr.get('المحافظة','—')}<br>
                            📜 <b>المؤهل:</b> {tr.get('المؤهل/الإجازة','—')}<br>
                            📆 <b>سنوات الخبرة:</b> {tr.get('سنوات الخبرة','—')}<br>
                            🎯 <b>الفئة:</b> {tr.get('الفئة التي يدرّسها','—')}<br>
                            🕐 <b>التوقيت:</b> {tr.get('التوقيت','—')}<br>
                            ⭐ <b>مميز في:</b> {tr.get('مميز في','—')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with td2:
                    teacher_rate_display = get_teacher_rate(sel_t)
                    salary_with_fee      = round(salary * VODAFONE_CASH_FEE, 2)
                    st.markdown(f"""
                    <div class="salary-card">
                        <h4 style="color:{T.PRIMARY_DARK};margin:0 0 0.8rem;">💰 الراتب التقديري هذا الشهر</h4>
                        <div style="direction:rtl;line-height:2.2;font-size:0.9rem;">
                            ⏱️ <b>إجمالي الساعات:</b> {hours:.2f} ساعة<br>
                            💵 <b>سعر الساعة:</b> {teacher_rate_display:.0f} ج.م<br>
                            <hr style="border-color:rgba(27,107,90,0.2);">
                            💰 <b style="font-size:1.1rem;color:{T.PRIMARY_DARK};">الراتب المستحق: {fmt_currency(salary)}</b><br>
                            📲 <b>إجمالي التحويل (فودافون):</b> {fmt_currency(salary_with_fee)}<br>
                            📊 <b>إيرادات طلابه:</b> {fmt_currency(revenue_t)}<br>
                            📈 <b>هامش الربح:</b> {fmt_currency(revenue_t - salary)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                if not t_students.empty:
                    st.markdown(f"**👨‍🎓 طلاب {sel_t} ({len(t_students)} طالب):**")
                    t_disp_cols = [c for c in ["كود الطالب","الاسم بالكامل","الفئة","المستوى",
                                               "قيمة الاشتراك الشهري","حالة الاشتراك","ملاحظات"]
                                   if c in t_students.columns]
                    display_table(t_students[t_disp_cols], max_height="320px")

        st.markdown("---")
        st.markdown(section_header("تحليل فريق المحفظين", "", "📊"), unsafe_allow_html=True)
        ch1, ch2 = st.columns(2)
        with ch1:
            if "المحافظة" in teachers_df.columns:
                gov_counts = teachers_df["المحافظة"].value_counts()
                fig_gov = go.Figure(go.Bar(
                    x=gov_counts.index.tolist(), y=gov_counts.values.tolist(),
                    marker=dict(color=CHART_COLORS[:len(gov_counts)]),
                    text=gov_counts.values.tolist(), textposition="outside",
                ))
                plotly_layout(fig_gov, "المحفظون حسب المحافظة", 320)
                st.plotly_chart(fig_gov, use_container_width=True)
        with ch2:
            if "المؤهل/الإجازة" in teachers_df.columns:
                lic_counts = teachers_df["المؤهل/الإجازة"].value_counts()
                fig_lic = go.Figure(go.Pie(
                    labels=lic_counts.index.tolist(), values=lic_counts.values.tolist(),
                    hole=0.5, marker=dict(colors=CHART_COLORS[:len(lic_counts)]),
                    textinfo="label+percent", textfont=dict(size=10),
                ))
                plotly_layout(fig_lic, "توزيع المؤهلات والإجازات", 320)
                fig_lic.update_layout(showlegend=False)
                st.plotly_chart(fig_lic, use_container_width=True)

# ============================================================
# TAB 4 — الجداول
# ============================================================
with tab_schedule:
    st.markdown(section_header("الجداول الدراسية", "جداول الحصص للطلاب والمحفظين", "📅"), unsafe_allow_html=True)

    sched_tab1, sched_tab2, sched_tab3 = st.tabs([
        "📋 جدول الطالب", "👩‍🏫 جدول المحفظ/ة", "📆 جدول الشهر الكامل",
    ])

    with sched_tab1:
        st.markdown('<div class="insight-box insight-teal"><b>📌 كيفية الاستخدام:</b> أدخل كود الطالب أو جزء من اسمه لعرض جدول حصصه الشهري.</div>', unsafe_allow_html=True)
        sc1, sc2 = st.columns([2, 1])
        with sc1:
            student_input = st.text_input("🔍 كود الطالب أو اسمه", placeholder="مثال: S-00001 أو فيروز", key="sched_student_input")
        with sc2:
            use_month_sheet = st.checkbox("استخدام بيانات شهر 3", value=True)

        if student_input.strip():
            source_df = month_df if (use_month_sheet and not month_df.empty) else students_df
            sched     = get_next_week_schedule(student_input.strip(), source_df)
            if sched.empty:
                st.warning(f"⚠️ لم يتم العثور على طالب بالكود أو الاسم: **{student_input}**")
            else:
                student_name = sched["اسم الطالب"].iloc[0] if "اسم الطالب" in sched.columns else student_input
                teacher_name = sched["المحفظ/ة"].iloc[0]   if "المحفظ/ة"   in sched.columns else "—"
                st.markdown(f'<div class="insight-box insight-success">✅ <b>{student_name}</b> — المحفظ/ة: <b>{teacher_name}</b> &nbsp;|&nbsp; عدد الحصص: <b>{len(sched)}</b></div>', unsafe_allow_html=True)
                display_table(sched, title=f"جدول حصص {student_name}", download_name=f"جدول_{student_name}.csv")
                st.markdown("**📊 توزيع الحصص:**")
                time_fig = go.Figure()
                for i, row_s in sched.iterrows():
                    time_fig.add_trace(go.Scatter(
                        x=[row_s["التاريخ"]], y=[row_s.get("الوقت", "")],
                        mode="markers+text",
                        marker=dict(size=18, color=T.PRIMARY, symbol="circle"),
                        text=[f"حصة {i+1}"], textposition="top center",
                        name=f"حصة {i+1}", showlegend=False,
                    ))
                plotly_layout(time_fig, f"جدول حصص {student_name}", 300)
                st.plotly_chart(time_fig, use_container_width=True)

    with sched_tab2:
        st.markdown('<div class="insight-box insight-gold"><b>📌 كيفية الاستخدام:</b> اختر اسم المحفظ/ة لعرض جدول جميع حصصه/ها مع طلابه/ها هذا الشهر.</div>', unsafe_allow_html=True)
        teacher_names_sched = ["— اختر —"] + (teachers_df["الاسم"].dropna().tolist() if not teachers_df.empty and "الاسم" in teachers_df.columns else [])
        sel_t_sched = st.selectbox("اختر المحفظ/ة", teacher_names_sched, key="sched_teacher_sel")

        if sel_t_sched != "— اختر —":
            source_df2 = month_df if not month_df.empty else students_df
            t_sched    = get_teacher_schedule(sel_t_sched, source_df2)
            if t_sched.empty:
                st.warning(f"⚠️ لا توجد حصص مسجلة للمحفظ/ة: **{sel_t_sched}**")
            else:
                hours_t, salary_t = compute_teacher_salary(sel_t_sched, students_df)
                ts1, ts2, ts3 = st.columns(3)
                with ts1: st.markdown(kpi_card("📋", fmt_num(len(t_sched)), "إجمالي الحصص", "teal"),              unsafe_allow_html=True)
                with ts2: st.markdown(kpi_card("⏰", f"{hours_t:.1f}",      "ساعات العمل",  "sapphire"),          unsafe_allow_html=True)
                with ts3: st.markdown(kpi_card("💰", fmt_currency(salary_t),"الراتب المستحق","gold"),             unsafe_allow_html=True)
                st.markdown("---")
                display_table(t_sched, title=f"جدول حصص {sel_t_sched}", download_name=f"جدول_{sel_t_sched}.csv")
                if "اسم الطالب" in t_sched.columns:
                    sess_per_student = t_sched["اسم الطالب"].value_counts()
                    fig_tss = go.Figure(go.Bar(
                        x=sess_per_student.index.tolist(), y=sess_per_student.values.tolist(),
                        marker=dict(color=T.PRIMARY, line=dict(color=T.PRIMARY_DARK, width=1)),
                        text=sess_per_student.values.tolist(), textposition="outside",
                    ))
                    plotly_layout(fig_tss, f"عدد الحصص لكل طالب — {sel_t_sched}", 320)
                    st.plotly_chart(fig_tss, use_container_width=True)

    with sched_tab3:
        st.markdown(section_header("جدول الشهر الكامل", "جميع الحصص المسجلة لهذا الشهر", "📆"), unsafe_allow_html=True)
        source_month = month_df if not month_df.empty else students_df
        if source_month.empty:
            st.error("❌ لا توجد بيانات لجدول الشهر.")
        else:
            all_month_sessions = []
            for _, row in source_month.iterrows():
                for s in get_session_dates(row):
                    all_month_sessions.append({
                        "كود الطالب":   str(row.get("كود الطالب", "")),
                        "اسم الطالب":   str(row.get("الاسم بالكامل", "")),
                        "المحفظ/ة":     str(row.get("اسم المحفظ/ة", "")),
                        "التاريخ":       s["التاريخ"],
                        "الوقت":         s["الوقت"],
                        "مدة الحصة":    f"{int(pd.to_numeric(row.get('مدة الحصة (دقائق)', 0), errors='coerce') or 0)} دقيقة",
                        "السورة":        str(row.get("السورة الحالية", "")),
                        "نظام الدراسة": str(row.get("نظام الاشتراك", "")),
                    })
            if all_month_sessions:
                month_sched_df      = pd.DataFrame(all_month_sessions)
                month_teacher_filter = st.selectbox(
                    "تصفية حسب المحفظ/ة",
                    ["الكل"] + sorted(month_sched_df["المحفظ/ة"].dropna().unique().tolist()),
                    key="month_sched_filter"
                )
                if month_teacher_filter != "الكل":
                    month_sched_df = month_sched_df[month_sched_df["المحفظ/ة"].str.contains(month_teacher_filter, na=False)]
                st.markdown(f'<div class="insight-box insight-teal">📊 <b>إجمالي الحصص المعروضة:</b> {len(month_sched_df)} حصة</div>', unsafe_allow_html=True)
                display_table(month_sched_df, title="جدول الشهر الكامل", download_name="جدول_الشهر_الكامل.csv", max_height="560px")
                if "التاريخ" in month_sched_df.columns:
                    day_counts = month_sched_df["التاريخ"].value_counts().sort_index()
                    if not day_counts.empty:
                        fig_days = go.Figure(go.Bar(
                            x=day_counts.index.tolist(), y=day_counts.values.tolist(),
                            marker=dict(color=T.GOLD, line=dict(color=T.GOLD_DARK, width=1)),
                            text=day_counts.values.tolist(), textposition="outside",
                        ))
                        plotly_layout(fig_days, "عدد الحصص لكل يوم في الشهر", 340)
                        st.plotly_chart(fig_days, use_container_width=True)

# ============================================================
# TAB 5 — المالية
# ============================================================
with tab_finance:
    st.markdown(section_header("التقرير المالي الشهري", "الإيرادات والرواتب وصافي الربح — محاسبة دقيقة", "💰"), unsafe_allow_html=True)

    fin_df        = filtered_students_df.copy() if not filtered_students_df.empty else students_df.copy()
    total_rev     = compute_center_revenue(fin_df)
    total_sal     = compute_total_salaries(fin_df, teachers_df)
    net_prof      = total_rev - total_sal
    profit_margin = (net_prof / total_rev * 100) if total_rev > 0 else 0

    fk1, fk2, fk3, fk4 = st.columns(4)
    with fk1: st.markdown(kpi_card("💵", fmt_currency(total_rev),  "إجمالي الإيرادات", "gold"),    unsafe_allow_html=True)
    with fk2: st.markdown(kpi_card("💸", fmt_currency(total_sal),  "إجمالي الرواتب",   "amber"),   unsafe_allow_html=True)
    with fk3: st.markdown(kpi_card("📈", fmt_currency(net_prof),   "صافي الربح",
                                   "emerald" if net_prof >= 0 else "crimson"), unsafe_allow_html=True)
    with fk4: st.markdown(kpi_card("📊", f"{profit_margin:.1f}%", "هامش الربح",        "sapphire"),unsafe_allow_html=True)

    st.markdown("---")

    fg1, fg2 = st.columns(2)
    with fg1:
        if total_rev > 0:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=net_prof,
                delta={"reference": total_rev * 0.5, "valueformat": ".0f"},
                title={"text": "صافي الربح الشهري (ج.م)", "font": {"size": 14, "family": T.FONT_FAMILY}},
                gauge={
                    "axis": {"range": [0, max(total_rev, 1)], "tickwidth": 1},
                    "bar":  {"color": T.PRIMARY},
                    "steps": [
                        {"range": [0,               total_rev * 0.3], "color": "rgba(239,68,68,0.2)"},
                        {"range": [total_rev * 0.3, total_rev * 0.6], "color": "rgba(245,158,11,0.2)"},
                        {"range": [total_rev * 0.6, total_rev],       "color": "rgba(16,185,129,0.2)"},
                    ],
                    "threshold": {"line": {"color": T.GOLD, "width": 4}, "thickness": 0.75, "value": total_rev * 0.5},
                },
                number={"suffix": " ج.م", "font": {"size": 22, "family": T.FONT_FAMILY}},
            ))
            fig_gauge.update_layout(height=320, paper_bgcolor="rgba(247,251,249,0.9)", font=dict(family=T.FONT_FAMILY))
            st.plotly_chart(fig_gauge, use_container_width=True)

    with fg2:
        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["الإيرادات", "الرواتب", "صافي الربح"],
            y=[total_rev, -total_sal, 0],
            connector={"line": {"color": T.PRIMARY_LIGHT}},
            decreasing={"marker": {"color": T.ACCENT_CRIMSON}},
            increasing={"marker": {"color": T.ACCENT_EMERALD}},
            totals={"marker":    {"color": T.GOLD}},
            text=[fmt_currency(total_rev), f"-{fmt_currency(total_sal)}", fmt_currency(net_prof)],
            textposition="outside",
        ))
        plotly_layout(fig_wf, "تدفق الإيرادات والمصروفات", 320)
        st.plotly_chart(fig_wf, use_container_width=True)

    st.markdown("---")
    st.markdown(section_header("كشف رواتب المحفظين", "الحساب: (الحصص الشهرية − الملغية) × مدة الحصة × سعر الساعة", "📋"), unsafe_allow_html=True)
    st.markdown(f"""
    <div class="insight-box insight-gold">
        <b>📐 معادلة الراتب:</b>
        الحصص الفعلية = إجمالي الحصص الشهرية − الحصص الملغية &nbsp;|&nbsp;
        الراتب = الحصص الفعلية × مدة الحصة (ساعة) × سعر الساعة &nbsp;|&nbsp;
        📲 إجمالي التحويل = الراتب × 1.01 (رسوم فودافون كاش)
    </div>
    """, unsafe_allow_html=True)

    if not teachers_df.empty and "الاسم" in teachers_df.columns:
        salary_records = []
        for _, t in teachers_df.iterrows():
            t_name = str(t.get("الاسم", "")).strip()
            if not t_name:
                continue
            rate                        = get_teacher_rate(t_name)
            hours, salary, _, cost_with_fee = compute_teacher_salary_new(t_name, fin_df)

            t_stu     = fin_df[fin_df.get("اسم المحفظ/ة", pd.Series(dtype=str)).astype(str).str.strip() == t_name] if not fin_df.empty else pd.DataFrame()
            t_active  = t_stu[t_stu.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)].shape[0] if not t_stu.empty else 0
            t_revenue = pd.to_numeric(
                t_stu[t_stu.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)]
                .get("قيمة الاشتراك الشهري", pd.Series(dtype=float)), errors="coerce"
            ).fillna(0).sum() if not t_stu.empty else 0

            salary_records.append({
                "الكود":                          str(t.get("ID", "—")),
                "اسم المحفظ/ة":                   t_name,
                "سعر الساعة":                     f"{rate:.0f} ج.م",
                "عدد الطلاب النشطين":             t_active,
                "ساعات العمل الفعلية":            f"{hours:.2f}",
                "الراتب المستحق":                 salary,
                "إجمالي التحويل (فودافون)":       cost_with_fee,
                "إيرادات طلابه":                  t_revenue,
                "هامش الربح":                     round(t_revenue - salary, 2),
            })

        if salary_records:
            sal_display = pd.DataFrame(salary_records).copy()
            sal_display["الراتب المستحق"]           = sal_display["الراتب المستحق"].apply(lambda x: f"{x:,.0f} ج.م")
            sal_display["إجمالي التحويل (فودافون)"] = sal_display["إجمالي التحويل (فودافون)"].apply(lambda x: f"{x:,.0f} ج.م")
            sal_display["إيرادات طلابه"]            = sal_display["إيرادات طلابه"].apply(lambda x: f"{x:,.0f} ج.م")
            sal_display["هامش الربح"]               = sal_display["هامش الربح"].apply(lambda x: f"{x:,.0f} ج.م")

            total_hours_all = sum(float(r["ساعات العمل الفعلية"]) for r in salary_records)
            total_sal_all   = sum(r["الراتب المستحق"]             for r in salary_records)
            total_fee_all   = sum(r["إجمالي التحويل (فودافون)"]   for r in salary_records)

            st.markdown(f"""
            <div class="insight-box insight-teal">
                ⏱️ <b>إجمالي ساعات العمل:</b> {total_hours_all:.2f} ساعة &nbsp;|&nbsp;
                💸 <b>إجمالي الرواتب:</b> {fmt_currency(total_sal_all)} &nbsp;|&nbsp;
                📲 <b>إجمالي التحويلات (مع فودافون):</b> {fmt_currency(total_fee_all)} &nbsp;|&nbsp;
                📈 <b>صافي الربح:</b> {fmt_currency(total_rev - total_sal_all)}
            </div>
            """, unsafe_allow_html=True)

            display_table(sal_display, title="كشف الرواتب الشهري", download_name="كشف_الرواتب.csv")

            fig_sal = go.Figure()
            fig_sal.add_trace(go.Bar(
                x=[r["اسم المحفظ/ة"] for r in salary_records],
                y=[r["الراتب المستحق"] for r in salary_records],
                name="الراتب", marker=dict(color=T.PRIMARY),
                text=[fmt_currency(r["الراتب المستحق"]) for r in salary_records],
                textposition="outside",
            ))
            fig_sal.add_trace(go.Bar(
                x=[r["اسم المحفظ/ة"] for r in salary_records],
                y=[r["إيرادات طلابه"] for r in salary_records],
                name="الإيرادات", marker=dict(color=T.GOLD),
                text=[fmt_currency(r["إيرادات طلابه"]) for r in salary_records],
                textposition="outside",
            ))
            plotly_layout(fig_sal, "الراتب مقابل الإيرادات لكل محفظ/ة (ج.م)", 380)
            fig_sal.update_layout(barmode="group")
            st.plotly_chart(fig_sal, use_container_width=True)

    st.markdown("---")
    st.markdown(section_header("تفصيل راتب المحفظ/ة", "اختر المحفظ/ة لعرض حساب الراتب بالتفصيل", "🔬"), unsafe_allow_html=True)

    drill_names = ["— اختر —"] + (teachers_df["الاسم"].dropna().tolist() if not teachers_df.empty and "الاسم" in teachers_df.columns else [])
    sel_drill   = st.selectbox("اختر المحفظ/ة للتفصيل", drill_names, key="fin_drill_sel")

    if sel_drill != "— اختر —":
        rate_d                              = get_teacher_rate(sel_drill)
        hours_d, salary_d, breakdown_df, cost_with_fee_d = compute_teacher_salary_new(sel_drill, fin_df)
        fee_amount_d                        = round(cost_with_fee_d - salary_d, 2)

        d1, d2, d3, d4 = st.columns(4)
        with d1: st.markdown(kpi_card("⏰", f"{hours_d:.2f}",           "ساعات العمل الفعلية",        "sapphire"), unsafe_allow_html=True)
        with d2: st.markdown(kpi_card("💵", f"{rate_d:.0f} ج.م",        "سعر الساعة",                 "gold"),     unsafe_allow_html=True)
        with d3: st.markdown(kpi_card("💰", fmt_currency(salary_d),     "الراتب المستحق",              "emerald"),  unsafe_allow_html=True)
        with d4: st.markdown(kpi_card("📲", fmt_currency(cost_with_fee_d),"إجمالي التحويل (فودافون)", "amber"),    unsafe_allow_html=True)

        if not breakdown_df.empty:
            st.markdown(f"""
            <div class="insight-box insight-gold" style="margin-top:1rem;">
                <b>📐 تفصيل الحساب لـ {sel_drill}:</b><br>
                لكل طالب: <b>الحصص الفعلية × مدة الحصة (ساعة) × {rate_d:.0f} ج.م</b><br>
                💳 <b>رسوم فودافون كاش (1%):</b> {fmt_currency(fee_amount_d)}
                &nbsp;|&nbsp;
                📲 <b>إجمالي التحويل:</b> {fmt_currency(cost_with_fee_d)}
            </div>
            """, unsafe_allow_html=True)
            display_table(breakdown_df, title=f"تفصيل راتب {sel_drill}", download_name=f"راتب_{sel_drill}.csv")

    st.markdown("---")
    st.markdown(section_header("مستحقات الطلاب", "ما يجب أن يدفعه كل طالب نشط هذا الشهر", "🧾"), unsafe_allow_html=True)

    active_fin = fin_df[fin_df.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False)].copy() if not fin_df.empty else pd.DataFrame()

    if not active_fin.empty:
        pay_rows = []
        for _, row in active_fin.iterrows():
            calc    = compute_student_teacher_cost(row)
            sub_val = pd.to_numeric(row.get("قيمة الاشتراك الشهري", 0), errors="coerce") or 0
            pay_rows.append({
                "كود الطالب":       str(row.get("كود الطالب", "—")),
                "اسم الطالب":       str(row.get("الاسم بالكامل", "—")),
                "المحفظ/ة":         str(row.get("اسم المحفظ/ة", "—")),
                "إجمالي الحصص":     calc["total_sessions"],
                "الحصص الملغية":    calc["cancelled"],
                "الحصص الفعلية":    calc["net_sessions"],
                "مدة الحصة (ساعة)": calc["duration_hr"],
                "تكلفة المحفظ":     f"{calc['cost']:,.0f} ج.م",
                "اشتراك الطالب":    f"{sub_val:,.0f} ج.م",
                "هامش الطالب":      f"{sub_val - calc['cost']:,.0f} ج.م",
                "تاريخ آخر تجديد":  str(row.get("تاريخ آخر تجديد", "—")),
            })
        display_table(pd.DataFrame(pay_rows), title="مستحقات الطلاب النشطين", download_name="مستحقات_الطلاب.csv")

# ============================================================
# TAB 6 — البحث والأتمتة
# ============================================================
with tab_search:
    st.markdown(section_header("البحث والأتمتة", "أدوات البحث السريع وتوليد التقارير الآلية", "🔍"), unsafe_allow_html=True)

    auto_tab1, auto_tab2, auto_tab3, auto_tab4 = st.tabs([
        "🔍 بحث سريع", "📅 توليد الجدول", "💰 حساب الراتب", "📊 تقرير شامل",
    ])

    # ── Quick Search ──────────────────────────────────────────────────────────
    with auto_tab1:
        st.markdown('<div class="insight-box insight-teal"><b>🔍 البحث الموحد:</b> ابحث بكود الطالب أو المحفظ أو الاسم أو رقم الهاتف في جميع البيانات.</div>', unsafe_allow_html=True)
        search_query = st.text_input("🔎 أدخل كلمة البحث", placeholder="مثال: S-00001 أو سارة أو 01276...", key="global_search")

        if search_query.strip():
            q            = search_query.strip()
            results_list = []
            for df_src, label in [(students_df, "الطلاب"), (teachers_df, "المحفظون")]:
                if not df_src.empty:
                    for col in df_src.columns:
                        try:
                            mask = df_src[col].astype(str).str.contains(q, case=False, na=False)
                            if mask.any():
                                matched = df_src[mask].copy()
                                matched["مصدر البحث"] = f"{label} — عمود: {col}"
                                results_list.append(matched)
                        except Exception:
                            pass
            if results_list:
                combined_results = pd.concat(results_list, ignore_index=True).drop_duplicates()
                st.success(f"✅ تم العثور على **{len(combined_results)}** نتيجة لـ: **{q}**")
                display_table(combined_results, title="نتائج البحث",
                              download_name=f"بحث_{q}.csv", max_height="480px")
            else:
                st.warning(f"⚠️ لم يتم العثور على نتائج لـ: **{q}**")

    # ── Schedule Generator ────────────────────────────────────────────────────
    with auto_tab2:
        st.markdown('<div class="insight-box insight-gold"><b>📅 مولّد الجداول:</b> أدخل كود الطالب أو المحفظ لتوليد جدول الأسبوع أو الشهر القادم تلقائياً.</div>', unsafe_allow_html=True)

        gen_col1, gen_col2 = st.columns(2)

        with gen_col1:
            st.markdown("#### 👨‍🎓 جدول طالب")
            gen_student = st.text_input("كود الطالب أو اسمه", key="gen_student", placeholder="S-00001")
            if st.button("🗓️ توليد جدول الطالب", key="btn_gen_student"):
                if gen_student.strip():
                    src          = month_df if not month_df.empty else students_df
                    result_sched = get_next_week_schedule(gen_student.strip(), src)
                    if result_sched.empty:
                        st.error(f"❌ لم يتم العثور على: {gen_student}")
                    else:
                        st.success(f"✅ تم توليد الجدول — {len(result_sched)} حصة")
                        display_table(result_sched, download_name=f"جدول_{gen_student}.csv")
                        st.markdown(f"""
                        <div class="salary-card">
                            <h4 style="color:{T.PRIMARY_DARK};">📋 ملخص الجدول</h4>
                            <div style="direction:rtl;line-height:2;font-size:0.9rem;">
                                👨‍🎓 <b>الطالب:</b> {result_sched['اسم الطالب'].iloc[0]}<br>
                                👩‍🏫 <b>المحفظ/ة:</b> {result_sched['المحفظ/ة'].iloc[0]}<br>
                                📚 <b>السورة:</b> {result_sched['السورة الحالية'].iloc[0]}<br>
                                📊 <b>عدد الحصص:</b> {len(result_sched)}<br>
                                ⏱️ <b>مدة الحصة:</b> {result_sched['مدة الحصة'].iloc[0]}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        with gen_col2:
            st.markdown("#### 👩‍🏫 جدول محفظ/ة")
            teacher_names_gen = ["— اختر —"] + (
                teachers_df["الاسم"].dropna().tolist()
                if not teachers_df.empty and "الاسم" in teachers_df.columns else []
            )
            gen_teacher = st.selectbox("اختر المحفظ/ة", teacher_names_gen, key="gen_teacher_sel")
            if st.button("🗓️ توليد جدول المحفظ/ة", key="btn_gen_teacher"):
                if gen_teacher != "— اختر —":
                    src2     = month_df if not month_df.empty else students_df
                    t_result = get_teacher_schedule(gen_teacher, src2)
                    if t_result.empty:
                        st.error(f"❌ لا توجد حصص للمحفظ/ة: {gen_teacher}")
                    else:
                        hours_g, salary_g = compute_teacher_salary(gen_teacher, students_df)
                        st.success(f"✅ تم توليد الجدول — {len(t_result)} حصة | {hours_g:.1f} ساعة | {fmt_currency(salary_g)}")
                        display_table(t_result, download_name=f"جدول_{gen_teacher}.csv")

    # ── Salary Calculator ─────────────────────────────────────────────────────
    with auto_tab3:
        st.markdown('<div class="insight-box insight-teal"><b>💰 حاسبة الرواتب:</b> احسب راتب أي محفظ/ة بناءً على ساعات العمل الفعلية المسجلة.</div>', unsafe_allow_html=True)

        sc_col1, sc_col2 = st.columns(2)

        with sc_col1:
            teacher_names_sal = ["— اختر —"] + (
                teachers_df["الاسم"].dropna().tolist()
                if not teachers_df.empty and "الاسم" in teachers_df.columns else []
            )
            sel_sal_teacher = st.selectbox("اختر المحفظ/ة", teacher_names_sal, key="sal_teacher_sel")
            custom_rate     = st.number_input("سعر الساعة (ج.م)", min_value=1, value=HOURLY_RATE, step=5, key="custom_rate")

            if st.button("💰 احسب الراتب", key="btn_calc_salary"):
                if sel_sal_teacher != "— اختر —":
                    hours_c, _      = compute_teacher_salary(sel_sal_teacher, students_df, rate=custom_rate)
                    salary_c        = round(hours_c * custom_rate, 2)
                    salary_c_w_fee  = round(salary_c * VODAFONE_CASH_FEE, 2)
                    fee_c           = round(salary_c_w_fee - salary_c, 2)

                    st.markdown(f"""
                    <div class="salary-card">
                        <h3 style="color:{T.PRIMARY_DARK};text-align:center;margin-bottom:1rem;">
                            💰 كشف راتب: {sel_sal_teacher}
                        </h3>
                        <div style="direction:rtl;line-height:2.5;font-size:1rem;text-align:center;">
                            ⏰ <b>إجمالي ساعات العمل:</b>
                            <span style="color:{T.PRIMARY};font-size:1.3rem;font-weight:800;">{hours_c:.2f} ساعة</span><br>
                            💵 <b>سعر الساعة:</b>
                            <span style="color:{T.GOLD};font-size:1.1rem;font-weight:700;">{custom_rate} ج.م</span><br>
                            <hr style="border-color:rgba(27,107,90,0.3);margin:0.5rem 0;">
                            💰 <b>الراتب المستحق:</b>
                            <span style="font-size:1.4rem;font-weight:900;color:{T.PRIMARY_DARK};">{fmt_currency(salary_c)}</span><br>
                            💳 <b>رسوم فودافون كاش (1%):</b>
                            <span style="color:{T.ACCENT_AMBER};font-weight:700;">{fmt_currency(fee_c)}</span><br>
                            📲 <b>إجمالي التحويل:</b>
                            <span style="font-size:1.3rem;font-weight:900;color:{T.ACCENT_AMBER};">{fmt_currency(salary_c_w_fee)}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        with sc_col2:
            st.markdown("#### 📊 مقارنة رواتب جميع المحفظين")
            if not teachers_df.empty and "الاسم" in teachers_df.columns:
                compare_rate = st.number_input("سعر الساعة للمقارنة (ج.م)", min_value=1,
                                               value=HOURLY_RATE, step=5, key="compare_rate")
                if st.button("📊 عرض مقارنة الرواتب", key="btn_compare_sal"):
                    compare_records = []
                    for _, t in teachers_df.iterrows():
                        t_name = str(t.get("الاسم", "")).strip()
                        if not t_name:
                            continue
                        h, _ = compute_teacher_salary(t_name, students_df, rate=compare_rate)
                        s    = round(h * compare_rate, 2)
                        compare_records.append({
                            "المحفظ/ة":                    t_name,
                            "الساعات":                     h,
                            "الراتب":                      s,
                            "إجمالي التحويل (فودافون)":    round(s * VODAFONE_CASH_FEE, 2),
                        })
                    if compare_records:
                        comp_df = pd.DataFrame(compare_records)
                        fig_comp = go.Figure()
                        fig_comp.add_trace(go.Bar(
                            x=comp_df["المحفظ/ة"].tolist(),
                            y=comp_df["الراتب"].tolist(),
                            name="الراتب",
                            marker=dict(color=T.PRIMARY),
                            text=[fmt_currency(v) for v in comp_df["الراتب"].tolist()],
                            textposition="outside",
                        ))
                        fig_comp.add_trace(go.Bar(
                            x=comp_df["المحفظ/ة"].tolist(),
                            y=comp_df["إجمالي التحويل (فودافون)"].tolist(),
                            name="مع فودافون",
                            marker=dict(color=T.ACCENT_AMBER),
                            text=[fmt_currency(v) for v in comp_df["إجمالي التحويل (فودافون)"].tolist()],
                            textposition="outside",
                        ))
                        plotly_layout(fig_comp, f"مقارنة الرواتب (سعر الساعة: {compare_rate} ج.م)", 360)
                        fig_comp.update_layout(barmode="group")
                        st.plotly_chart(fig_comp, use_container_width=True)

                        comp_display = comp_df.copy()
                        comp_display["الراتب"]                   = comp_display["الراتب"].apply(lambda x: f"{x:,.0f} ج.م")
                        comp_display["إجمالي التحويل (فودافون)"] = comp_display["إجمالي التحويل (فودافون)"].apply(lambda x: f"{x:,.0f} ج.م")
                        display_table(comp_display, download_name="مقارنة_الرواتب.csv")

    # ── Full Report Generator ─────────────────────────────────────────────────
    with auto_tab4:
        st.markdown(f"""
        <div class="insight-box insight-gold">
            <b>📊 التقرير الشهري الشامل:</b> اضغط الزر لتوليد تقرير كامل قابل للتحميل يشمل
            الطلاب والرواتب والإيرادات والجداول.
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 توليد التقرير الشهري الشامل", key="btn_full_report"):
            with st.spinner("⏳ جاري إعداد التقرير..."):

                # ── Section 1: Student Summary ───────────────────────────────
                st.markdown(section_header("1️⃣ ملخص الطلاب", "", "👨‍🎓"), unsafe_allow_html=True)
                if not students_df.empty:
                    rk1, rk2, rk3, rk4 = st.columns(4)
                    with rk1: st.markdown(kpi_card("👨‍🎓", fmt_num(len(students_df)), "إجمالي الطلاب", "teal"), unsafe_allow_html=True)
                    with rk2:
                        a_c = students_df.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("نشط", na=False).sum()
                        st.markdown(kpi_card("✅", fmt_num(a_c), "نشطون", "emerald"), unsafe_allow_html=True)
                    with rk3:
                        f_c = students_df.get("حالة الاشتراك", pd.Series(dtype=str)).str.contains("تجميد", na=False).sum()
                        st.markdown(kpi_card("⏸️", fmt_num(f_c), "مجمّدون", "sapphire"), unsafe_allow_html=True)
                    with rk4:
                        st.markdown(kpi_card("💰", fmt_currency(total_revenue), "الإيرادات", "gold"), unsafe_allow_html=True)

                # ── Section 2: Salary Report ─────────────────────────────────
                st.markdown("---")
                st.markdown(section_header("2️⃣ كشف الرواتب", "", "💸"), unsafe_allow_html=True)
                if not teachers_df.empty and "الاسم" in teachers_df.columns:
                    report_sal_records = []
                    for _, t in teachers_df.iterrows():
                        t_name = str(t.get("الاسم", "")).strip()
                        if not t_name:
                            continue
                        h, s = compute_teacher_salary(t_name, students_df)
                        report_sal_records.append({
                            "المحفظ/ة":                    t_name,
                            "ساعات العمل":                 f"{h:.2f}",
                            "الراتب المستحق":              f"{s:,.0f} ج.م",
                            "إجمالي التحويل (فودافون)":    f"{round(s * VODAFONE_CASH_FEE, 2):,.0f} ج.م",
                        })
                    if report_sal_records:
                        display_table(pd.DataFrame(report_sal_records),
                                      download_name="تقرير_الرواتب_الشهري.csv")

                # ── Section 3: Full Schedule ─────────────────────────────────
                st.markdown("---")
                st.markdown(section_header("3️⃣ الجدول الشهري الكامل", "", "📅"), unsafe_allow_html=True)
                src_r          = month_df if not month_df.empty else students_df
                all_r_sessions = []
                for _, row in src_r.iterrows():
                    for s in get_session_dates(row):
                        all_r_sessions.append({
                            "الطالب":   str(row.get("الاسم بالكامل", "")),
                            "المحفظ/ة": str(row.get("اسم المحفظ/ة", "")),
                            "التاريخ":   s["التاريخ"],
                            "الوقت":     s["الوقت"],
                            "المدة":     f"{int(pd.to_numeric(row.get('مدة الحصة (دقائق)', 0), errors='coerce') or 0)} دقيقة",
                        })
                if all_r_sessions:
                    display_table(pd.DataFrame(all_r_sessions),
                                  download_name="الجدول_الشهري_الكامل.csv", max_height="400px")

                # ── Section 4: Financial Summary ─────────────────────────────
                st.markdown("---")
                st.markdown(section_header("4️⃣ الملخص المالي", "", "💰"), unsafe_allow_html=True)

                total_sal_report = compute_total_salaries(students_df, teachers_df)
                total_fee_report = round(total_sal_report * VODAFONE_CASH_FEE, 2)
                net_prof_report  = total_revenue - total_sal_report
                margin_report    = (net_prof_report / total_revenue * 100) if total_revenue > 0 else 0

                st.markdown(f"""
                <div class="salary-card" style="text-align:center;">
                    <h3 style="color:{T.PRIMARY_DARK};margin-bottom:1.2rem;">📊 الملخص المالي الشهري</h3>
                    <div style="direction:rtl;line-height:3;font-size:1rem;">
                        💵 <b>إجمالي الإيرادات:</b>
                        <span style="color:{T.GOLD};font-size:1.2rem;font-weight:800;">{fmt_currency(total_revenue)}</span><br>
                        💸 <b>إجمالي الرواتب:</b>
                        <span style="color:{T.ACCENT_CRIMSON};font-size:1.2rem;font-weight:800;">{fmt_currency(total_sal_report)}</span><br>
                        📲 <b>إجمالي التحويلات (مع فودافون):</b>
                        <span style="color:{T.ACCENT_AMBER};font-size:1.1rem;font-weight:800;">{fmt_currency(total_fee_report)}</span><br>
                        <hr style="border-color:rgba(27,107,90,0.3);margin:0.5rem auto;width:60%;">
                        📈 <b>صافي الربح:</b>
                        <span style="color:{T.PRIMARY_DARK};font-size:1.5rem;font-weight:900;">{fmt_currency(net_prof_report)}</span><br>
                        📊 <b>هامش الربح:</b>
                        <span style="color:{T.ACCENT_SAPPHIRE};font-size:1.2rem;font-weight:800;">{margin_report:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.success("✅ تم توليد التقرير الشهري الشامل بنجاح!")

# ============================================================
# 🦶 FOOTER
# ============================================================
st.markdown("---")
st.markdown(f"""
<div style="
    text-align: center;
    padding: 1.5rem;
    background: {T.hero_gradient(135)};
    border-radius: {T.BORDER_RADIUS_LARGE};
    margin-top: 2rem;
    box-shadow: {T.SHADOW_MEDIUM};
    direction: rtl;
">
    <div style="color:rgba(255,255,255,0.9);font-size:0.9rem;font-weight:600;line-height:2;">
        🕌 <b style="color:{T.GOLD_LIGHT};">دار روضة القرآن</b>
        &nbsp;|&nbsp; نظام الإدارة المتكامل
        &nbsp;|&nbsp; جميع الحقوق محفوظة © {datetime.now().year}
    </div>
    <div style="color:rgba(255,255,255,0.5);font-size:0.78rem;margin-top:0.3rem;">
        آخر تحديث للبيانات: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Memory cleanup ────────────────────────────────────────────────────────────
gc.collect()
