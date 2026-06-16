# -*- coding: utf-8 -*-
"""
الحصص والإدخال — قلب النظام الذي يلغي التكرار الشهري.

• توليد حصص الشهر لتسجيل واحد من نمطه الأسبوعي بضغطة زر.
• ترحيل شهري جماعي: توليد حصص كل التسجيلات النشطة دفعة واحدة.
• تسجيل/تقييم الحصة: حالة، تقييم الأداء، السورة، الآيات، ملاحظات المحفظ.
"""
from __future__ import annotations
import calendar
from datetime import date

import pandas as pd
import streamlit as st

from .. import ui, state
from .. import sheets_io as io
from ..config import CODE_PREFIX
from ..schema import (
    Enrollment, Session, parse_weekdays, weekday_to_pywd, parse_arabic_time,
    format_arabic_time, add_minutes, month_key, code_of, make_display,
    normalize_digits,
)


# ────────────────────────────────────────────────────────────────────────────
# 🧮 منطق التوليد
# ────────────────────────────────────────────────────────────────────────────
def _existing_keys(sessions_df: pd.DataFrame) -> set:
    keys = set()
    if sessions_df is None or sessions_df.empty:
        return keys
    for _, r in sessions_df.iterrows():
        ec = str(code_of(r.get(Session.ENROLL_CODE, "")) or r.get(Session.ENROLL_CODE, "")).strip()
        d = str(r.get(Session.DATE, "")).strip()[:10]
        if ec and d:
            keys.add((ec, d))
    return keys


def _next_session_num(sessions_df: pd.DataFrame) -> int:
    code = io.next_code("session", sessions_df, Session.CODE)
    prefix = CODE_PREFIX["session"][0]
    try:
        return int(normalize_digits(code[len(prefix):]))
    except Exception:
        return 1


def generate_rows(enr_row: dict, year: int, month: int, default_status: str,
                  existing_keys: set, start_num: int):
    """توليد صفوف حصص لتسجيل واحد في شهر معيّن حسب نمطه الأسبوعي."""
    days = parse_weekdays(enr_row.get(Enrollment.WEEK_DAYS, ""))
    if not days:
        return [], start_num
    pywds = {weekday_to_pywd(d) for d in days}
    minutes = int(state.num(enr_row.get(Enrollment.SESS_MIN), 30))
    stime = parse_arabic_time(enr_row.get(Enrollment.SESS_TIME))
    etime = add_minutes(stime, minutes) if stime else None
    e_code = str(enr_row.get(Enrollment.CODE, "")).strip()
    s_code = code_of(enr_row.get(Enrollment.STUDENT_CODE, "")) or ""
    s_name = enr_row.get(Enrollment.STUDENT_NAME, "")
    t_code = code_of(enr_row.get(Enrollment.TEACHER_CODE, "")) or ""
    t_name = enr_row.get(Enrollment.TEACHER_NAME, "")
    prefix, width = CODE_PREFIX["session"]

    rows, num = [], start_num
    ndays = calendar.monthrange(year, month)[1]
    for day in range(1, ndays + 1):
        d = date(year, month, day)
        if d.weekday() not in pywds:
            continue
        if (e_code, d.isoformat()) in existing_keys:
            continue
        rows.append({
            Session.CODE: f"{prefix}{num:0{width}d}",
            Session.ENROLL_CODE: enr_row.get(Enrollment.DISPLAY) or e_code,
            Session.STUDENT_CODE: s_code, Session.STUDENT_NAME: s_name,
            Session.TEACHER_CODE: t_code, Session.TEACHER_NAME: t_name,
            Session.DATE: d, Session.MONTH: f"{year}-{month:02d}",
            Session.START_TIME: format_arabic_time(stime),
            Session.END_TIME: format_arabic_time(etime),
            Session.DURATION: minutes, Session.STATUS: default_status,
        })
        existing_keys.add((e_code, d.isoformat()))
        num += 1
    return rows, num


