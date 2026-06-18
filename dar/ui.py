# -*- coding: utf-8 -*-
"""
طبقة الواجهة المشتركة — CSS، تسجيل الدخول، والمكوّنات (مأخوذة من اللوحة الأصلية
ومُكيَّفة لتعمل مع الحزمة الجديدة). RTL بالكامل وبهوية دار روضة القرآن.
"""
from __future__ import annotations
import base64
import hmac

import pandas as pd
import streamlit as st

from .config import T, LOGO_PATH, CHART_COLORS


# ────────────────────────────────────────────────────────────────────────────
# 🖼️ الشعار
# ────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def logo_b64() -> str | None:
    try:
        if LOGO_PATH.exists():
            return base64.b64encode(LOGO_PATH.read_bytes()).decode()
    except Exception:
        return None
    return None


# ────────────────────────────────────────────────────────────────────────────
# 🔢 تنسيق
# ────────────────────────────────────────────────────────────────────────────
def fmt_num(n):
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "0"
    n = float(n)
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{int(n):,}"


def fmt_currency(n):
    if n is None or (isinstance(n, float) and pd.isna(n)) or n == 0:
        return "—"
    return f"{int(float(n)):,} ج.م"


# ────────────────────────────────────────────────────────────────────────────
# 🎨 CSS العام
# ────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700;800;900&family=Tajawal:wght@300;400;500;700;800&display=swap');
    * {{ font-family: {T.FONT_FAMILY}; }}
    #MainMenu, footer {{ visibility: hidden; }}
    .stApp {{
        background: linear-gradient(160deg, #F0F7F5 0%, #E8F4F0 50%, #DFF0EA 100%);
        background-size: 400% 400%; animation: bgPulse 20s ease infinite; direction: rtl;
    }}
    @keyframes bgPulse {{ 0%,100% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} }}
    @keyframes fadeInUp {{ from {{ opacity:0; transform:translateY(30px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes slideDown {{ from {{ opacity:0; transform:translateY(-50px); }} to {{ opacity:1; transform:translateY(0); }} }}
    @keyframes rotate {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    .block-container {{
        padding: 1.5rem 2.5rem; background: rgba(255,255,255,0.97);
        border-radius: {T.BORDER_RADIUS_LARGE}; box-shadow: 0 20px 60px rgba(27,107,90,0.10);
        max-width: 1600px; border: 1px solid rgba(27,107,90,0.12);
    }}
    section[data-testid="stSidebar"] {{ background: {T.gradient('#0A1A16','#0F2E24',180)} !important; direction: rtl; }}
    section[data-testid="stSidebar"] * {{ color: {T.TEXT_LIGHT} !important; }}
    section[data-testid="stSidebar"] label {{ color: {T.GOLD_LIGHT} !important; font-weight: 600 !important; }}
    .stButton > button {{
        background: {T.teal_gradient()}; color: white; border: none;
        border-radius: {T.BORDER_RADIUS}; padding: 10px 22px; font-weight: 700;
        font-size: 0.92rem; transition: all 0.3s ease; box-shadow: {T.SHADOW_SMALL}; width: 100%;
    }}
    .stButton > button:hover {{ transform: translateY(-3px); box-shadow: {T.SHADOW_HOVER}; }}
    div.stDownloadButton > button {{
        background: {T.gold_gradient()} !important; color: white !important; border: none !important;
        border-radius: {T.BORDER_RADIUS} !important; font-weight: 700 !important; width: 100%;
    }}
    .stTextInput input, .stNumberInput input, .stDateInput input,
    .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{ text-align: right !important; direction: rtl !important; }}
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label,
    .stTextArea label, .stMultiSelect label, .stTimeInput label, .stRadio label {{
        color: {T.PRIMARY_DARK} !important; font-weight: 700 !important; direction: rtl; }}
    .main-header {{
        text-align: center; padding: 2.2rem 2rem; background: {T.hero_gradient(135)};
        border-radius: {T.BORDER_RADIUS_LARGE}; margin-bottom: 1.6rem; box-shadow: {T.SHADOW_GLOW};
        position: relative; overflow: hidden; animation: slideDown 0.8s ease-out; direction: rtl;
    }}
    .main-header::before {{
        content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(201,168,76,0.15) 0%, transparent 70%);
        animation: rotate 18s linear infinite;
    }}
    .main-header h1 {{ color: white; font-size: 2rem; font-weight: 900; margin: 0; text-shadow: 2px 2px 8px rgba(0,0,0,0.3); position: relative; z-index: 1; }}
    .main-header p {{ color: rgba(255,255,255,0.92); font-size: 1rem; margin-top: 0.5rem; position: relative; z-index: 1; }}
    .kpi-card {{
        background: {T.teal_gradient(135)}; padding: 1.4rem 1rem; border-radius: {T.BORDER_RADIUS_LARGE};
        box-shadow: 0 10px 30px rgba(27,107,90,0.35); text-align: center; color: white;
        animation: fadeInUp 0.6s ease-out; min-height: 135px; display: flex; flex-direction: column;
        justify-content: center; align-items: center; direction: rtl; transition: all 0.4s ease;
    }}
    .kpi-card:hover {{ transform: translateY(-10px) scale(1.03); box-shadow: 0 22px 55px rgba(27,107,90,0.50); }}
    .kpi-card .kpi-icon  {{ font-size: 2rem; margin-bottom: 0.3rem; }}
    .kpi-card .kpi-value {{ font-size: 1.8rem; font-weight: 900; line-height:1.1; }}
    .kpi-card .kpi-label {{ font-size: 0.8rem; font-weight: 700; opacity: 0.92; margin-top: 0.3rem; }}
    .kpi-card .kpi-sub   {{ font-size: 0.75rem; opacity: 0.8; margin-top: 0.2rem; }}
    .kpi-gold    {{ background: {T.gold_gradient(135)}; box-shadow: 0 10px 30px rgba(201,168,76,0.35); }}
    .kpi-emerald {{ background: linear-gradient(135deg,#059669,#10B981); }}
    .kpi-amber   {{ background: linear-gradient(135deg,#D97706,#F59E0B); }}
    .kpi-crimson {{ background: linear-gradient(135deg,#DC2626,#EF4444); }}
    .kpi-sapphire{{ background: linear-gradient(135deg,#1D4ED8,#3B82F6); }}
    .kpi-violet  {{ background: linear-gradient(135deg,#6D28D9,#8B5CF6); }}
    .kpi-teal    {{ background: linear-gradient(135deg,#0D9488,#14B8A6); }}
    .kpi-rose    {{ background: linear-gradient(135deg,#BE185D,#F43F5E); }}
    .section-header {{
        padding: 1.1rem 1.5rem; background: {T.gradient("rgba(27,107,90,0.08)","rgba(27,107,90,0.02)",135)};
        border-radius: {T.BORDER_RADIUS}; border-right: 5px solid {T.PRIMARY}; margin: 1rem 0 1.1rem;
        box-shadow: {T.SHADOW_SMALL}; direction: rtl;
    }}
    .insight-box {{ padding: 1.1rem 1.3rem; border-radius: {T.BORDER_RADIUS}; margin-bottom: 1rem; box-shadow: {T.SHADOW_SMALL}; direction: rtl; }}
    .insight-success {{ background: rgba(16,185,129,0.08); border-right: 5px solid {T.ACCENT_EMERALD}; }}
    .insight-warning {{ background: rgba(245,158,11,0.08); border-right: 5px solid {T.ACCENT_AMBER}; }}
    .insight-danger  {{ background: rgba(239,68,68,0.08);  border-right: 5px solid {T.ACCENT_CRIMSON}; }}
    .insight-info    {{ background: rgba(59,130,246,0.08); border-right: 5px solid {T.ACCENT_SAPPHIRE}; }}
    .insight-teal    {{ background: rgba(27,107,90,0.08);  border-right: 5px solid {T.PRIMARY}; }}
    .insight-gold    {{ background: rgba(201,168,76,0.10); border-right: 5px solid {T.GOLD}; }}
    .badge-active   {{ background: rgba(16,185,129,0.15); color:#059669; padding:3px 10px; border-radius:50px; font-size:0.8rem; font-weight:700; }}
    .badge-frozen   {{ background: rgba(59,130,246,0.15); color:#1D4ED8; padding:3px 10px; border-radius:50px; font-size:0.8rem; font-weight:700; }}
    .badge-inactive {{ background: rgba(239,68,68,0.15);  color:#DC2626; padding:3px 10px; border-radius:50px; font-size:0.8rem; font-weight:700; }}
    .dar-table {{ width:100%; border-collapse:collapse; font-size:13px; background:white; direction:rtl; }}
    .dar-table thead tr {{ background: {T.teal_gradient(135)}; color: white; position: sticky; top: 0; z-index: 10; }}
    .dar-table th {{ padding: 10px 12px; border: 1px solid {T.PRIMARY_DARK}; font-size: 12px; font-weight: 700; white-space: nowrap; text-align: center; }}
    .dar-table tbody tr:nth-child(odd)  {{ background: #F7FBF9; }}
    .dar-table tbody tr:nth-child(even) {{ background: #EEF7F3; }}
    .dar-table tbody tr:hover {{ background: rgba(27,107,90,0.10) !important; }}
    .dar-table td {{ padding: 8px 11px; border: 1px solid rgba(27,107,90,0.15); color: {T.TEXT_PRIMARY}; font-size: 12px; text-align: center; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; background: {T.teal_gradient(90)}; padding: 10px 12px; border-radius: {T.BORDER_RADIUS_LARGE}; direction: rtl; }}
    .stTabs [data-baseweb="tab"] {{ background: rgba(255,255,255,0.15); color: white !important; border-radius: {T.BORDER_RADIUS}; padding: 8px 16px; font-weight: 700; }}
    .stTabs [aria-selected="true"] {{ background: white !important; color: {T.PRIMARY_DARK} !important; }}
    </style>
    """, unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────────────────
# 🔐 تسجيل الدخول
# ────────────────────────────────────────────────────────────────────────────
def check_password() -> bool:
    try:
        VALID_USER = st.secrets["auth"]["username"]
        VALID_PASS = st.secrets["auth"]["password"]
    except Exception:
        VALID_USER, VALID_PASS = "admin", "dar2026"

    def _verify():
        u_ok = hmac.compare_digest(st.session_state.get("username", ""), VALID_USER)
        p_ok = hmac.compare_digest(st.session_state.get("password", ""), VALID_PASS)
        st.session_state["auth_ok"] = u_ok and p_ok
        if u_ok and p_ok:
            st.session_state.pop("password", None)
            st.session_state.pop("username", None)

    if st.session_state.get("auth_ok", False):
        return True

    inject_css()
    lb = logo_b64()
    logo_html = (f'<img src="data:image/png;base64,{lb}" style="max-width:150px;">'
                 if lb else '<div style="font-size:3rem;">🕌</div>')
    col = st.columns([1, 1.4, 1])[1]
    with col:
        st.markdown(f"""
        <div style="background:{T.gradient('#0F2E24','#1B4A3A',160)};border-radius:22px 22px 0 0;
            padding:2.2rem 2rem 1.6rem;text-align:center;border:1px solid {T.PRIMARY};box-shadow:{T.SHADOW_GLOW};">
            {logo_html}
            <div style="color:{T.GOLD_LIGHT};font-size:1.5rem;font-weight:800;margin-top:0.8rem;">دار روضة القرآن</div>
            <div style="color:rgba(255,255,255,0.7);font-size:0.9rem;">نظام الإدارة المتكامل</div>
        </div>""", unsafe_allow_html=True)
        with st.form("login_form"):
            st.text_input("👤 اسم المستخدم", key="username", placeholder="اسم المستخدم")
            st.text_input("🔑 كلمة المرور", type="password", key="password", placeholder="كلمة المرور")
            if st.form_submit_button("🚀 تسجيل الدخول"):
                _verify()
                if st.session_state.get("auth_ok"):
                    st.rerun()
                else:
                    st.error("❌ بيانات الدخول غير صحيحة.")
    return False


# ────────────────────────────────────────────────────────────────────────────
# 🧩 مكوّنات
# ────────────────────────────────────────────────────────────────────────────
def header(title, subtitle=""):
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="main-header"><h1>{title}</h1>{sub}</div>', unsafe_allow_html=True)


def section(title, subtitle="", icon=""):
    sub = f'<p style="color:{T.TEXT_SECONDARY};margin:0.3rem 0 0;font-size:0.9rem;">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<div class="section-header"><h3 style="color:{T.PRIMARY_DARK};margin:0;font-size:1.2rem;font-weight:800;">{icon} {title}</h3>{sub}</div>', unsafe_allow_html=True)


def kpi_card(icon, value, label, variant="teal", subtitle=None):
    sub = f'<div class="kpi-sub">{subtitle}</div>' if subtitle else ""
    return f'<div class="kpi-card kpi-{variant}"><div class="kpi-icon">{icon}</div><div class="kpi-value">{value}</div><div class="kpi-label">{label}</div>{sub}</div>'


def kpi_row(items):
    """items = [(icon, value, label, variant[, subtitle])]"""
    cols = st.columns(len(items))
    for c, it in zip(cols, items):
        with c:
            st.markdown(kpi_card(*it), unsafe_allow_html=True)


def insight(text, kind="teal", icon="💡"):
    st.markdown(f'<div class="insight-box insight-{kind}"><span style="font-weight:700;color:{T.PRIMARY_DARK};">{icon} {text}</span></div>', unsafe_allow_html=True)


def display_table(df, title=None, download_name=None, max_height="480px", max_rows=None):
    if df is None or df.empty:
        st.info("لا توجد بيانات للعرض.")
        return
    ddf = df.head(max_rows).copy() if max_rows else df.copy()
    if title:
        st.markdown(f'<h4 style="color:{T.PRIMARY_DARK};font-weight:800;direction:rtl;">{title}</h4>', unsafe_allow_html=True)
    html = (f'<div style="overflow:auto;max-height:{max_height};border:2px solid {T.PRIMARY};'
            f'border-radius:{T.BORDER_RADIUS};box-shadow:{T.SHADOW_MEDIUM};"><table class="dar-table"><thead><tr>'
            + "".join(f"<th>{c}</th>" for c in ddf.columns) + "</tr></thead><tbody>")
    for _, row in ddf.iterrows():
        html += "<tr>" + "".join(f"<td>{'' if pd.isna(v) else v}</td>" for v in row) + "</tr>"
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)
    if max_rows and len(df) > max_rows:
        st.caption(f"يعرض {max_rows} من {len(df):,} سجل")
    if download_name:
        st.download_button(f"📥 تحميل {download_name}",
                           data=df.to_csv(index=False).encode("utf-8-sig"),
                           file_name=download_name, mime="text/csv",
                           key=f"dl_{download_name}_{id(df)}")


def plotly_layout(fig, title="", height=400):
    fig.update_layout(
        title=dict(text=f'<b style="color:{T.PRIMARY_DARK};">{title}</b>', x=0.5, xanchor="center"),
        plot_bgcolor="rgba(240,247,245,0.7)", paper_bgcolor="rgba(247,251,249,0.9)",
        font=dict(color=T.TEXT_PRIMARY, family="Cairo, Tajawal, sans-serif", size=12),
        height=height, margin=dict(l=40, r=40, t=60, b=50),
        legend=dict(bgcolor="rgba(255,255,255,0.92)", bordercolor=T.PRIMARY_LIGHT, borderwidth=1),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(27,107,90,0.10)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(27,107,90,0.10)")
    return fig


def whatsapp_url(phone, text: str) -> str | None:
    """رابط واتساب (wa.me) برسالة مُعبّأة. يحوّل 01XXXXXXXXX → 20XXXXXXXXXX."""
    from .schema import clean_phone
    import urllib.parse
    p = clean_phone(phone)
    if not p:
        return None
    if p.startswith("0"):
        p = "20" + p[1:]
    return f"https://wa.me/{p}?text={urllib.parse.quote(text)}"


def whatsapp_button(phone, text: str, label: str = "📲 إرسال عبر واتساب",
                    with_attachment_hint: bool = True):
    url = whatsapp_url(phone, text)
    if not url:
        st.caption("لا يوجد رقم هاتف صالح لهذا الشخص لإرسال واتساب.")
        return
    st.link_button(label, url)
    if with_attachment_hint:
        st.caption("سيفتح واتساب برسالة جاهزة — ثم أرفِق ملف الـPDF الذي حمّلته.")
    else:
        st.caption("الرسالة تتضمّن رابط التقويم (PDF) — يفتحه المستلم بنقرة، دون إرفاق يدوي.")


def status_badge(status: str) -> str:
    s = str(status)
    if "نشط" in s:
        cls = "badge-active"
    elif "تجميد" in s or "تجريب" in s:
        cls = "badge-frozen"
    else:
        cls = "badge-inactive"
    return f'<span class="{cls}">{s}</span>'
