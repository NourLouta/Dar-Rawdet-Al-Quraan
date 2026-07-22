# -*- coding: utf-8 -*-
"""لوحة المتابعة — مؤشرات وأعمال ورسوم بيانية."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st

from .. import ui, state, finance as fin
from ..config import CHART_COLORS, T, STUDENT_HOURLY
from ..schema import Student, Teacher, Session, Enrollment


def render():
    ui.header("📊 لوحة المتابعة", "نظرة عامة على دار روضة القرآن")
    ui.guide("عن هذه الشاشة", """
**ما هي؟** نظرة سريعة وشاملة على وضع الدار: عدد الطلاب والمحفظين، الإيرادات والمرتبات
والأرباح، وتوزيع الطلاب حسب الحالة والفئة، وحمل كل محفظة.

**متى تستخدمها؟**
- أول شيء تفتحينه كل يوم لمعرفة الوضع العام بسرعة.
- لمتابعة الأداء المالي الشهري (فلتري بالشهر من القائمة أعلاه).
- لملاحظة أي طلاب في حالة تجميد أو توقف تحتاج متابعة.

**ملاحظة:** الأرقام المالية تعتمد على وجود حصص مولّدة بحالة «تمت» ومدة محدّدة —
إن ظهرت صفرًا، تأكدي من توليد حصص الشهر أولًا من شاشة «الحصص والإدخال».
""")
    data = state.get_data()
    students, teachers = data["students"], data["teachers"]
    sessions, enroll = data["sessions"], data["enrollments"]

    months = state.months_available(sessions)
    c1, c2 = st.columns([3, 1])
    with c2:
        month = st.selectbox("📅 الشهر", ["كل الشهور"] + months, index=0)
    month_f = None if month == "كل الشهور" else month

    n_total = len(students)
    n_active = int(state.active_mask(students).sum())
    n_frozen = int(students[Student.STATUS].astype(str).str.contains("تجميد", na=False).sum()) if Student.STATUS in students.columns else 0
    cs = fin.center_summary(sessions, teachers, STUDENT_HOURLY, month=month_f, enrollments=enroll, program_map=state.program_rate_map())

    ui.kpi_row([
        ("👨‍🎓", n_total, "إجمالي الطلاب", "teal"),
        ("✅", n_active, "طلاب نشطون", "emerald"),
        ("⏸️", n_frozen, "تجميد مؤقت", "sapphire"),
        ("👩‍🏫", len(teachers), "المحفظون", "violet"),
    ])
    st.write("")
    ui.kpi_row([
        ("⏱️", f"{cs['total_hours']:.0f}", "ساعات منفّذة", "amber"),
        ("💰", ui.fmt_currency(cs["revenue"]), "الإيرادات", "gold"),
        ("👛", ui.fmt_currency(cs["salaries_payout"]), "مرتبات المحفظين", "rose"),
        ("📈", ui.fmt_currency(cs["profit"]), f"صافي الربح ({cs['margin_pct']:.0f}%)", "emerald"),
    ])

    if cs["total_hours"] == 0 and not sessions.empty:
        ui.insight("لا توجد ساعات محسوبة — تأكد من تعبئة «مدة الحصة (دقيقة)» و«حالة الحصة = تمت» في الحصص.", "warning", "⚠️")

    st.write("")
    col1, col2 = st.columns(2)

    with col1:
        ui.section("توزيع حالة الاشتراك", icon="🟢")
        if Student.STATUS in students.columns and not students.empty:
            vc = students[Student.STATUS].fillna("غير محدد").value_counts().reset_index()
            vc.columns = ["الحالة", "العدد"]
            fig = px.pie(vc, names="الحالة", values="العدد", hole=0.55,
                         color_discrete_sequence=CHART_COLORS)
            st.plotly_chart(ui.plotly_layout(fig, height=350), width='stretch')

    with col2:
        ui.section("الطلاب حسب الفئة", icon="👥")
        if Student.CATEGORY in students.columns and not students.empty:
            vc = students[Student.CATEGORY].fillna("غير محدد").value_counts().reset_index()
            vc.columns = ["الفئة", "العدد"]
            fig = px.bar(vc, x="العدد", y="الفئة", orientation="h",
                         color="العدد", color_continuous_scale=["#2A8C75", "#134E41"])
            st.plotly_chart(ui.plotly_layout(fig, height=350), width='stretch')

    col3, col4 = st.columns(2)
    with col3:
        ui.section("حمل المحفظين (طلاب نشطون)", icon="📊")
        if not enroll.empty and Enrollment.TEACHER_NAME in enroll.columns:
            act = enroll
            if Enrollment.STATUS in enroll.columns:
                act = enroll[enroll[Enrollment.STATUS].astype(str).str.contains("نشط", na=False)]
            vc = act[Enrollment.TEACHER_NAME].replace("", pd.NA).dropna().value_counts().reset_index()
            vc.columns = ["المحفظ", "عدد الطلاب"]
            if not vc.empty:
                fig = px.bar(vc.head(12), x="عدد الطلاب", y="المحفظ", orientation="h",
                             color="عدد الطلاب", color_continuous_scale=["#E2C06A", "#A8892E"])
                st.plotly_chart(ui.plotly_layout(fig, height=360), width='stretch')

    with col4:
        ui.section("الإيراد مقابل المرتبات", icon="💹")
        fig = px.bar(pd.DataFrame({
            "البند": ["الإيرادات", "المرتبات", "صافي الربح"],
            "القيمة": [cs["revenue"], cs["salaries_payout"], cs["profit"]],
        }), x="البند", y="القيمة", color="البند",
            color_discrete_sequence=[T.GOLD, T.ACCENT_ROSE, T.ACCENT_EMERALD])
        st.plotly_chart(ui.plotly_layout(fig, height=360), width='stretch')
