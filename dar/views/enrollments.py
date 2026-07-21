# -*- coding: utf-8 -*-
"""التسجيلات — ربط الطالب بالمحفظ + النمط الأسبوعي + الأسعار (قابلة للتعديل) + تعديل/حذف."""
from __future__ import annotations
from datetime import date

import streamlit as st

from .. import ui, state
from .. import sheets_io as io
from ..config import STUDENT_HOURLY
from ..schema import (
    Enrollment, Student, Teacher, options_from, code_of, make_display,
    ARABIC_WEEKDAYS, format_day_schedule, parse_day_schedule,
)
from ..finance import teacher_hourly_rate, program_rates


def _default_rates(study, t_code, teachers):
    """أسعار البرنامج الافتراضية: الطالب من البرنامج، المحفظ من البرنامج أو ملف المحفظين."""
    ps, pt = program_rates(study)
    srate = ps if ps is not None else STUDENT_HOURLY
    trate = pt if pt is not None else teacher_hourly_rate(t_code, teachers)
    return float(srate), float(trate)


def _schedule_editor(times, key_prefix, preset_days=None, preset_sched=None):
    """محرّر الجدول الأسبوعي (أيام + وقت/مدة لكل يوم). يُرجع قائمة (يوم, وقت, دقائق)."""
    presched = {d: (t, m) for d, t, m in (preset_sched or [])}
    days = st.multiselect("أيام الأسبوع", ARABIC_WEEKDAYS,
                          default=preset_days or list(presched.keys()), key=f"{key_prefix}_days")
    st.caption("اختر الأيام، ثم حدّد وقت ومدة كل يوم (يمكن أن تختلف من يوم لآخر).")
    sched = []
    for d in days:
        cc1, cc2, cc3 = st.columns([1, 2, 2])
        cc1.markdown(f"<div style='padding-top:2rem;font-weight:700;'>{d}</div>", unsafe_allow_html=True)
        dt, dm = presched.get(d, (times[0] if times else "5:00 م", 30))
        t_idx = times.index(dt) if dt in times else 0
        durs = [30, 45, 60, 90, 120]
        m_idx = durs.index(int(dm)) if int(dm) in durs else 0
        t = cc2.selectbox(f"وقت {d}", times, index=t_idx, key=f"{key_prefix}_t_{d}")
        m = cc3.selectbox(f"مدة {d} (دقيقة)", durs, index=m_idx, key=f"{key_prefix}_m_{d}")
        sched.append((d, t, int(m)))
    return sched


def _rate_inputs(study, t_code, teachers, key_prefix, cur_s=None, cur_t=None):
    """عرض الأسعار الافتراضية مع خيار تعديلها يدويًا. يُرجع (سعر الطالب, سعر المحفظ)."""
    ds, dt = _default_rates(study, t_code, teachers)
    s_default = float(cur_s) if cur_s not in (None, "", 0) else ds
    t_default = float(cur_t) if cur_t not in (None, "", 0) else dt
    custom = st.checkbox("✏️ تعديل الأسعار يدويًا", key=f"{key_prefix}_custom",
                         value=(cur_s not in (None, "", 0)) or (cur_t not in (None, "", 0)))
    if custom:
        rc1, rc2 = st.columns(2)
        srate = rc1.number_input("سعر ساعة الطالب (ج.م)", min_value=0.0, value=s_default, step=5.0, key=f"{key_prefix}_sr")
        trate = rc2.number_input("سعر ساعة المحفظ (ج.م)", min_value=0.0, value=t_default, step=5.0, key=f"{key_prefix}_tr")
    else:
        srate, trate = ds, dt
        st.caption(f"💰 أسعار البرنامج: الطالب **{ds:.0f}** ج.م/س — المحفظ **{dt:.0f}** ج.م/س "
                   f"(فعّل الخيار أعلاه لتعديلها).")
    return float(srate), float(trate)


