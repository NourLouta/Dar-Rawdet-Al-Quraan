# -*- coding: utf-8 -*-
"""الطلاب — قائمة + إضافة/تعديل بنماذج ذكية."""
from __future__ import annotations
from datetime import date

import pandas as pd
import streamlit as st

from .. import ui, state
from .. import sheets_io as io
from ..schema import (
    Student, Parent, options_from, code_of, make_display, clean_phone,
    is_valid_egypt_phone, to_date,
)


def _age_from_birth(b):
    d = to_date(b)
    if not d:
        return ""
    today = date.today()
    return today.year - d.year - ((today.month, today.day) < (d.month, d.day))


def render():
    ui.header("👨‍🎓 الطلاب", "إدارة بيانات الطلاب")
    data = state.get_data()
    students, parents = data["students"], data["parents"]
    t_list, t_add = st.tabs(["📋 قائمة الطلاب", "➕ إضافة طالب"])

    # ── القائمة ──────────────────────────────────────────────────────────────
    with t_list:
        if students.empty:
            st.info("لا يوجد طلاب بعد.")
        else:
            c1, c2, c3 = st.columns(3)
            q = c1.text_input("🔍 بحث بالاسم/الكود")
            statuses = ["الكل"] + state.lk("sub_status")
            stt = c2.selectbox("الحالة", statuses)
            cats = ["الكل"] + state.lk("age_cat")
            cat = c3.selectbox("الفئة", cats)
            df = students.copy()
            if q:
                m = pd.Series(False, index=df.index)
                for c in (Student.NAME, Student.CODE):
                    if c in df.columns:
                        m |= df[c].astype(str).str.contains(q, case=False, na=False)
                df = df[m]
            if stt != "الكل" and Student.STATUS in df.columns:
                df = df[df[Student.STATUS].astype(str).str.contains(stt, na=False)]
            if cat != "الكل" and Student.CATEGORY in df.columns:
                df = df[df[Student.CATEGORY] == cat]
            show_cols = [c for c in [Student.CODE, Student.NAME, Student.CATEGORY, Student.AGE,
                                     Student.GENDER, Student.LEVEL, Student.SURAH, Student.STATUS,
                                     Student.SUB_VALUE, Student.PARENT_NAME] if c in df.columns]
            st.caption(f"عدد النتائج: {len(df)}")
            ui.display_table(df[show_cols], download_name="الطلاب.csv")

    # ── إضافة ────────────────────────────────────────────────────────────────
    with t_add:
        can = state.write_banner()
        next_code = io.next_code("student", students, Student.CODE)
        st.markdown(f"**الكود الجديد:** `{next_code}`")

        p_opts = options_from(parents, Parent.CODE, Parent.NAME)
        p_labels = ["➕ ولي أمر جديد"] + [o[0] for o in p_opts]

        with st.form("add_student", clear_on_submit=False):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("الاسم الكامل *")
            birth = c2.date_input("تاريخ الميلاد", value=None, min_value=date(2005, 1, 1),
                                  max_value=date.today(), format="YYYY-MM-DD")
            gender = c3.selectbox("النوع", [""] + state.lk("gender"))

            c4, c5, c6 = st.columns(3)
            category = c4.selectbox("الفئة", [""] + state.lk("age_cat"))
            study = c5.selectbox("نوع الدراسة", [""] + state.lk("study_type"))
            level = c6.selectbox("المستوى", [""] + state.lk("levels"))

            c7, c8, c9 = st.columns(3)
            surah = c7.selectbox("السورة الحالية", [""] + state.lk("surahs"))
            status = c8.selectbox("حالة الاشتراك", state.lk("sub_status") or ["نشط"])
            sub_sys = c9.selectbox("نظام الاشتراك", ["أونلاين", "حضوري"])

            st.markdown("##### 👨‍👩‍👧 ولي الأمر")
            parent_sel = st.selectbox("اختر ولي أمر مسجّل أو أنشئ جديدًا", p_labels)
            pc1, pc2, pc3 = st.columns(3)
            new_p_name = pc1.text_input("اسم ولي الأمر (جديد)", disabled=(parent_sel != "➕ ولي أمر جديد"))
            new_p_phone = pc2.text_input("هاتف ولي الأمر (جديد)", disabled=(parent_sel != "➕ ولي أمر جديد"))
            relation = pc3.selectbox("صلة القرابة", [""] + state.lk("relation"))

            notes = st.text_area("ملاحظات", height=70)
            submitted = st.form_submit_button("💾 حفظ الطالب")

        if submitted:
            if not name:
                st.error("الاسم مطلوب.")
                return
            # ولي الأمر
            if parent_sel == "➕ ولي أمر جديد":
                if not new_p_name:
                    st.error("اسم ولي الأمر الجديد مطلوب.")
                    return
                if new_p_phone and not is_valid_egypt_phone(new_p_phone):
                    st.error("رقم هاتف ولي الأمر غير صحيح (مثال: 01XXXXXXXXX).")
                    return
                p_code = io.next_code("parent", parents, Parent.CODE)
                p_name = new_p_name
                p_phone = clean_phone(new_p_phone)
                if can:
                    io.append_row("parents", {
                        Parent.CODE: p_code, Parent.NAME: p_name, Parent.PHONE: p_phone,
                        Parent.WHATSAPP: p_phone, Parent.REG_DATE: date.today(),
                        Parent.N_KIDS: 1, Parent.DISPLAY: make_display(p_code, p_name),
                    })
            else:
                p_code = code_of(parent_sel)
                prow = parents[parents[Parent.CODE] == p_code]
                p_name = prow.iloc[0][Parent.NAME] if not prow.empty else ""
                p_phone = prow.iloc[0].get(Parent.PHONE, "") if not prow.empty else ""

            row = {
                Student.CODE: next_code, Student.NAME: name,
                Student.BIRTH: birth or "", Student.AGE: _age_from_birth(birth),
                Student.GENDER: gender, Student.CATEGORY: category,
                Student.PARENT_CODE: make_display(p_code, p_name), Student.RELATION: relation,
                Student.PARENT_NAME: p_name, Student.PARENT_PHONE: p_phone,
                Student.STUDY_TYPE: study, Student.LEVEL: level, Student.SURAH: surah,
                Student.STATUS: status, Student.SUB_SYSTEM: sub_sys,
                Student.REG_DATE: date.today(), Student.NOTES: notes,
                Student.DISPLAY: make_display(next_code, name),
            }
            if not can:
                st.info("وضع القراءة فقط — هذه معاينة للسجل الذي كان سيُحفظ:")
                st.json({k: str(v) for k, v in row.items()})
                return
            try:
                io.append_row("students", row)
                state.get_data(force=True)
                st.success(f"✅ تم حفظ الطالب {name} بالكود {next_code}.")
            except Exception as e:
                st.error(f"تعذّر الحفظ: {e}")
