# -*- coding: utf-8 -*-
"""
مصدر قراءة بديل من Supabase (Postgres) — Phase A3.

يُستدعى فقط من sheets_io.read_ws() عند تفعيل read_from=supabase في
الإعدادات (مستقل تمامًا عن write_target() — لا يمكن أن يؤثر على الكتابة
بالخطأ). المخطط في Supabase منظّم (مفاتيح خارجية حقيقية، أعمدة إنجليزية)؛
هذا الملف يعيد بناء نفس الشكل المسطّح بالأعمدة العربية الذي تتوقعه كل
شاشات dar/views/*.py، بلا أي تعديل عليها — تمامًا كما يخرج من Google Sheets.
"""
from __future__ import annotations
from functools import lru_cache

import pandas as pd

from . import schema
from .schema import (
    Teacher, Parent, Student, Enrollment, Session, Program, Branch,
    ParentFeedback, make_display, format_day_schedule, ARABIC_WEEKDAYS,
)


@lru_cache(maxsize=1)
def get_client():
    import streamlit as st
    try:
        cfg = st.secrets["supabase"]
        from supabase import create_client
        return create_client(cfg["url"], cfg["service_role_key"])
    except Exception:
        return None


def read_from_supabase() -> bool:
    import streamlit as st
    try:
        return st.secrets["supabase"].get("read_from", "sheets") == "supabase"
    except Exception:
        return False


def clear_cache():
    get_client.cache_clear()


def _fetch(table: str) -> pd.DataFrame:
    sb = get_client()
    if sb is None:
        return pd.DataFrame()
    rows, offset = [], 0
    while True:
        res = sb.schema("dar").table(table).select("*").range(offset, offset + 999).execute()
        if not res.data:
            break
        rows.extend(res.data)
        offset += 1000
    return pd.DataFrame(rows)


def _s(df: pd.DataFrame, col: str) -> pd.Series:
    """عمود كنص، أو سلسلة فارغة إن لم يكن العمود موجودًا (جدول فارغ)."""
    if col in df.columns:
        return df[col].fillna("").astype(str)
    return pd.Series([""] * len(df), index=df.index)


def _n(df: pd.DataFrame, col: str) -> pd.Series:
    """عمود رقمي كنص (يحافظ على القيم الصحيحة بلا '.0')."""
    if col not in df.columns:
        return pd.Series([""] * len(df), index=df.index)
    v = pd.to_numeric(df[col], errors="coerce")
    return v.map(lambda x: "" if pd.isna(x) else (str(int(x)) if float(x).is_integer() else str(x)))


def read_branches() -> pd.DataFrame:
    df = _fetch("branches")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["branches"])
    return pd.DataFrame({
        Branch.CODE: _s(df, "code"), Branch.NAME: _s(df, "name"),
        Branch.ADDRESS: _s(df, "address"), Branch.NOTES: _s(df, "notes"),
    })


def read_programs() -> pd.DataFrame:
    df = _fetch("programs")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["programs"])
    return pd.DataFrame({
        Program.CODE: _s(df, "code"), Program.NAME: _s(df, "name"),
        Program.STUDENT_RATE: _n(df, "student_hourly_rate"),
        Program.TEACHER_RATE: _n(df, "teacher_hourly_rate"),
        Program.NOTES: _s(df, "notes"),
    })


