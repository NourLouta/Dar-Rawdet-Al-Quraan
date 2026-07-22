# -*- coding: utf-8 -*-
"""التقييمات — رضا أولياء الأمور + ملخص تقييمات المحفظين + روابط النماذج."""
from __future__ import annotations
from datetime import date

import pandas as pd
import streamlit as st

from .. import ui, state
from .. import sheets_io as io
from ..schema import (
    ParentFeedback, Student, Session, options_from, code_of, make_display,
)

RATING_SCORE = {"ممتاز": 5, "جيد جداً": 4, "جيد": 3, "مقبول": 2, "ضعيف": 1}


def _forms_links():
    try:
        import streamlit as st
        f = st.secrets.get("forms", {})
        return f.get("parent", ""), f.get("teacher", "")
    except Exception:
        return "", ""


def render():
    ui.header("⭐ التقييمات والمتابعة", "رضا أولياء الأمور وتقييم المحفظين للأداء")
    ui.guide("عن هذه الشاشة", """
**ما هي؟** متابعة الجودة من طرفين: رضا أولياء الأمور عن الخدمة، وتقييم أداء
الطلاب الذي تسجّله المحفظة بعد كل حصة (من شاشة «الحصص»).

**متى تستخدمها؟**
- شهريًا: لتسجيل رأي ولي أمر (عبر مكالمة أو واتساب) إن لم يملأ النموذج بنفسه.
- لمراجعة متوسط تقييم كل محفظة، أو أكثر الطلاب رضا أو الأقل.
- لمشاركة روابط نماذج Google مع المعلمين وأولياء الأمور ليملأوها بأنفسهم.
""")
    data = state.get_data()
    students, sessions = data["students"], data["sessions"]
    pfb = data.get("pfeedback", pd.DataFrame())

    t_parent, t_summary, t_forms = st.tabs(["👨‍👩‍👧 رأي ولي الأمر", "📊 ملخص التقييمات", "🔗 نماذج المشاركة"])

    # ── إدخال رأي ولي الأمر ─────────────────────────────────────────────────────
    with t_parent:
        ui.guide("متى تستخدم هذا التبويب؟",
                "لتسجيل رأي ولي أمر يدويًا (بعد مكالمة أو رسالة واتساب) — تقييم عام من 1 "
                "إلى 10 ومستوى الرضا وملاحظات. البديل: مشاركة نموذج Google من تبويب "
                "«نماذج المشاركة» ليملأه ولي الأمر بنفسه دون تدخل منك.")
        can = state.write_banner()
        if students.empty:
            st.info("لا يوجد طلاب.")
        else:
            s_opts = options_from(students, Student.CODE, Student.NAME)
            with st.form("parent_fb"):
                c1, c2 = st.columns(2)
                s_lbl = c1.selectbox("الطالب", [o[0] for o in s_opts])
                month = c2.text_input("الشهر (YYYY-MM)", value=date.today().strftime("%Y-%m"))
                c3, c4 = st.columns(2)
                score = c3.slider("التقييم العام (من 10)", 1, 10, 8)
                satis = c4.selectbox("مستوى الرضا", ["راضٍ تمامًا", "راضٍ", "محايد", "غير راضٍ"])
                notes = st.text_area("ملاحظات ولي الأمر", height=80)
                submitted = st.form_submit_button("💾 حفظ التقييم")
            if submitted:
                s_code = code_of(s_lbl)
                s_name = s_lbl.split(" — ")[-1] if " — " in s_lbl else ""
                code = io.next_code("pfeedback", pfb, ParentFeedback.CODE)
                row = {
                    ParentFeedback.CODE: code, ParentFeedback.STUDENT_CODE: s_code,
                    ParentFeedback.STUDENT_NAME: s_name, ParentFeedback.MONTH: month,
                    ParentFeedback.SCORE: score, ParentFeedback.SATISFACTION: satis,
                    ParentFeedback.NOTES: notes, ParentFeedback.DATE: date.today(),
                    ParentFeedback.SOURCE: "إدخال السكرتير",
                }
                if not can:
                    st.json({k: str(v) for k, v in row.items()})
                else:
                    try:
                        io.append_row("pfeedback", row)
                        state.get_data(force=True)
                        st.success("✅ تم حفظ تقييم ولي الأمر.")
                    except Exception as e:
                        st.error(f"تعذّر الحفظ: {e}")

            if pfb is not None and not pfb.empty:
                ui.section("أحدث آراء أولياء الأمور", icon="🗂️")
                ui.display_table(pfb.tail(15), download_name="تقييمات_اولياء_الامور.csv")

    # ── ملخص التقييمات ──────────────────────────────────────────────────────────
    with t_summary:
        ui.guide("متى تستخدم هذا التبويب؟",
                "لمراجعة شاملة: متوسط تقييم أداء كل محفظة (من تقييمات الحصص)، ومتوسط رضا "
                "أولياء الأمور لكل طالب. مفيد لمقارنة أداء المحفظين أو رصد طالب/ولي أمر يحتاج متابعة.")
        ui.section("متوسط تقييم المحفظين للأداء (من الحصص)", icon="👩‍🏫")
        if (not sessions.empty and Session.RATING in sessions.columns
                and Session.TEACHER_NAME in sessions.columns):
            df = sessions.copy()
            df["score"] = df[Session.RATING].map(RATING_SCORE)
            g = df.dropna(subset=["score"]).groupby(Session.TEACHER_NAME)["score"].agg(["mean", "count"]).reset_index()
            if not g.empty:
                g.columns = ["المحفظ", "متوسط التقييم", "عدد الحصص المقيّمة"]
                g["متوسط التقييم"] = g["متوسط التقييم"].round(2)
                ui.display_table(g.sort_values("متوسط التقييم", ascending=False))
            else:
                st.info("لا توجد حصص مقيّمة بعد — استخدم شاشة «الحصص ← تسجيل/تقييم حصة».")
        else:
            st.info("لا توجد تقييمات أداء بعد.")

        ui.section("متوسط رضا أولياء الأمور", icon="⭐")
        if (pfb is not None and not pfb.empty and ParentFeedback.SCORE in pfb.columns
                and ParentFeedback.STUDENT_NAME in pfb.columns):
            p = pfb.copy()
            p["sc"] = pd.to_numeric(p[ParentFeedback.SCORE], errors="coerce")
            g = p.dropna(subset=["sc"]).groupby(ParentFeedback.STUDENT_NAME)["sc"].mean().reset_index()
            g.columns = ["الطالب", "متوسط الرضا (من 10)"]
            g["متوسط الرضا (من 10)"] = g["متوسط الرضا (من 10)"].round(1)
            ui.display_table(g.sort_values("متوسط الرضا (من 10)", ascending=False))
        else:
            st.info("لا توجد تقييمات من أولياء الأمور بعد.")

    # ── روابط النماذج ───────────────────────────────────────────────────────────
    with t_forms:
        ui.guide("متى تستخدم هذا التبويب؟",
                "لنسخ روابط نماذج Google (تقييم ولي الأمر، تقييم المحفظة بعد الحصة) ومشاركتها "
                "عبر واتساب — بلا تسجيل دخول، تصل الإجابات تلقائيًا للنظام. راجعي SETUP.md "
                "لإعداد الروابط لأول مرة إن لم تظهر.")
        ui.section("نماذج Google للمعلمين وأولياء الأمور", icon="🔗")
        p_url, t_url = _forms_links()
        st.markdown("""
شارك الروابط التالية عبر واتساب. تتدفّق الإجابات تلقائيًا إلى أوراق الردود
في Google Sheets، ويقرأها النظام في الملخصات والتقارير. (تُضبط الروابط في الإعدادات.)
""")
        st.markdown(f"**نموذج رضا أولياء الأمور:** {p_url or '— لم يُضبط بعد (راجع SETUP.md) —'}")
        st.markdown(f"**نموذج تقييم المحفظ بعد الحصة:** {t_url or '— لم يُضبط بعد (راجع SETUP.md) —'}")
        if p_url:
            st.code(p_url)
        ui.insight("الطريقة الأسهل للمعلمين وأولياء الأمور: نموذج موبايل بدون تسجيل دخول، "
                   "والسكرتير يتابع كل شيء من هذه اللوحة.", "gold", "💡")
