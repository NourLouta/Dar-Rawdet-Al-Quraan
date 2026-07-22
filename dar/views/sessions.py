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


def _weekly_map(enr_row: dict) -> dict:
    """
    خريطة {رقم يوم بايثون: (وقت, دقائق)} للنمط الأسبوعي.
    يفضّل «جدول الأيام» (وقت/مدة لكل يوم)، وإلا يستخدم وقتًا/مدة موحّدة لكل الأيام.
    """
    from ..schema import parse_day_schedule
    sched = parse_day_schedule(enr_row.get(Enrollment.DAY_SCHEDULE, ""))
    out = {}
    if sched:
        for day, t, m in sched:
            wd = weekday_to_pywd(day)
            if wd is not None:
                out[wd] = (t, int(m))
        return out
    # احتياطي: وقت/مدة موحّدة
    days = parse_weekdays(enr_row.get(Enrollment.WEEK_DAYS, ""))
    minutes = int(state.num(enr_row.get(Enrollment.SESS_MIN), 30))
    t = enr_row.get(Enrollment.SESS_TIME, "")
    for d in days:
        wd = weekday_to_pywd(d)
        if wd is not None:
            out[wd] = (t, minutes)
    return out


def generate_rows(enr_row: dict, year: int, month: int, default_status: str,
                  existing_keys: set, start_num: int, start_from=None):
    """
    توليد صفوف حصص لتسجيل واحد في شهر معيّن — يدعم وقتًا/مدة مختلفة لكل يوم.
    start_from: إن حُدِّد تاريخ، تُتجاهل الأيام قبله (تبدأ الحصص من هذا التاريخ).
    """
    wmap = _weekly_map(enr_row)
    if not wmap:
        return [], start_num
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
        if start_from and d < start_from:
            continue
        if d.weekday() not in wmap:
            continue
        if (e_code, d.isoformat()) in existing_keys:
            continue
        time_str, minutes = wmap[d.weekday()]
        stime = parse_arabic_time(time_str)
        etime = add_minutes(stime, minutes) if stime else None
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
    ui.guide("عن هذه الشاشة", """
**ما هي؟** قلب النظام: تحوّل جدول التسجيل الأسبوعي إلى حصص فعلية، وتتيح إضافة حصص
استثنائية، وإلغاء/تعديل حصص موجودة، وتسجيل تقييم الأداء بعد كل حصة.

**متى تستخدمها؟**
- بعد إنشاء أي تسجيل جديد (أو أول كل شهر) — لتوليد حصصه.
- عند وجود يوم إضافي أو تعويضي خارج الجدول الثابت.
- عند إلغاء حصة أو تغيّر ميعادها.
- بعد انتهاء كل حصة فعليًا — لتسجيل تقييمها.

**لماذا لا يظهر الطالب أحيانًا هنا؟** الحصص لا تُنشأ تلقائيًا بمجرد إضافة التسجيل —
يجب توليدها أولًا من تبويب «⚡ توليد حصص تسجيل» أو «🔁 ترحيل شهري جماعي».
""")
    data = state.get_data()
    sessions, enroll = data["sessions"], data["enrollments"]
    t_gen, t_single, t_roll, t_cancel, t_log = st.tabs([
        "⚡ توليد حصص تسجيل", "➕ إضافة حصة مفردة", "🔁 ترحيل شهري جماعي",
        "🗓️ إلغاء/تعديل حالات الحصص", "✍️ تسجيل/تقييم حصة"])

    today = date.today()
    statuses = state.lk("sess_status") or ["تمت"]

    # ── توليد لتسجيل واحد ──────────────────────────────────────────────────────
    with t_gen:
        ui.guide("متى تستخدم هذا التبويب؟", """
لتوليد كل حصص الشهر لتسجيل واحد بضغطة زر، اعتمادًا على جدوله الأسبوعي المحفوظ.
اختاري «من أول الشهر» في الحالة المعتادة، أو «من تاريخ محدّد» لو الطالب انضمّ في
منتصف الشهر (لن تُحسب أيام قبل هذا التاريخ). المولّد يتجاهل أي حصة موجودة مسبقًا
لنفس التسجيل والتاريخ تلقائيًا — لا خطر من التكرار.
""")
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

            # خيار بداية التوليد: من أول الشهر أو من تاريخ محدد (للطلاب المنضمّين في منتصف الشهر)
            start_mode = st.radio("بداية التوليد", ["من أول الشهر", "من تاريخ محدّد"],
                                  horizontal=True, key="gen_start_mode")
            start_from = None
            if start_mode == "من تاريخ محدّد":
                default_d = date(int(year), int(month), min(today.day, 28))
                start_from = st.date_input("ابدأ الحصص من تاريخ", value=default_d, format="YYYY-MM-DD",
                                           key="gen_start_date")

            from ..schema import parse_day_schedule
            _sched = parse_day_schedule(enr.get(Enrollment.DAY_SCHEDULE, ""))
            if _sched:
                st.info("الجدول: " + "، ".join(f"{d} {t} ({m}د)" for d, t, m in _sched))
            else:
                st.info(f"النمط: أيام [{enr.get(Enrollment.WEEK_DAYS,'—')}] | "
                        f"الوقت {enr.get(Enrollment.SESS_TIME,'—')} | "
                        f"{enr.get(Enrollment.SESS_MIN,'—')} دقيقة")
            preview, _ = generate_rows(enr, int(year), int(month), dflt,
                                       _existing_keys(sessions), _next_session_num(sessions),
                                       start_from=start_from)
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

    # ── إضافة حصة مفردة (يوم إضافي/تعويضي خارج النمط) ────────────────────────────
    with t_single:
        ui.guide("متى تستخدم هذا التبويب؟", """
لإضافة حصة **واحدة** خارج الجدول الأسبوعي الثابت — مثل يوم إضافي في أسبوع مكثّف،
أو تعويض حصة فائتة. لا تستخدمي هذا لتعديل الجدول الدائم؛ عدّلي التسجيل بدلًا من ذلك
لو كان التغيير سيتكرر كل أسبوع. **حماية تلقائية:** لن تُضاف حصة مكرَّرة لنفس
التسجيل في نفس التاريخ.
""")
        can = state.write_banner()
        if enroll.empty:
            st.warning("أضف تسجيلًا أولًا.")
        else:
            st.caption("لإضافة حصة واحدة خارج الجدول الأسبوعي (مثل يوم إضافي أو تعويض).")
            opts = [(r.get(Enrollment.DISPLAY) or r.get(Enrollment.CODE, f"صف {i}"), i)
                    for i, r in enroll.iterrows()]
            sel1 = st.selectbox("اختر التسجيل", [o[0] for o in opts], key="single_enr")
            enr1 = enroll.loc[dict(opts)[sel1]].to_dict()
            times = state.lk("time_slots") or ["5:00 م"]
            sc1, sc2, sc3, sc4 = st.columns(4)
            s_date = sc1.date_input("التاريخ", value=today, format="YYYY-MM-DD", key="single_date")
            s_time = sc2.selectbox("الوقت", times, key="single_time")
            s_min = sc3.selectbox("المدة (دقيقة)", [30, 45, 60, 90, 120], key="single_min")
            s_stat = sc4.selectbox("الحالة", statuses, key="single_stat")
            if st.button("➕ إضافة الحصة", disabled=not can):
                from ..schema import parse_arabic_time, format_arabic_time, add_minutes, month_key
                stime = parse_arabic_time(s_time)
                etime = add_minutes(stime, int(s_min)) if stime else None
                e_code = str(enr1.get(Enrollment.CODE, "")).strip()
                # منع التكرار لنفس التسجيل/التاريخ
                if (e_code, s_date.isoformat()) in _existing_keys(sessions):
                    st.warning("توجد حصة بالفعل لهذا التسجيل في هذا التاريخ.")
                else:
                    code = f"{CODE_PREFIX['session'][0]}{_next_session_num(sessions):0{CODE_PREFIX['session'][1]}d}"
                    row = {
                        Session.CODE: code,
                        Session.ENROLL_CODE: enr1.get(Enrollment.DISPLAY) or e_code,
                        Session.STUDENT_CODE: code_of(enr1.get(Enrollment.STUDENT_CODE, "")),
                        Session.STUDENT_NAME: enr1.get(Enrollment.STUDENT_NAME, ""),
                        Session.TEACHER_CODE: code_of(enr1.get(Enrollment.TEACHER_CODE, "")),
                        Session.TEACHER_NAME: enr1.get(Enrollment.TEACHER_NAME, ""),
                        Session.DATE: s_date, Session.MONTH: month_key(s_date),
                        Session.START_TIME: format_arabic_time(stime),
                        Session.END_TIME: format_arabic_time(etime),
                        Session.DURATION: int(s_min), Session.STATUS: s_stat,
                    }
                    try:
                        io.append_row("sessions", row)
                        state.get_data(force=True)
                        st.success(f"✅ تمت إضافة حصة {code} بتاريخ {s_date} للطالب {row[Session.STUDENT_NAME]}.")
                    except Exception as e:
                        st.error(f"تعذّر الإضافة: {e}")

    # ── ترحيل جماعي ────────────────────────────────────────────────────────────
    with t_roll:
        ui.guide("متى تستخدم هذا التبويب؟",
                "أول كل شهر: بدل توليد حصص كل تسجيل يدويًا واحدًا تلو الآخر، هذا الزر يولّد "
                "حصص الشهر **لكل التسجيلات النشطة دفعة واحدة** من جداولها الأسبوعية المحفوظة. "
                "التسجيلات بلا جدول أسبوعي أو التي وُلِّدت حصصها مسبقًا تُتجاهل تلقائيًا.")
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

    # ── إلغاء/تعديل حالات الحصص (تحرير جماعي سريع) ──────────────────────────────
    with t_cancel:
        ui.guide("متى تستخدم هذا التبويب؟", """
عند إلغاء حصة (غياب الطالب، ظرف طارئ، تغيّر معاد) أو أي تعديل جماعي سريع على حالة
عدة حصص لطالب أو شهر معيّن. غيّري «حالة الحصة» في الجدول مباشرة (اختاري من القائمة)
واكتبي سبب الإلغاء إن وُجد، ثم احفظي. **مهم:** الحصص الملغية تُستبعد تلقائيًا من
حساب الساعات والمرتبات والإيرادات في شاشة «المالية».
""")
        can = state.write_banner()
        if sessions.empty:
            st.info("لا توجد حصص بعد.")
        else:
            months = state.months_available(sessions)
            cc1, cc2 = st.columns(2)
            mon = cc1.selectbox("الشهر", months, key="cancel_month")
            sub = sessions[sessions[Session.MONTH].astype(str) == mon] if Session.MONTH in sessions.columns else sessions
            names = ["الكل"] + sorted([n for n in sub[Session.STUDENT_NAME].dropna().unique() if str(n).strip()]) \
                if Session.STUDENT_NAME in sub.columns else ["الكل"]
            who = cc2.selectbox("الطالب", names, key="cancel_student")
            if who != "الكل":
                sub = sub[sub[Session.STUDENT_NAME] == who]
            sub = sub.sort_values(Session.DATE) if Session.DATE in sub.columns else sub

            if sub.empty:
                st.info("لا توجد حصص مطابقة.")
            else:
                st.caption("غيّر «حالة الحصة» لأي صفوف (مثلاً: ملغية - طالب) ثم اضغط حفظ التغييرات. "
                           "الحصص الملغية لا تُحتسب في الساعات أو الرواتب.")
                view_cols = [Session.CODE, Session.DATE, Session.START_TIME,
                             Session.STUDENT_NAME, Session.TEACHER_NAME,
                             Session.STATUS, Session.CANCEL_RSN]
                view_cols = [c for c in view_cols if c in sub.columns]
                editable = sub[view_cols].copy().reset_index(drop=True)
                orig = editable.copy()
                edited = st.data_editor(
                    editable, hide_index=True, use_container_width=True, height=420,
                    key="cancel_editor",
                    disabled=[Session.CODE, Session.DATE, Session.START_TIME,
                              Session.STUDENT_NAME, Session.TEACHER_NAME],
                    column_config={
                        Session.STATUS: st.column_config.SelectboxColumn(
                            Session.STATUS, options=statuses, width="medium"),
                        Session.CANCEL_RSN: st.column_config.TextColumn(Session.CANCEL_RSN),
                    },
                )
                if st.button("💾 حفظ التغييرات", disabled=not can):
                    changed = 0
                    for i in range(len(edited)):
                        code = str(edited.iloc[i][Session.CODE])
                        upd = {}
                        if str(edited.iloc[i][Session.STATUS]) != str(orig.iloc[i][Session.STATUS]):
                            upd[Session.STATUS] = edited.iloc[i][Session.STATUS]
                        if (Session.CANCEL_RSN in edited.columns and
                                str(edited.iloc[i][Session.CANCEL_RSN]) != str(orig.iloc[i][Session.CANCEL_RSN])):
                            upd[Session.CANCEL_RSN] = edited.iloc[i][Session.CANCEL_RSN]
                        if upd:
                            try:
                                io.update_row_by_code("sessions", Session.CODE, code, upd)
                                changed += 1
                            except Exception as e:
                                st.error(f"تعذّر تحديث {code}: {e}")
                    if changed:
                        state.get_data(force=True)
                        st.success(f"✅ تم تحديث {changed} حصة.")
                    else:
                        st.info("لا تغييرات لحفظها.")

    # ── تسجيل/تقييم حصة ────────────────────────────────────────────────────────
    with t_log:
        ui.guide("متى تستخدم هذا التبويب؟", """
بعد انتهاء الحصة فعليًا: سجّلي السورة، من آية إلى آية، مقدار الحفظ، تقييم أداء
الطالب، وملاحظات المحفظة. هذا التقييم يظهر لاحقًا في «تقرير الطالب» الشهري
وفي ملخص التقييمات بشاشة «⭐ التقييمات». ابحثي بالاسم إن لم تجدي الحصة مباشرة.
""")
        can = state.write_banner()
        if sessions.empty:
            st.info("ℹ️ لا تظهر الحصص هنا إلا بعد توليدها. الخطوات: **الطلاب ← التسجيلات ← ⚡ توليد حصص تسجيل**، "
                    "ثم ارجع لهذه الشاشة لتسجيل/تقييم الحصص.")
            return
        months = state.months_available(sessions)
        c1, c2 = st.columns(2)
        mon = c1.selectbox("الشهر", months, key="log_month")
        sub = sessions[sessions[Session.MONTH].astype(str) == mon] if Session.MONTH in sessions.columns else sessions
        # بحث بالطالب أو المحفظ (يحل مشكلة عدم ظهور الطالب)
        who = c2.text_input("🔍 بحث باسم الطالب أو المحفظ", key="log_search")
        if who:
            m = pd.Series(False, index=sub.index)
            for col in (Session.STUDENT_NAME, Session.TEACHER_NAME):
                if col in sub.columns:
                    m |= sub[col].astype(str).str.contains(who, case=False, na=False)
            sub = sub[m]
        if sub.empty:
            st.info("لا توجد حصص مطابقة في هذا الشهر. تأكد أنك ولّدت حصص هذا الطالب لهذا الشهر.")
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