def read_teachers() -> pd.DataFrame:
    df = _fetch("teachers")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["teachers"])
    out = pd.DataFrame({
        Teacher.CODE: _s(df, "code"), Teacher.NAME: _s(df, "full_name"),
        Teacher.GENDER: _s(df, "gender"), Teacher.PHONE: _s(df, "phone"),
        Teacher.WHATSAPP: _s(df, "whatsapp"), Teacher.GOV: _s(df, "governorate"),
        Teacher.QUALIFY: _s(df, "qualification"), Teacher.EXPERIENCE: _n(df, "experience_years"),
        Teacher.TEACHES: _s(df, "teaches_category"), Teacher.STUDY_TYPE: _s(df, "study_type"),
        Teacher.WORK_SYS: _s(df, "work_system"), Teacher.HOURLY: _n(df, "hourly_rate"),
        Teacher.MIN_SESS: _n(df, "min_sessions"), Teacher.CONTRACT: _s(df, "contract_status"),
        Teacher.START: _s(df, "start_date"), Teacher.TIMING: _s(df, "preferred_timing"),
        Teacher.PAY_METHOD: _s(df, "pay_method"), Teacher.SPECIAL: _s(df, "special_in"),
        Teacher.NOTES: _s(df, "notes"),
    })
    out[Teacher.DISPLAY] = [make_display(c, n) for c, n in zip(out[Teacher.CODE], out[Teacher.NAME])]
    return out


def read_parents() -> pd.DataFrame:
    df = _fetch("parents")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["parents"])
    students = _fetch("students")
    kids_count = (students["parent_id"].value_counts() if "parent_id" in students.columns
                  else pd.Series(dtype=int))
    out = pd.DataFrame({
        Parent.CODE: _s(df, "code"), Parent.NAME: _s(df, "full_name"),
        Parent.PHONE: _s(df, "phone"), Parent.WHATSAPP: _s(df, "whatsapp"),
        Parent.ADDRESS: _s(df, "address"), Parent.EMAIL: _s(df, "email"),
        Parent.SOURCE: _s(df, "source"), Parent.REG_DATE: _s(df, "reg_date"),
        Parent.NOTES: _s(df, "notes"),
    })
    out[Parent.N_KIDS] = [str(int(kids_count.get(i, 0))) for i in df.get("id", [])]
    out[Parent.DISPLAY] = [make_display(c, n) for c, n in zip(out[Parent.CODE], out[Parent.NAME])]
    return out