def render():
    ui.header("📝 التسجيلات", "ربط كل طالب بمحفظ + الجدول + الأسعار")
    data = state.get_data()
    enroll, students, teachers = data["enrollments"], data["students"], data["teachers"]
    times = state.lk("time_slots") or ["8:00 ص", "5:00 م"]
    t_list, t_add, t_edit = st.tabs(["📋 التسجيلات", "➕ تسجيل جديد", "✏️ تعديل / حذف"])

    # ── القائمة ───────────────────────────────────────────────────────────────
    with t_list:
        if enroll.empty:
            st.info("لا توجد تسجيلات بعد.")
        else:
            cols = [c for c in [Enrollment.CODE, Enrollment.STUDENT_NAME, Enrollment.TEACHER_NAME,
                                Enrollment.STUDY_TYPE, Enrollment.WEEK_DAYS, Enrollment.STUDENT_RATE,
                                Enrollment.TEACHER_RATE, Enrollment.STATUS] if c in enroll.columns]
            ui.display_table(enroll[cols], download_name="التسجيلات.csv")

    # ── تسجيل جديد ─────────────────────────────────────────────────────────────
    with t_add:
        can = state.write_banner()
        if students.empty or teachers.empty:
            st.warning("أضف طلابًا ومحفظين أولًا.")
        else:
            next_code = io.next_code("enrollment", enroll, Enrollment.CODE)
            st.markdown(f"**كود التسجيل:** `{next_code}`")
            s_opts = options_from(students, Student.CODE, Student.NAME)
            t_opts = options_from(teachers, Teacher.CODE, Teacher.NAME)

            c1, c2 = st.columns(2)
            s_lbl = c1.selectbox("الطالب *", [o[0] for o in s_opts], key="enr_student")
            t_lbl = c2.selectbox("المحفظ *", [o[0] for o in t_opts], key="enr_teacher")
            c3, c4, c5 = st.columns(3)
            study = c3.selectbox("نوع الدراسة (البرنامج)", state.lk("study_type") or ["قرآن"], key="enr_study")
            start = c4.date_input("تاريخ البداية", value=date.today(), format="YYYY-MM-DD", key="enr_start")
            status = c5.selectbox("حالة التسجيل", ["نشط", "موقوف", "منتهي"], key="enr_status")

            srate, trate = _rate_inputs(study, code_of(t_lbl), teachers, "enr")

            st.markdown("##### 🗓️ الجدول الأسبوعي (يُولّد الحصص تلقائيًا)")
            sched = _schedule_editor(times, "enr")
            notes = st.text_input("ملاحظات", key="enr_notes")

            if st.button("💾 حفظ التسجيل"):
                if not s_lbl or not t_lbl:
                    st.error("اختر الطالب والمحفظ.")
                elif not sched:
                    st.error("اختر يومًا واحدًا على الأقل.")
                else:
                    s_code, t_code = code_of(s_lbl), code_of(t_lbl)
                    s_name = s_lbl.split(" — ")[-1] if " — " in s_lbl else ""
                    t_name = t_lbl.split(" — ")[-1] if " — " in t_lbl else ""
                    row = {
                        Enrollment.CODE: next_code,
                        Enrollment.STUDENT_CODE: make_display(s_code, s_name),
                        Enrollment.STUDENT_NAME: s_name,
                        Enrollment.TEACHER_CODE: make_display(t_code, t_name),
                        Enrollment.TEACHER_NAME: t_name,
                        Enrollment.STUDY_TYPE: study, Enrollment.START: start, Enrollment.STATUS: status,
                        Enrollment.STUDENT_RATE: srate, Enrollment.TEACHER_RATE: trate,
                        Enrollment.WEEK_DAYS: "، ".join(d for d, _, _ in sched),
                        Enrollment.SESS_TIME: sched[0][1], Enrollment.SESS_MIN: sched[0][2],
                        Enrollment.DAY_SCHEDULE: format_day_schedule(sched),
                        Enrollment.NOTES: notes,
                        Enrollment.DISPLAY: f"{next_code} — {s_name} / {t_name}",
                    }
                    if not can:
                        st.json({k: str(v) for k, v in row.items()})
                    else:
                        try:
                            io.append_row("enrollments", row)
                            state.get_data(force=True)
                            summ = "، ".join(f"{d} {t}({m}د)" for d, t, m in sched)
                            st.success(f"✅ تم حفظ التسجيل {next_code}: {s_name} مع {t_name} — {summ} | "
                                       f"الطالب {srate:.0f} والمحفظ {trate:.0f} ج.م/س")
                        except Exception as e:
                            st.error(f"تعذّر الحفظ: {e}")

    # ── تعديل / حذف ────────────────────────────────────────────────────────────
    with t_edit:
        can = state.write_banner()
        if enroll.empty:
            st.info("لا توجد تسجيلات لتعديلها.")
        else:
            opts = [(r.get(Enrollment.DISPLAY) or r.get(Enrollment.CODE, f"صف {i}"), i)
                    for i, r in enroll.iterrows()]
            sel = st.selectbox("اختر التسجيل", [o[0] for o in opts], key="enr_edit_sel")
            row = enroll.loc[dict(opts)[sel]].to_dict()
            ecode = row.get(Enrollment.CODE, "")
            study_opts = state.lk("study_type") or ["قرآن"]
            cur_study = row.get(Enrollment.STUDY_TYPE, "") or study_opts[0]

            e1, e2 = st.columns(2)
            study2 = e1.selectbox("نوع الدراسة", study_opts,
                                  index=study_opts.index(cur_study) if cur_study in study_opts else 0, key="ee_study")
            st_opts = ["نشط", "موقوف", "منتهي"]
            cur_st = row.get(Enrollment.STATUS, "نشط")
            status2 = e2.selectbox("حالة التسجيل", st_opts,
                                   index=st_opts.index(cur_st) if cur_st in st_opts else 0, key="ee_status")

            t_code = code_of(row.get(Enrollment.TEACHER_CODE, "")) or row.get(Enrollment.TEACHER_NAME, "")
            srate2, trate2 = _rate_inputs(study2, t_code, teachers, "ee",
                                          cur_s=row.get(Enrollment.STUDENT_RATE),
                                          cur_t=row.get(Enrollment.TEACHER_RATE))

            st.markdown("##### 🗓️ تعديل الجدول الأسبوعي")
            presched = parse_day_schedule(row.get(Enrollment.DAY_SCHEDULE, ""))
            sched2 = _schedule_editor(times, "ee", preset_sched=presched)
            notes2 = st.text_input("ملاحظات", value=row.get(Enrollment.NOTES, ""), key="ee_notes")

            b1, b2 = st.columns(2)
            if b1.button("💾 حفظ التعديلات", disabled=not can):
                updates = {
                    Enrollment.STUDY_TYPE: study2, Enrollment.STATUS: status2,
                    Enrollment.STUDENT_RATE: srate2, Enrollment.TEACHER_RATE: trate2,
                    Enrollment.NOTES: notes2,
                }
                if sched2:
                    updates[Enrollment.WEEK_DAYS] = "، ".join(d for d, _, _ in sched2)
                    updates[Enrollment.SESS_TIME] = sched2[0][1]
                    updates[Enrollment.SESS_MIN] = sched2[0][2]
                    updates[Enrollment.DAY_SCHEDULE] = format_day_schedule(sched2)
                try:
                    io.update_row_by_code("enrollments", Enrollment.CODE, ecode, updates)
                    state.get_data(force=True)
                    st.success(f"✅ تم تعديل التسجيل {ecode}. (لتطبيق الجدول الجديد: أعِد توليد حصص الشهر)")
                except Exception as e:
                    st.error(f"تعذّر التعديل: {e}")

            with b2.expander("🗑️ حذف هذا التسجيل"):
                st.warning("سيُحذف التسجيل نهائيًا (لن تُحذف حصصه المولّدة).")
                if st.button("تأكيد الحذف", disabled=not can, key="ee_del"):
                    try:
                        io.delete_row_by_code("enrollments", Enrollment.CODE, ecode)
                        state.get_data(force=True)
                        st.success(f"🗑️ تم حذف التسجيل {ecode}.")
                    except Exception as e:
                        st.error(f"تعذّر الحذف: {e}")
