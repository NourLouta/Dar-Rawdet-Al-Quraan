# -*- coding: utf-8 -*-
"""المحفظون — قائمة + إضافة، مع كشف أداء سريع."""
from __future__ import annotations
from datetime import date

import pandas as pd
import streamlit as st

from .. import ui, state, finance as fin
from .. import sheets_io as io
from ..config import STUDENT_HOURLY
from ..schema import Teacher, Session, make_display, clean_phone, is_valid_egypt_phone


def render():
    ui.header("👩‍🏫 المحفظون", "إدارة بيانات المحفظين والأداء")
    data = state.get_data()
    teachers, sessions = data["teachers"], data["sessions"]
    t_list, t_perf, t_add = st.tabs(["📋 القائمة", "📊 الأداء", "➕ إضافة محفظ"])

    with t_list:
        if teachers.empty:
            st.info("لا يوجد محفظون بعد.")
        else:
            cols = [c for c in [Teacher.CODE, Teacher.NAME, Teacher.GENDER, Teacher.GOV,
                                Teacher.QUALIFY, Teacher.EXPERIENCE, Teacher.TEACHES,
                                Teacher.HOURLY, Teacher.CONTRACT, Teacher.SPECIAL] if c in teachers.columns]
            ui.display_table(teachers[cols], download_name="المحفظين.csv")

    with t_perf:
        months = ["كل الشهور"] + state.months_available(sessions)
        month = st.selectbox("الشهر", months, key="t_perf_month")
        mf = None if month == "كل الشهور" else month
        sal = fin.all_teacher_salaries(sessions, teachers, month=mf)
        if sal.empty:
            st.info("لا توجد حصص لحساب الأداء.")
        else:
            disp = sal.rename(columns={
                "teacher_name": "المحفظ", "sessions_done": "حصص منفّذة",
                "sessions_cancelled": "ملغية", "hours": "ساعات", "rate": "سعر الساعة",
                "base_salary": "الراتب الأساسي", "vodafone_fee": "رسوم 1%",
                "net_payout": "صافي التحويل",
            })[["المحفظ", "حصص منفّذة", "ملغية", "ساعات", "سعر الساعة",
                "الراتب الأساسي", "رسوم 1%", "صافي التحويل"]]
            ui.display_table(disp, download_name="اداء_المحفظين.csv")

    with t_add:
        can = state.write_banner()
        next_code = io.next_code("teacher", teachers, Teacher.CODE)
        st.markdown(f"**الكود الجديد:** `{next_code}`")
        with st.form("add_teacher"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("الاسم الكامل *")
            gender = c2.selectbox("النوع", [""] + state.lk("gender"))
            phone = c3.text_input("رقم الهاتف")
            c4, c5, c6 = st.columns(3)
            gov = c4.text_input("المحافظة")
            qualify = c5.text_input("المؤهل/الإجازة")
            exp = c6.number_input("سنوات الخبرة", min_value=0, max_value=60, value=0)
            c7, c8, c9 = st.columns(3)
            teaches = c7.selectbox("الفئة التي يدرّسها", [""] + state.lk("age_cat"))
            hourly = c8.number_input("سعر الساعة (ج.م) *", min_value=0, value=35, step=5)
            contract = c9.selectbox("حالة التعاقد", state.lk("contract") or ["نشط"])
            special = st.text_input("مميز في")
            notes = st.text_area("ملاحظات", height=60)
            submitted = st.form_submit_button("💾 حفظ المحفظ")

        if submitted:
            if not name:
                st.error("الاسم مطلوب.")
                return
            if phone and not is_valid_egypt_phone(phone):
                st.error("رقم الهاتف غير صحيح.")
                return
            row = {
                Teacher.CODE: next_code, Teacher.NAME: name, Teacher.GENDER: gender,
                Teacher.PHONE: clean_phone(phone), Teacher.WHATSAPP: clean_phone(phone),
                Teacher.GOV: gov, Teacher.QUALIFY: qualify, Teacher.EXPERIENCE: exp,
                Teacher.TEACHES: teaches, Teacher.HOURLY: hourly, Teacher.CONTRACT: contract,
                Teacher.START: date.today(), Teacher.SPECIAL: special, Teacher.NOTES: notes,
                Teacher.DISPLAY: make_display(next_code, name),
            }
            if not can:
                st.json({k: str(v) for k, v in row.items()})
                return
            try:
                io.append_row("teachers", row)
                state.get_data(force=True)
                st.success(f"✅ تم حفظ المحفظ {name} بالكود {next_code}.")
            except Exception as e:
                st.error(f"تعذّر الحفظ: {e}")