def read_students() -> pd.DataFrame:
    df = _fetch("students")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["students"])
    parents = _fetch("parents").set_index("id") if not _fetch("parents").empty else pd.DataFrame()
    branches = _fetch("branches").set_index("id") if not _fetch("branches").empty else pd.DataFrame()

    def _parent_field(pid, field):
        if parents.empty or pd.isna(pid) or int(pid) not in parents.index:
            return ""
        return str(parents.loc[int(pid), field] or "")

    def _branch_name(bid):
        if branches.empty or pd.isna(bid) or int(bid) not in branches.index:
            return ""
        return str(branches.loc[int(bid), "name"] or "")

    birth = pd.to_datetime(df.get("birth_date"), errors="coerce")
    today = pd.Timestamp.now().normalize()
    age = ((today - birth).dt.days // 365).fillna(-1).astype(int)

    out = pd.DataFrame({
        Student.CODE: _s(df, "code"), Student.NAME: _s(df, "full_name"),
        Student.BIRTH: _s(df, "birth_date"),
        Student.AGE: [str(a) if a >= 0 else "" for a in age],
        Student.GENDER: _s(df, "gender"), Student.CATEGORY: _s(df, "category"),
        Student.PARENT_CODE: [_parent_field(pid, "code") for pid in df.get("parent_id", [])],
        Student.RELATION: _s(df, "relation"),
        Student.PARENT_NAME: [_parent_field(pid, "full_name") for pid in df.get("parent_id", [])],
        Student.PARENT_PHONE: [_parent_field(pid, "phone") for pid in df.get("parent_id", [])],
        Student.STUDY_TYPE: _s(df, "study_type"),
        Student.BRANCH: [_branch_name(bid) for bid in df.get("branch_id", [])],
        Student.LEVEL: _s(df, "level"), Student.SURAH: _s(df, "current_surah"),
        Student.STATUS: _s(df, "status"), Student.STOP_REASON: _s(df, "stop_reason"),
        Student.SUB_SYSTEM: _s(df, "sub_system"), Student.SUB_VALUE: _n(df, "sub_value"),
        Student.REG_DATE: _s(df, "reg_date"), Student.PREF_DAYS: _s(df, "preferred_days"),
        Student.NOTES: _s(df, "notes"),
    })
    out[Student.DISPLAY] = [make_display(c, n) for c, n in zip(out[Student.CODE], out[Student.NAME])]
    return out


def read_enrollments() -> pd.DataFrame:
    df = _fetch("enrollments")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["enrollments"])
    students = _fetch("students").set_index("id")
    teachers = _fetch("teachers").set_index("id")
    sched = _fetch("enrollment_schedule_days")
    order = {d: i for i, d in enumerate(ARABIC_WEEKDAYS)}

    def _sched_for(eid):
        rows = sched[sched["enrollment_id"] == eid] if not sched.empty else sched
        items = sorted(
            ((r["weekday"], r["session_time"], int(r["duration_minutes"])) for _, r in rows.iterrows()),
            key=lambda x: order.get(x[0], 99),
        )
        return items

    codes, s_codes, s_names, t_codes, t_names = [], [], [], [], []
    week_days, sess_time, sess_min, day_sched = [], [], [], []
    for _, r in df.iterrows():
        s_code = str(students.loc[int(r["student_id"]), "code"]) if r.get("student_id") in students.index else ""
        s_name = str(students.loc[int(r["student_id"]), "full_name"]) if r.get("student_id") in students.index else ""
        t_code = str(teachers.loc[int(r["teacher_id"]), "code"]) if r.get("teacher_id") in teachers.index else ""
        t_name = str(teachers.loc[int(r["teacher_id"]), "full_name"]) if r.get("teacher_id") in teachers.index else ""
        codes.append(r["code"]); s_codes.append(make_display(s_code, s_name)); s_names.append(s_name)
        t_codes.append(make_display(t_code, t_name)); t_names.append(t_name)
        items = _sched_for(r["id"])
        week_days.append("، ".join(d for d, _, _ in items))
        sess_time.append(items[0][1] if items else "")
        sess_min.append(str(items[0][2]) if items else "")
        day_sched.append(format_day_schedule(items))

    out = pd.DataFrame({
        Enrollment.CODE: codes, Enrollment.STUDENT_CODE: s_codes, Enrollment.STUDENT_NAME: s_names,
        Enrollment.TEACHER_CODE: t_codes, Enrollment.TEACHER_NAME: t_names,
        Enrollment.STUDY_TYPE: _s(df, "study_type"), Enrollment.START: _s(df, "start_date"),
        Enrollment.END: _s(df, "end_date"), Enrollment.SUB_VALUE: _n(df, "sub_value"),
        Enrollment.SESS_PRICE: _n(df, "session_price_ref"), Enrollment.STATUS: _s(df, "status"),
        Enrollment.NOTES: _s(df, "notes"), Enrollment.WEEK_DAYS: week_days,
        Enrollment.SESS_TIME: sess_time, Enrollment.SESS_MIN: sess_min,
        Enrollment.DAY_SCHEDULE: day_sched,
        Enrollment.STUDENT_RATE: _n(df, "student_hourly_rate"),
        Enrollment.TEACHER_RATE: _n(df, "teacher_hourly_rate"),
    })
    out[Enrollment.DISPLAY] = [f"{c} — {sn} / {tn}" for c, sn, tn in zip(codes, s_names, t_names)]
    return out


