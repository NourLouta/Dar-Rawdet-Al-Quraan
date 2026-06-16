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
    format_arabic_time, parse_arabic_time, ARABIC_WEEKDAYS,
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
                                Enrollment.STUDY_TYPE, Enrollment.WEEK_DAYS, Enrollment.SESS_TIME,
                                Enrollment.SESS_MIN, Enrollment.SUB_VALUE, Enrollment.STATUS]
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

        with st.form("add_enrollment"):
            c1, c2 = st.columns(2)
            s_lbl = c1.selectbox("الطالب *", [o[0] for o in s_opts])
            t_lbl = c2.selectbox("المحفظ *", [o[0] for o in t_opts])
            c3, c4, c5 = st.columns(3)
            study = c3.selectbox("نوع الدراسة", [""] + state.lk("study_type"))
            start = c4.date_input("تاريخ البداية", value=date.today(), format="YYYY-MM-DD")
            status = c5.selectbox("حالة التسجيل", ["نشط", "موقوف", "منتهي"])

            st.markdown("##### 🗓️ النمط الأسبوعي (يُستخدم لتوليد الحصص تلقائيًا)")
            c6, c7, c8 = st.columns(3)
            days = c6.multiselect("أيام الأسبوع", ARABIC_WEEKDAYS)
            time_slot = c7.selectbox("وقت الحصة", state.lk("time_slots") or ["5:00 م"])
            minutes = c8.selectbox("مدة الحصة (دقيقة)", [30, 45, 60, 90, 120], index=0)

            st.caption(f"سعر ساعة الطالب: {STUDENT_HOURLY} ج.م — سعر ساعة المحفظ يُؤخذ من ملف المحفظين.")
            notes = st.text_input("ملاحظات")
            submitted = st.form_submit_button("💾 حفظ التسجيل")

        if submitted:
            if not s_lbl or not t_lbl:
                st.error("اختر الطالب والمحفظ.")
                return
            s_code = code_of(s_lbl)
            t_code = code_of(t_lbl)
            s_name = s_lbl.split(" — ")[-1] if " — " in s_lbl else ""
            t_name = t_lbl.split(" — ")[-1] if " — " in t_lbl else ""
            rate = teacher_hourly_rate(t_code, teachers) or TEACHER_HOURLY_DEFAULT
            # سعر الحصة المرجعي للمعلم = الساعة × (الدقائق/60)
            sess_price = round(rate * minutes / 60, 2)
            row = {
                Enrollment.CODE: next_code,
                Enrollment.STUDENT_CODE: make_display(s_code, s_name),
                Enrollment.STUDENT_NAME: s_name,
                Enrollment.TEACHER_CODE: make_display(t_code, t_name),
                Enrollment.TEACHER_NAME: t_name,
                Enrollment.STUDY_TYPE: study, Enrollment.START: start,
                Enrollment.SESS_PRICE: sess_price, Enrollment.STATUS: status,
                Enrollment.WEEK_DAYS: "، ".join(days),
                Enrollment.SESS_TIME: time_slot, Enrollment.SESS_MIN: minutes,
                Enrollment.NOTES: notes,
                Enrollment.DISPLAY: f"{next_code} — {s_name} / {t_name}",
            }
            if not can:
                st.json({k: str(v) for k, v in row.items()})
                return
            try:
                io.append_row("enrollments", row)
                state.get_data(force=True)
                st.success(f"✅ تم حفظ التسجيل {next_code} للطالب {s_name} مع {t_name}.")
            except Exception as e:
                st.error(f"تعذّر الحفظ: {e}")
