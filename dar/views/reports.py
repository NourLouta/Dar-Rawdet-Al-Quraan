# -*- coding: utf-8 -*-
"""التقارير والتقاويم — توليد PDF احترافي بالهوية للطلاب والمحفظين."""
from __future__ import annotations
import pandas as pd
import streamlit as st

from .. import ui, state, finance as fin, documents as doc
from ..config import STUDENT_HOURLY
from ..schema import (
    Student, Teacher, Session, options_from, code_of,
)
from .feedback import RATING_SCORE


def _student_stats(s_code, sessions, students, teachers, pfb, month, enrollments=None):
    sub = sessions[sessions[Session.STUDENT_CODE].astype(str) == str(s_code)] if Session.STUDENT_CODE in sessions.columns else sessions.iloc[0:0]
    if month and Session.MONTH in sub.columns:
        sub = sub[sub[Session.MONTH].astype(str) == month]
    total = len(sub)
    done = int((sub[Session.STATUS].astype(str).str.strip() == "تمت").sum()) if Session.STATUS in sub.columns else 0
    cancelled = total - done
    hours = fin.completed_hours(sub)
    rev = fin.student_revenue(str(s_code), sub, month=None, enrollments=enrollments, teachers=teachers, program_map=state.program_rate_map())
    # متوسط تقييم المحفظ
    avg_rating = "—"
    if Session.RATING in sub.columns:
        sc = sub[Session.RATING].map(RATING_SCORE).dropna()
        if len(sc):
            avg_rating = round(sc.mean(), 2)
    teacher = sub[Session.TEACHER_NAME].iloc[0] if (not sub.empty and Session.TEACHER_NAME in sub.columns) else ""
    # رضا ولي الأمر
    pscore = "—"
    if pfb is not None and not pfb.empty:
        from ..schema import ParentFeedback as PF
        pp = pfb[pfb[PF.STUDENT_CODE].astype(str) == str(s_code)] if PF.STUDENT_CODE in pfb.columns else pfb.iloc[0:0]
        if month and PF.MONTH in pp.columns:
            pp = pp[pp[PF.MONTH].astype(str) == month]
        sc = pd.to_numeric(pp[PF.SCORE], errors="coerce").dropna() if PF.SCORE in pp.columns else pd.Series(dtype=float)
        if len(sc):
            pscore = round(sc.mean(), 1)
    return {
        "done": done, "cancelled": cancelled,
        "attendance": round(done / total * 100) if total else 0,
        "hours": round(hours, 1), "teacher": teacher, "avg_rating": avg_rating,
        "parent_score": pscore, "fee": rev["fee_rounded"],
    }, sub


