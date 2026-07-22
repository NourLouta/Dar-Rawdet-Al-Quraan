# -*- coding: utf-8 -*-
"""المالية — الإيراد، مرتبات المحفظين (بالساعة + فودافون)، الأرباح، الفواتير."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .. import ui, state, finance as fin
from ..config import STUDENT_HOURLY, VODAFONE_CASH_FEE, ROUND_TO, T, CHART_COLORS
from ..schema import Session, Student


def render():
    ui.header("💰 المالية", "حساب بالساعة — مع رسوم فودافون كاش والتقريب لأقرب 5 ج.م")
    ui.guide("عن هذه الشاشة", """
**ما هي؟** الحساب المالي الكامل: كشف مرتبات كل محفظة، فواتير كل طالب، والإيرادات
والأرباح الإجمالية — كلها محسوبة تلقائيًا من الحصص المنفّذة وأسعار كل تسجيل.

**متى تستخدمها؟**
- آخر كل شهر، لصرف المرتبات ومعرفة صافي الربح.
- لإصدار فاتورة مستحقات أي طالب.
- لمراجعة سعر ساعة أي تسجيل قبل تأكيد المرتب.

**لماذا تظهر الأرقام صفرًا؟** الحساب يعتمد فقط على الحصص بحالة «تمت» ولها «مدة
الحصة (دقيقة)» محدَّدة. تأكدي من توليد الحصص وتسجيل حالتها أولًا من شاشة «الحصص».
""")
    data = state.get_data()
    sessions, teachers, students = data["sessions"], data["teachers"], data["students"]
    enroll = data["enrollments"]

    months = ["كل الشهور"] + state.months_available(sessions)
    month = st.selectbox("📅 الشهر", months)
    mf = None if month == "كل الشهور" else month

    cs = fin.center_summary(sessions, teachers, STUDENT_HOURLY, month=mf, enrollments=enroll, program_map=state.program_rate_map())
    ui.kpi_row([
        ("💰", ui.fmt_currency(cs["revenue"]), "إجمالي الإيرادات", "gold"),
        ("👛", ui.fmt_currency(cs["salaries_payout"]), "مرتبات المحفظين", "rose"),
        ("📈", ui.fmt_currency(cs["profit"]), "صافي الربح", "emerald"),
        ("％", f"{cs['margin_pct']:.0f}%", "هامش الربح", "teal"),
    ])

    ui.insight(
        f"المعادلة: راتب المحفظ = ساعات الحصص المنفّذة × سعر ساعته، ثم ×{VODAFONE_CASH_FEE} "
        f"(رسوم فودافون كاش) مع التقريب لأعلى لأقرب {ROUND_TO} ج.م. "
        f"إيراد الطالب = ساعاته × {STUDENT_HOURLY} ج.م.", "teal", "🧮")

    # رسم الإيراد/المرتبات/الربح
    c1, c2 = st.columns(2)
    with c1:
        ui.section("توزيع الأموال", icon="💹")
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["الإيرادات", "المرتبات", "صافي الربح"],
            y=[cs["revenue"], -cs["salaries_payout"], cs["profit"]],
            connector={"line": {"color": T.PRIMARY_LIGHT}},
            increasing={"marker": {"color": T.ACCENT_EMERALD}},
            decreasing={"marker": {"color": T.ACCENT_ROSE}},
            totals={"marker": {"color": T.GOLD}},
        ))
        st.plotly_chart(ui.plotly_layout(fig, height=350), width='stretch')

    sal = fin.all_teacher_salaries(sessions, teachers, month=mf, enrollments=enroll, program_map=state.program_rate_map())
    with c2:
        ui.section("مرتبات المحفظين", icon="👩‍🏫")
        if not sal.empty:
            fig = px.bar(sal.head(12), x="net_payout", y="teacher_name", orientation="h",
                         labels={"net_payout": "صافي التحويل", "teacher_name": "المحفظ"},
                         color="net_payout", color_continuous_scale=["#E2C06A", "#A8892E"])
            st.plotly_chart(ui.plotly_layout(fig, height=350), width='stretch')

    ui.section("كشف رواتب المحفظين", icon="🧾")
    if sal.empty:
        st.info("لا توجد بيانات رواتب (تأكد من الحصص ومددها).")
    else:
        disp = sal.rename(columns={
            "teacher_code": "الكود", "teacher_name": "المحفظ", "sessions_done": "حصص منفّذة",
            "hours": "ساعات", "rate": "سعر الساعة", "base_salary": "الراتب الأساسي",
            "vodafone_fee": "رسوم 1%", "net_payout": "صافي التحويل",
        })[["الكود", "المحفظ", "حصص منفّذة", "ساعات", "سعر الساعة",
            "الراتب الأساسي", "رسوم 1%", "صافي التحويل"]]
        total = disp["صافي التحويل"].sum()
        ui.display_table(disp, download_name="كشف_الرواتب.csv")
        st.markdown(f"**إجمالي صافي التحويلات:** {int(total):,} ج.م")

    # فواتير الطلاب
    ui.section("فواتير الطلاب (المستحق)", icon="📑")
    rows = []
    src = sessions
    if mf and Session.MONTH in sessions.columns:
        src = sessions[sessions[Session.MONTH].astype(str) == mf]
    if not src.empty and Session.STUDENT_CODE in src.columns:
        for code in src[Session.STUDENT_CODE].dropna().unique():
            r = fin.student_revenue(str(code), src, month=None, enrollments=enroll, teachers=teachers, program_map=state.program_rate_map())
            if r["hours"] <= 0:
                continue
            name = ""
            sub = src[src[Session.STUDENT_CODE] == code]
            if not sub.empty:
                name = sub.iloc[0].get(Session.STUDENT_NAME, "")
            rows.append({"كود الطالب": code, "اسم الطالب": name, "ساعات": r["hours"],
                         "سعر الساعة": r["rate"], "المستحق": r["fee_due"],
                         "مقرّب لـ5": r["fee_rounded"]})
    if rows:
        inv = pd.DataFrame(rows).sort_values("المستحق", ascending=False)
        ui.display_table(inv, download_name="فواتير_الطلاب.csv")
    else:
        st.info("لا توجد ساعات محسوبة لإصدار فواتير.")
