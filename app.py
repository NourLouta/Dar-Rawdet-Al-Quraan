# -*- coding: utf-8 -*-
"""
دار روضة القرآن — نظام الإدارة المتكامل (Streamlit).

نقطة الدخول: تسجيل دخول → شريط جانبي بالهوية → توجيه للصفحات.
قاعدة البيانات = Google Sheets (الملف الجديد) عبر dar.sheets_io.
شغّل محليًا:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="دار روضة القرآن",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "# دار روضة القرآن\nنظام الإدارة المتكامل"},
)

from dar import ui, state
from dar import sheets_io as io
from dar.config import T
from dar.views import (
    dashboard, students, teachers, enrollments, sessions, finance_view,
    feedback, reports,
)

# ── تسجيل الدخول ──────────────────────────────────────────────────────────────
if not ui.check_password():
    st.stop()

ui.inject_css()

PAGES = {
    "📊 لوحة المتابعة": dashboard.render,
    "👨‍🎓 الطلاب": students.render,
    "👩‍🏫 المحفظون": teachers.render,
    "📝 التسجيلات": enrollments.render,
    "📅 الحصص والإدخال": sessions.render,
    "💰 المالية": finance_view.render,
    "⭐ التقييمات": feedback.render,
    "📄 التقارير والتقاويم": reports.render,
}


def sidebar():
    lb = ui.logo_b64()
    logo_html = (f'<img src="data:image/png;base64,{lb}" style="max-width:130px;margin:0 auto 0.6rem;display:block;">'
                 if lb else '<div style="font-size:2.4rem;text-align:center;">🕌</div>')
    st.sidebar.markdown(f"""
    <div style="background:{T.gradient('#0F2E24','#1B4A3A',160)};border:1px solid {T.PRIMARY};
        border-radius:{T.BORDER_RADIUS_LARGE};padding:1.3rem 1rem;text-align:center;
        margin-bottom:1rem;box-shadow:{T.SHADOW_GLOW};">
        {logo_html}
        <div style="color:{T.GOLD_LIGHT};font-size:1rem;font-weight:800;">دار روضة القرآن</div>
        <div style="color:rgba(255,255,255,0.55);font-size:0.72rem;">نظام الإدارة المتكامل</div>
    </div>""", unsafe_allow_html=True)

    choice = st.sidebar.radio("القائمة", list(PAGES.keys()), label_visibility="collapsed")

    # ملخص سريع + حالة الاتصال
    data = state.get_data()
    n_students = len(data["students"])
    n_active = int(state.active_mask(data["students"]).sum())
    n_teachers = len(data["teachers"])
    _tgt = io.write_target()
    mode = {"google": "✅ Google (حفظ مباشر)", "local": "💾 حفظ محلي (تجربة)"}.get(_tgt, "👁️ قراءة فقط")
    st.sidebar.markdown(f"""
    <div style="background:rgba(27,107,90,0.15);border:1px solid {T.PRIMARY};
        border-radius:{T.BORDER_RADIUS};padding:0.9rem;margin-top:0.6rem;">
        <div style="color:{T.GOLD_LIGHT};font-size:0.78rem;font-weight:700;margin-bottom:0.4rem;">📊 ملخص سريع</div>
        <div style="color:rgba(255,255,255,0.85);font-size:0.78rem;line-height:2;">
            👨‍🎓 الطلاب: {n_students} (نشط {n_active})<br>
            👩‍🏫 المحفظون: {n_teachers}<br>
            🔌 الوضع: {mode}
        </div>
    </div>""", unsafe_allow_html=True)

    if st.sidebar.button("🔄 تحديث البيانات"):
        state.get_data(force=True)
        st.rerun()
    if st.sidebar.button("🚪 تسجيل الخروج"):
        st.session_state["auth_ok"] = False
        st.rerun()
    return choice


def main():
    choice = sidebar()
    try:
        PAGES[choice]()
    except Exception as e:
        st.error(f"حدث خطأ في الصفحة: {e}")
        st.exception(e)


main()