def read_sessions() -> pd.DataFrame:
    df = _fetch("sessions")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["sessions"])
    enroll = _fetch("enrollments").set_index("id")
    students = _fetch("students").set_index("id")
    teachers = _fetch("teachers").set_index("id")

    enroll_disp, s_codes, s_names, t_codes, t_names = [], [], [], [], []
    for _, r in df.iterrows():
        eid = r.get("enrollment_id")
        if eid in enroll.index:
            erow = enroll.loc[int(eid)]
            sid, tid = erow.get("student_id"), erow.get("teacher_id")
            s_code = str(students.loc[int(sid), "code"]) if sid in students.index else ""
            s_name = str(students.loc[int(sid), "full_name"]) if sid in students.index else ""
            t_code = str(teachers.loc[int(tid), "code"]) if tid in teachers.index else ""
            t_name = str(teachers.loc[int(tid), "full_name"]) if tid in teachers.index else ""
            enroll_disp.append(f"{erow['code']} — {s_name} / {t_name}")
        else:
            s_code = s_name = t_code = t_name = ""
            enroll_disp.append("")
        s_codes.append(s_code); s_names.append(s_name); t_codes.append(t_code); t_names.append(t_name)

    return pd.DataFrame({
        Session.CODE: _s(df, "code"), Session.ENROLL_CODE: enroll_disp,
        Session.STUDENT_CODE: s_codes, Session.STUDENT_NAME: s_names,
        Session.TEACHER_CODE: t_codes, Session.TEACHER_NAME: t_names,
        Session.DATE: _s(df, "session_date"), Session.MONTH: _s(df, "month"),
        Session.START_TIME: _s(df, "start_time"), Session.END_TIME: _s(df, "end_time"),
        Session.DURATION: _n(df, "duration_minutes"), Session.STATUS: _s(df, "status"),
        Session.CANCEL_RSN: _s(df, "cancel_reason"), Session.SURAH: _s(df, "surah"),
        Session.AYAH_FROM: _s(df, "ayah_from"), Session.AYAH_TO: _s(df, "ayah_to"),
        Session.AMOUNT: _s(df, "amount_memorized"), Session.RATING: _s(df, "rating"),
        Session.NOTES: _s(df, "notes"),
    })


def read_parent_feedback() -> pd.DataFrame:
    df = _fetch("parent_feedback")
    if df.empty:
        return pd.DataFrame(columns=schema.HEADERS["pfeedback"])
    students = _fetch("students").set_index("id")
    s_codes, s_names = [], []
    for sid in df.get("student_id", []):
        s_codes.append(str(students.loc[int(sid), "code"]) if sid in students.index else "")
        s_names.append(str(students.loc[int(sid), "full_name"]) if sid in students.index else "")
    return pd.DataFrame({
        ParentFeedback.CODE: _s(df, "code"), ParentFeedback.STUDENT_CODE: s_codes,
        ParentFeedback.STUDENT_NAME: s_names, ParentFeedback.MONTH: _s(df, "month"),
        ParentFeedback.SCORE: _n(df, "score"), ParentFeedback.SATISFACTION: _s(df, "satisfaction"),
        ParentFeedback.NOTES: _s(df, "notes"), ParentFeedback.DATE: _s(df, "feedback_date"),
        ParentFeedback.SOURCE: _s(df, "source"),
    })


def read_lookups() -> pd.DataFrame:
    df = _fetch("lookup_lists")
    if df.empty:
        return pd.DataFrame()
    cols = {}
    for list_key, col_name in schema.LOOKUP_COLS.items():
        vals = (df[df["list_key"] == list_key].sort_values("sort_order")["value_ar"].tolist()
                if "list_key" in df.columns else [])
        cols[col_name] = vals
    max_len = max((len(v) for v in cols.values()), default=0)
    for k in cols:
        cols[k] = cols[k] + [""] * (max_len - len(cols[k]))
    return pd.DataFrame(cols)


READERS = {
    "lookups": read_lookups, "teachers": read_teachers, "parents": read_parents,
    "students": read_students, "enrollments": read_enrollments, "sessions": read_sessions,
    "pfeedback": read_parent_feedback, "programs": read_programs, "branches": read_branches,
}


def read_ws(key: str) -> pd.DataFrame:
    reader = READERS.get(key)
    if reader is None:
        return pd.DataFrame()
    try:
        return reader()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"تعذّر قراءة '{key}' من Supabase: {e}")
        return pd.DataFrame()
