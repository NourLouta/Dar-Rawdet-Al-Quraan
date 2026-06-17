# -*- coding: utf-8 -*-
"""التسجيلات — ربط الطالب بالمحفظ + تحديد النمط الأسبوعي (يشغّل مولّد الحصص)."""
from __future__ import annotations
from datetime import date

import streamlit as st

from .. import ui, state
from .. import sheets_io as io
from ..config import STUDENT_HOURLY, TEACHER_HOURLY_DEFAULT
from ..schema import (
    Enrollment, Student, Teacher, options_from, code_of, make_display,
    format_arabic_time, parse_arabic_time, ARABIC_WEEKDAYS, format_day_schedule,
)
from ..finance import teacher_hourly_rate


def render():
    ui.header("📝 التسجيلات", "ربط كل طالب بمحفظ وتحديد جدوله الأسبوعي")
    data = state.get_data()
    enroll, students, teachers = data["enrollments"], data["students"], data["teachers"]
    t_list, t_add = st.tabs(["📋 التسجيلات", "➕ تسجيل جديد"])

    with t_list:
        if enroll.empty:
            st.info("لا توجد تسجيلات بعد.")
        else:
            cols = [c for c in [Enrollment.CODE, Enrollment.STUDENT_NAME, Enrollment.TEACHER_NAME,
                                Enrollment.STUDY_TYPE, Enrollment.WEEK_DAYS, Enrollment.DAY_SCHEDULE,
                                Enrollment.SUB_VALUE, Enrollment.STATUS]
                    if c in enroll.columns]
            ui.display_table(enroll[cols], download_name="التسجيلات.csv")

    with t_add:
        can = state.write_banner()
        if students.empty or teachers.empty:
            st.warning("أضف طلابًا ومحفظين أولًا.")
            return
        next_code = io.next_code("enrollment", enroll, Enrollment.CODE)
        st.markdown(f"**كود التسجيل:** `{next_code}`")

        s_opts = options_from(students, Student.CODE, Student.NAME)
        t_opts = options_from(teachers, Teacher.CODE, Teacher.NAME)
        times = state.lk("time_slots") or ["8:00 ص", "5:00 م"]

        # ملاحظة: خارج st.form كي تظهر حقول كل يوم تفاعليًا حسب الأيام المختارة
        c1, c2 = st.columns(2)
        s_lbl = c1.selectbox("الطالب *", [o[0] for o in s_opts], key="enr_student")
        t_lbl = c2.selectbox("المحفظ *", [o[0] for o in t_opts], key="enr_teacher")
        c3, c4, c5 = st.columns(3)
        study = c3.selectbox("نوع الدراسة", [""] + state.lk("study_type"), key="enr_study")
        start = c4.date_input("تاريخ البداية", value=date.today(), format="YYYY-MM-DD", key="enr_start")
        status = c5.selectbox("حالة التسجيل", ["نشط", "موقوف", "منتهي"], key="enr_status")

        st.markdown("##### 🗓️ الجدول الأسبوعي (يُولّد الحصص تلقائيًا)")
        days = st.multiselect("أيام الأسبوع", ARABIC_WEEKDAYS, key="enr_days")
        st.caption("اختر الأيام، ثم حدّد وقت ومدة كل يوم (يمكن أن تختلف من يوم لآخر).")

        # حقول وقت/مدة لكل يوم مختار
        sched = []
        for d in days:
            cc1, cc2, cc3 = st.columns([1, 2, 2])
            cc1.markdown(f"<div style='padding-top:2rem;font-weight:700;'>{d}</div>", unsafe_allow_html=True)
            t = cc2.selectbox(f"وقت {d}", times, key=f"enr_t_{d}")
            m = cc3.selectbox(f"مدة {d} (دقيقة)", [30, 45, 60, 90, 120], index=0, key=f"enr_m_{d}")
            sched.append((d, t, int(m)))

        st.caption(f"سعر ساعة الطالب: {STUDENT_HOURLY} ج.م — سعر ساعة المحفظ من ملف المحفظين.")
        notes = st.text_input("ملاحظات", key="enr_notes")
        submitted = st.button("💾 حفظ التسجيل")

        if submitted:
            if not s_lbl or not t_lbl:
                st.error("اختر الطالب والمحفظ.")
                return
            if not sched:
                st.error("اختر يومًا واحدًا على الأقل وحدّد وقته ومدته.")
                return
            s_code, t_code = code_of(s_lbl), code_of(t_lbl)
            s_name = s_lbl.split(" — ")[-1] if " — " in s_lbl else ""
            t_name = t_lbl.split(" — ")[-1] if " — " in t_lbl else ""
            row = {
                Enrollment.CODE: next_code,
                Enrollment.STUDENT_CODE: make_display(s_code, s_name),
                Enrollment.STUDENT_NAME: s_name,
                Enrollment.TEACHER_CODE: make_display(t_code, t_name),
                Enrollment.TEACHER_NAME: t_name,
                Enrollment.STUDY_TYPE: study, Enrollment.START: start,
                Enrollment.STATUS: status,
                Enrollment.WEEK_DAYS: "، ".join(d for d, _, _ in sched),
                Enrollment.SESS_TIME: sched[0][1], Enrollment.SESS_MIN: sched[0][2],
                Enrollment.DAY_SCHEDULE: format_day_schedule(sched),
                Enrollment.NOTES: notes,
                Enrollment.DISPLAY: f"{next_code} — {s_name} / {t_name}",
            }
            if not can:
                st.json({k: str(v) for k, v in row.items()})
                return
            try:
                io.append_row("enrollments", row)
                state.get_data(force=True)
                summary = "، ".join(f"{d} {t} ({m}د)" for d, t, m in sched)
                st.success(f"✅ تم حفظ التسجيل {next_code}: {s_name} مع {t_name} — {summary}")
            except Exception as e:
                st.error(f"تعذّر الحفظ: {e}")
