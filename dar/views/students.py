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
    ui.guide("عن هذه الشاشة", """
**ما هي؟** كل بيانات الطلاب: التسجيل، تعديل الحالة والفرع والسورة الحالية، أو الحذف.

**متى تستخدمها؟**
- عند وصول طالب جديد للتسجيل لأول مرة.
- عند تغيّر حالة طالب (إيقاف مؤقت، تجميد، إنهاء اشتراك).
- عند البحث عن بيانات طالب معيّن (هاتف ولي الأمر، الفرع، السورة الحالية).

**الخطوة التالية:** بعد تسجيل الطالب هنا، اذهبي إلى «📝 التسجيلات» لربطه بمحفظة
وتحديد جدوله — هذا ما يجعله يظهر لاحقًا في «الحصص والإدخال».
""")
    data = state.get_data()
    students, parents = data["students"], data["parents"]
    t_list, t_add, t_edit = st.tabs(["📋 قائمة الطلاب", "➕ إضافة طالب", "✏️ تعديل / حذف"])

    # ── القائمة ──────────────────────────────────────────────────────────────
    with t_list:
        ui.guide("متى تستخدم هذا التبويب؟",
                "للبحث عن طالب بالاسم أو الكود، أو الفلترة حسب حالة الاشتراك/الفئة العمرية، "
                "وتحميل القائمة كملف CSV لأي استخدام خارجي (تقارير، أرشفة).")
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
        ui.guide("متى تستخدم هذا التبويب؟",
                "عند تسجيل طالب جديد لم يسبق تسجيله. يمكنك ربطه بولي أمر مسجَّل مسبقًا "
                "أو إنشاء ولي أمر جديد في نفس الخطوة. الكود يُنشأ تلقائيًا — لا تكتبيه بنفسك.")
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
            study = c5.selectbox("نوع الدراسة", [""] + state.study_type_options())
            level = c6.selectbox("المستوى", [""] + state.lk("levels"))

            c7, c8, c9 = st.columns(3)
            surah = c7.selectbox("السورة الحالية", [""] + state.lk("surahs"))
            status = c8.selectbox("حالة الاشتراك", state.lk("sub_status") or ["نشط"])
            branch = c9.selectbox("الفرع", [""] + state.branch_names())

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
                Student.STUDY_TYPE: study, Student.BRANCH: branch,
                Student.LEVEL: level, Student.SURAH: surah,
                Student.STATUS: status,
                Student.SUB_SYSTEM: "أونلاين" if branch == "أونلاين" else "حضوري",
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

    # ── تعديل / حذف ────────────────────────────────────────────────────────────
    with t_edit:
        ui.guide("متى تستخدم هذا التبويب؟",
                "لتعديل بيانات طالب موجود (مثل تغيير حالة الاشتراك عند التوقف، أو تحديث "
                "السورة الحالية والمستوى)، أو لحذف طالب نهائيًا. **تنبيه:** الحذف لا يحذف "
                "تسجيله أو حصصه تلقائيًا — احذفي تلك من شاشتي «التسجيلات» و«الحصص» إن لزم.")
        can = state.write_banner()
        if students.empty:
            st.info("لا يوجد طلاب لتعديلهم.")
            return
        s_opts = options_from(students, Student.CODE, Student.NAME)
        sel = st.selectbox("اختر الطالب", [o[0] for o in s_opts], key="stu_edit_sel")
        scode = code_of(sel)
        srow = students[students[Student.CODE] == scode]
        srow = srow.iloc[0].to_dict() if not srow.empty else {}

        def _idx(lst, val):
            return lst.index(val) if val in lst else 0

        c1, c2, c3 = st.columns(3)
        e_name = c1.text_input("الاسم الكامل", value=srow.get(Student.NAME, ""), key="se_name")
        cats = [""] + state.lk("age_cat")
        e_cat = c2.selectbox("الفئة", cats, index=_idx(cats, srow.get(Student.CATEGORY, "")), key="se_cat")
        surs = [""] + state.lk("surahs")
        e_sur = c3.selectbox("السورة الحالية", surs, index=_idx(surs, srow.get(Student.SURAH, "")), key="se_sur")

        c4, c5, c6 = st.columns(3)
        studs = [""] + state.study_type_options()
        e_study = c4.selectbox("نوع الدراسة", studs, index=_idx(studs, srow.get(Student.STUDY_TYPE, "")), key="se_study")
        brs = [""] + state.branch_names()
        e_branch = c5.selectbox("الفرع", brs, index=_idx(brs, srow.get(Student.BRANCH, "")), key="se_branch")
        stts = state.lk("sub_status") or ["نشط", "موقوف", "تجميد مؤقت"]
        e_status = c6.selectbox("حالة الاشتراك", stts, index=_idx(stts, srow.get(Student.STATUS, "")), key="se_status")

        e_stop = st.text_input("سبب الإيقاف", value=srow.get(Student.STOP_REASON, ""), key="se_stop")
        e_notes = st.text_input("ملاحظات", value=srow.get(Student.NOTES, ""), key="se_notes")

        b1, b2 = st.columns(2)
        if b1.button("💾 حفظ التعديلات", disabled=not can, key="se_save"):
            updates = {
                Student.NAME: e_name, Student.CATEGORY: e_cat, Student.SURAH: e_sur,
                Student.STUDY_TYPE: e_study, Student.BRANCH: e_branch, Student.STATUS: e_status,
                Student.STOP_REASON: e_stop, Student.NOTES: e_notes,
                Student.DISPLAY: make_display(scode, e_name),
            }
            try:
                io.update_row_by_code("students", Student.CODE, scode, updates)
                state.get_data(force=True)
                st.success(f"✅ تم تعديل بيانات {e_name}.")
            except Exception as e:
                st.error(f"تعذّر التعديل: {e}")

        with b2.expander("🗑️ حذف هذا الطالب"):
            st.warning("سيُحذف الطالب نهائيًا. (لا يُحذف تسجيله أو حصصه تلقائيًا)")
            if st.button("تأكيد الحذف", disabled=not can, key="se_del"):
                try:
                    io.delete_row_by_code("students", Student.CODE, scode)
                    state.get_data(force=True)
                    st.success(f"🗑️ تم حذف الطالب {scode}.")
                except Exception as e:
                    st.error(f"تعذّر الحذف: {e}")