# ────────────────────────────────────────────────────────────────────────────
# 🖥️ الواجهة
# ────────────────────────────────────────────────────────────────────────────
def render():
    ui.header("📅 الحصص والإدخال", "توليد جداول الحصص وتسجيل التقييمات دون تكرار")
    data = state.get_data()
    sessions, enroll = data["sessions"], data["enrollments"]
    t_gen, t_roll, t_log = st.tabs(["⚡ توليد حصص تسجيل", "🔁 ترحيل شهري جماعي", "✍️ تسجيل/تقييم حصة"])

    today = date.today()
    statuses = state.lk("sess_status") or ["تمت"]

    # ── توليد لتسجيل واحد ──────────────────────────────────────────────────────
    with t_gen:
        can = state.write_banner()
        if enroll.empty:
            st.warning("أضف تسجيلًا بنمط أسبوعي أولًا.")
        else:
            opts = [(r.get(Enrollment.DISPLAY) or r.get(Enrollment.CODE, f"صف {i}"), i)
                    for i, r in enroll.iterrows()]
            sel = st.selectbox("اختر التسجيل", [o[0] for o in opts])
            idx = dict(opts)[sel]
            enr = enroll.loc[idx].to_dict()
            c1, c2, c3 = st.columns(3)
            year = c1.number_input("السنة", min_value=2024, max_value=2100, value=today.year)
            month = c2.selectbox("الشهر", list(range(1, 13)), index=today.month - 1)
            dflt = c3.selectbox("الحالة الافتراضية", statuses)
            st.info(f"النمط: أيام [{enr.get(Enrollment.WEEK_DAYS,'—')}] | "
                    f"الوقت {enr.get(Enrollment.SESS_TIME,'—')} | "
                    f"{enr.get(Enrollment.SESS_MIN,'—')} دقيقة")
            preview, _ = generate_rows(enr, int(year), int(month), dflt,
                                       _existing_keys(sessions), _next_session_num(sessions))
            st.caption(f"سيتم توليد **{len(preview)}** حصة (مع تجاهل المكرر).")
            if preview:
                ui.display_table(pd.DataFrame([{
                    "التاريخ": r[Session.DATE], "الوقت": r[Session.START_TIME],
                    "المدة": r[Session.DURATION], "الحالة": r[Session.STATUS],
                } for r in preview]), max_height="240px")
            if st.button("⚡ توليد الحصص", disabled=not (can and preview)):
                try:
                    n = io.append_rows("sessions", preview)
                    state.get_data(force=True)
                    st.success(f"✅ تم توليد {n} حصة للشهر {year}-{month:02d}.")
                except Exception as e:
                    st.error(f"تعذّر التوليد: {e}")

    # ── ترحيل جماعي ────────────────────────────────────────────────────────────
    with t_roll:
        can = state.write_banner()
        st.markdown("توليد حصص شهر كامل **لكل التسجيلات النشطة** دفعة واحدة.")
        c1, c2 = st.columns(2)
        year = c1.number_input("السنة", min_value=2024, max_value=2100, value=today.year, key="roll_y")
        month = c2.selectbox("الشهر", list(range(1, 13)), index=today.month - 1, key="roll_m")
        dflt = st.selectbox("الحالة الافتراضية", statuses, key="roll_s")
        active = enroll
        if Enrollment.STATUS in enroll.columns:
            active = enroll[enroll[Enrollment.STATUS].astype(str).str.contains("نشط", na=False)]
        st.caption(f"عدد التسجيلات النشطة: {len(active)}")

        if st.button("🔁 توليد حصص الشهر للجميع", disabled=not can):
            keys = _existing_keys(sessions)
            num = _next_session_num(sessions)
            all_rows, skipped = [], 0
            for _, r in active.iterrows():
                rows, num = generate_rows(r.to_dict(), int(year), int(month), dflt, keys, num)
                if not rows and not parse_weekdays(r.get(Enrollment.WEEK_DAYS, "")):
                    skipped += 1
                all_rows.extend(rows)
            if not all_rows:
                st.warning("لا توجد حصص جديدة للتوليد (إما مكرّرة أو بلا نمط أسبوعي).")
            else:
                try:
                    n = io.append_rows("sessions", all_rows)
                    state.get_data(force=True)
                    msg = f"✅ تم توليد {n} حصة لـ {year}-{month:02d}."
                    if skipped:
                        msg += f" (تُجوهل {skipped} تسجيل بلا نمط أسبوعي)"
                    st.success(msg)
                except Exception as e:
                    st.error(f"تعذّر التوليد: {e}")

    # ── تسجيل/تقييم حصة ────────────────────────────────────────────────────────
    with t_log:
        can = state.write_banner()
        if sessions.empty:
            st.info("لا توجد حصص لتسجيلها بعد.")
            return
        months = state.months_available(sessions)
        c1, c2 = st.columns(2)
        mon = c1.selectbox("الشهر", months, key="log_month")
        sub = sessions[sessions[Session.MONTH].astype(str) == mon] if Session.MONTH in sessions.columns else sessions
        teachers_list = ["الكل"] + sorted(sub[Session.TEACHER_NAME].dropna().unique().tolist())
        tf = c2.selectbox("المحفظ", teachers_list, key="log_teacher")
        if tf != "الكل":
            sub = sub[sub[Session.TEACHER_NAME] == tf]
        if sub.empty:
            st.info("لا توجد حصص مطابقة.")
            return
        # اختيار حصة
        def _lbl(r):
            return f"{r[Session.CODE]} | {r.get(Session.DATE,'')} {r.get(Session.START_TIME,'')} | {r.get(Session.STUDENT_NAME,'')}"
        labels = {(_lbl(r)): r[Session.CODE] for _, r in sub.iterrows()}
        sel = st.selectbox("اختر الحصة", list(labels.keys()))
        code = labels[sel]
        cur = sub[sub[Session.CODE] == code].iloc[0].to_dict()

        with st.form("log_session"):
            c1, c2, c3 = st.columns(3)
            status = c1.selectbox("حالة الحصة", statuses,
                                  index=(statuses.index(cur.get(Session.STATUS)) if cur.get(Session.STATUS) in statuses else 0))
            rating = c2.selectbox("تقييم الأداء", [""] + state.lk("rating"))
            surah = c3.selectbox("السورة", [""] + state.lk("surahs"))
            c4, c5, c6 = st.columns(3)
            ay_from = c4.text_input("من آية")
            ay_to = c5.text_input("إلى آية")
            amount = c6.selectbox("مقدار الحفظ", [""] + state.lk("amount"))
            cancel = st.text_input("سبب الإلغاء (إن وُجد)")
            notes = st.text_area("ملاحظات المحفظ", height=70)
            submitted = st.form_submit_button("💾 حفظ التقييم")

        if submitted:
            updates = {
                Session.STATUS: status, Session.RATING: rating, Session.SURAH: surah,
                Session.AYAH_FROM: ay_from, Session.AYAH_TO: ay_to, Session.AMOUNT: amount,
                Session.CANCEL_RSN: cancel, Session.NOTES: notes,
            }
            updates = {k: v for k, v in updates.items() if v != ""}
            if not can:
                st.json({Session.CODE: code, **{k: str(v) for k, v in updates.items()}})
                return
            try:
                ok = io.update_row_by_code("sessions", Session.CODE, code, updates)
                state.get_data(force=True)
                st.success("✅ تم حفظ التقييم.") if ok else st.error("لم يُعثر على الحصة.")
            except Exception as e:
                st.error(f"تعذّر الحفظ: {e}")