def render():
    ui.header("📄 التقارير والتقاويم", "مستندات PDF احترافية بهوية الدار — جاهزة للإرسال")
    ui.guide("عن هذه الشاشة", """
**ما هي؟** توليد مستندات PDF جاهزة للإرسال، بهوية الدار: تقويم شهري بحصص الطالب أو
المحفظة، وتقرير أداء شهري لكل منهما.

**متى تستخدمها؟**
- أول كل شهر: أرسلي لكل طالب تقويم حصصه، ولكل محفظة تقويم جدولها.
- عند طلب ولي أمر تقريرًا عن تقدّم ابنه (حضور، تقدّم الحفظ، التقييم).
- لمراجعة أداء محفظة قبل تجديد التعاقد.

**تحتاج حصصًا مولّدة أولًا** — لن تظهر بيانات هنا قبل توليد حصص الشهر من شاشة «الحصص».
""")
    data = state.get_data()
    sessions, students, teachers = data["sessions"], data["students"], data["teachers"]
    enroll = data["enrollments"]
    pfb = data.get("pfeedback", pd.DataFrame())
    months = state.months_available(sessions)
    if not months:
        st.info("لا توجد حصص لتوليد التقارير. ابدأ بتوليد الحصص من شاشة «الحصص».")
        return

    t_cal, t_srep, t_trep = st.tabs(["📅 تقويم شهري", "🧑‍🎓 تقرير طالب", "👩‍🏫 تقرير محفظ"])

    # ── تقويم ────────────────────────────────────────────────────────────────
    with t_cal:
        ui.guide("متى تستخدم هذا التبويب؟",
                "لتوليد تقويم شهري جميل (PDF) بحصص طالب أو محفظة معيّنة، وتحميله ثم إرساله "
                "عبر واتساب مباشرة بضغطة زر (مع رسالة جاهزة).")
        c1, c2, c3 = st.columns(3)
        kind = c1.radio("النوع", ["طالب", "محفظ"], horizontal=True)
        month = c2.selectbox("الشهر", months, key="cal_m")
        if kind == "طالب":
            opts = options_from(students, Student.CODE, Student.NAME)
            sel = c3.selectbox("الطالب", [o[0] for o in opts], key="cal_s")
            code = code_of(sel)
            sub = sessions[sessions[Session.STUDENT_CODE].astype(str) == code] \
                if Session.STUDENT_CODE in sessions.columns else sessions.iloc[0:0]
            title = f"تقويم الطالب — {(sel or '').split(' — ')[-1]}"
            field = "surah"
        else:
            opts = options_from(teachers, Teacher.CODE, Teacher.NAME)
            sel = c3.selectbox("المحفظ", [o[0] for o in opts], key="cal_t")
            name = (sel or "").split(" — ")[-1]
            sub = sessions[sessions[Session.TEACHER_NAME].astype(str) == name] \
                if Session.TEACHER_NAME in sessions.columns else sessions.iloc[0:0]
            title = f"تقويم المحفظ — {name}"
            field = "student"
        # رقم الهاتف للمشاركة عبر واتساب
        phone = ""
        if kind == "طالب":
            row = students[students[Student.CODE] == code]
            phone = row.iloc[0].get(Student.PARENT_PHONE, "") if not row.empty else ""
        else:
            row = teachers[teachers[Teacher.NAME] == name]
            phone = row.iloc[0].get(Teacher.PHONE, "") if not row.empty else ""
        if not sel:
            st.info("لا توجد بيانات للاختيار.")
            return
        if st.button("📄 توليد التقويم (PDF)"):
            fname = f"{title}-{month}.pdf"
            pdf = doc.monthly_calendar_pdf(month, sub, title, "الحصص الشهرية", show_field=field)
            st.download_button("⬇️ تحميل التقويم", pdf, file_name=fname, mime="application/pdf")
            st.success("تم التوليد — حمّل الملف ثم شاركه.")
            msg = f"السلام عليكم ورحمة الله، إليكم جدول حصص {title} لشهر {month} من دار روضة القرآن."
            ui.whatsapp_button(phone, msg)

    # ── تقرير طالب ──────────────────────────────────────────────────────────────
    with t_srep:
        ui.guide("متى تستخدم هذا التبويب؟",
                "لتوليد تقرير شهري لطالب معيّن: عدد الحصص المنفّذة والملغية، نسبة الحضور، "
                "متوسط تقييم المحفظة، رضا ولي الأمر، والمستحق ماليًا — مناسب لمشاركته مع الأهل.")
        c1, c2 = st.columns(2)
        opts = options_from(students, Student.CODE, Student.NAME)
        sel = c1.selectbox("الطالب", [o[0] for o in opts], key="srep_s")
        month = c2.selectbox("الشهر", months, key="srep_m")
        code = code_of(sel)
        if not sel:
            st.info("لا يوجد طلاب.")
            return
        if st.button("📄 توليد تقرير الطالب (PDF)"):
            srow = students[students[Student.CODE] == code]
            srow = srow.iloc[0].to_dict() if not srow.empty else {Student.CODE: code, Student.NAME: (sel or "").split(" — ")[-1]}
            stats, sub = _student_stats(code, sessions, students, teachers, pfb, month, enrollments=enroll)
            pdf = doc.student_report_pdf(srow, stats, sub.head(40).to_dict("records"), month)
            st.download_button("⬇️ تحميل التقرير", pdf,
                               file_name=f"تقرير-{srow.get(Student.NAME,'')}-{month}.pdf",
                               mime="application/pdf")
            ui.kpi_row([
                ("✅", stats["done"], "حصص منفّذة", "emerald"),
                ("📊", f"{stats['attendance']}%", "الحضور", "teal"),
                ("⭐", stats["parent_score"], "رضا ولي الأمر", "gold"),
                ("💰", ui.fmt_currency(stats["fee"]), "المستحق", "amber"),
            ])

    # ── تقرير محفظ ──────────────────────────────────────────────────────────────
    with t_trep:
        ui.guide("متى تستخدم هذا التبويب؟",
                "لتوليد تقرير شهري لمحفظة معيّنة: عدد الحصص والساعات والراتب المستحق، "
                "عدد الطلاب، ومتوسط رضا أولياء أمورهم — مفيد لمراجعة الأداء أو عند التجديد.")
        c1, c2 = st.columns(2)
        opts = options_from(teachers, Teacher.CODE, Teacher.NAME)
        sel = c1.selectbox("المحفظ", [o[0] for o in opts], key="trep_t")
        month = c2.selectbox("الشهر", months, key="trep_m")
        code = code_of(sel)
        name = (sel or "").split(" — ")[-1]
        if not sel:
            st.info("لا يوجد محفظون.")
            return
        if st.button("📄 توليد تقرير المحفظ (PDF)"):
            trow = teachers[teachers[Teacher.CODE] == code]
            trow = trow.iloc[0].to_dict() if not trow.empty else {Teacher.CODE: code, Teacher.NAME: name}
            sal = fin.teacher_salary(code, name, sessions, teachers, month, enrollments=enroll, program_map=state.program_rate_map())
            # طلاب المحفظ في الشهر
            sub = sessions[(sessions[Session.TEACHER_NAME] == name)] \
                if Session.TEACHER_NAME in sessions.columns else sessions.iloc[0:0]
            if Session.MONTH in sub.columns:
                sub = sub[sub[Session.MONTH].astype(str) == month]
            srows = []
            codes = sub[Session.STUDENT_CODE].dropna().unique() if Session.STUDENT_CODE in sub.columns else []
            for sc in codes:
                ss = sub[sub[Session.STUDENT_CODE] == sc]
                srows.append({
                    "code": sc, "name": ss.iloc[0].get(Session.STUDENT_NAME, ""),
                    "done": int((ss[Session.STATUS].astype(str).str.strip() == "تمت").sum()) if Session.STATUS in ss.columns else 0,
                    "hours": round(fin.completed_hours(ss), 1),
                    "surah": ss.iloc[0].get(Session.SURAH, ""),
                })
            pdf = doc.teacher_report_pdf(trow, sal, srows, month)
            st.download_button("⬇️ تحميل التقرير", pdf,
                               file_name=f"تقرير-{name}-{month}.pdf", mime="application/pdf")
            ui.kpi_row([
                ("✅", sal["sessions_done"], "حصص منفّذة", "emerald"),
                ("⏱️", sal["hours"], "ساعات", "teal"),
                ("👛", ui.fmt_currency(sal["net_payout"]), "صافي التحويل", "gold"),
                ("🧑‍🎓", len(srows), "عدد الطلاب", "violet"),
            ])
