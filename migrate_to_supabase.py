# -*- coding: utf-8 -*-
"""
سكربت نسخ من Google Sheets إلى Supabase (Postgres) — Phase A2.

يقرأ عبر dar.sheets_io.read_ws() فقط (لا يلمس gspread أو الملف المحلي
مباشرة — نفس حاجز التجريد الذي تلتزم به كل شاشات التطبيق)، يطبّع الحقول
ويفكّك الأعمدة المُرمَّزة (جدول الأيام، الأسماء المكرَّرة) إلى المخطط
المنظّم الجديد (supabase/migrations/0001_dar_schema.sql)، ثم upsert بالكود
— idempotent، آمن لإعادة التشغيل في أي وقت.

Google Sheets يبقى المصدر الوحيد الموثوق خلال Phase A2/A3/A4 — هذا سكربت
نسخ أحادي الاتجاه (Sheets → Supabase) للتحقق فقط، لا يُستدعى من التطبيق.

الاستخدام:
    python migrate_to_supabase.py            # ينسخ كل الجداول
    python migrate_to_supabase.py --dry-run  # يطبع الصفوف بدل الكتابة
"""
from __future__ import annotations
import argparse
import sys

import pandas as pd
import streamlit as st

from dar import sheets_io as io
from dar.schema import (
    Teacher, Parent, Student, Enrollment, Session, Program, Branch, ParentFeedback,
    parse_day_schedule, to_date, clean_phone, code_of,
)

BATCH_SIZE = 500


def get_client():
    from supabase import create_client
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["service_role_key"])


def _upsert(sb, table: str, rows: list[dict], on_conflict: str, dry_run: bool) -> int:
    if not rows:
        return 0
    if dry_run:
        print(f"[dry-run] {table}: {len(rows)} rows (sample: {rows[0]})")
        return len(rows)
    n = 0
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i:i + BATCH_SIZE]
        sb.schema("dar").table(table).upsert(chunk, on_conflict=on_conflict).execute()
        n += len(chunk)
    return n


def _code_map(sb, table: str) -> dict:
    """يبني {code: id} من جدول Supabase بعد إدراجه، لاستخدامه كمفاتيح خارجية للجداول التالية."""
    res = sb.schema("dar").table(table).select("id,code").execute()
    return {r["code"]: r["id"] for r in res.data}


def migrate_lookups(sb, df: pd.DataFrame, dry_run: bool) -> int:
    from dar.schema import LOOKUP_COLS
    rows = []
    for list_key, col in LOOKUP_COLS.items():
        if col not in df.columns:
            continue
        for order, val in enumerate(df[col].dropna().astype(str)):
            val = val.strip()
            if val and val.lower() != "nan":
                rows.append({"list_key": list_key, "value_ar": val, "sort_order": order})
    return _upsert(sb, "lookup_lists", rows, "list_key,value_ar", dry_run)


def migrate_branches(sb, df: pd.DataFrame, dry_run: bool) -> int:
    rows = [{
        "code": r[Branch.CODE], "name": r.get(Branch.NAME, ""),
        "address": r.get(Branch.ADDRESS, ""), "notes": r.get(Branch.NOTES, ""),
    } for _, r in df.iterrows() if str(r.get(Branch.CODE, "")).strip()]
    return _upsert(sb, "branches", rows, "code", dry_run)


def migrate_programs(sb, df: pd.DataFrame, dry_run: bool) -> int:
    rows = [{
        "code": r[Program.CODE], "name": r.get(Program.NAME, ""),
        "student_hourly_rate": pd.to_numeric(r.get(Program.STUDENT_RATE), errors="coerce"),
        "teacher_hourly_rate": pd.to_numeric(r.get(Program.TEACHER_RATE), errors="coerce"),
        "notes": r.get(Program.NOTES, ""),
    } for _, r in df.iterrows() if str(r.get(Program.CODE, "")).strip()]
    return _upsert(sb, "programs", rows, "code", dry_run)


def migrate_teachers(sb, df: pd.DataFrame, dry_run: bool) -> int:
    rows = []
    for _, r in df.iterrows():
        code = str(r.get(Teacher.CODE, "")).strip()
        if not code:
            continue
        rows.append({
            "code": code, "full_name": r.get(Teacher.NAME, ""), "gender": r.get(Teacher.GENDER, ""),
            "phone": clean_phone(r.get(Teacher.PHONE)), "whatsapp": clean_phone(r.get(Teacher.WHATSAPP)),
            "governorate": r.get(Teacher.GOV, ""), "qualification": r.get(Teacher.QUALIFY, ""),
            "experience_years": pd.to_numeric(r.get(Teacher.EXPERIENCE), errors="coerce"),
            "teaches_category": r.get(Teacher.TEACHES, ""), "study_type": r.get(Teacher.STUDY_TYPE, ""),
            "work_system": r.get(Teacher.WORK_SYS, ""),
            "hourly_rate": pd.to_numeric(r.get(Teacher.HOURLY), errors="coerce"),
            "min_sessions": pd.to_numeric(r.get(Teacher.MIN_SESS), errors="coerce"),
            "contract_status": r.get(Teacher.CONTRACT, ""),
            "start_date": str(to_date(r.get(Teacher.START)) or "") or None,
            "preferred_timing": r.get(Teacher.TIMING, ""), "pay_method": r.get(Teacher.PAY_METHOD, ""),
            "special_in": r.get(Teacher.SPECIAL, ""), "notes": r.get(Teacher.NOTES, ""),
        })
    return _upsert(sb, "teachers", rows, "code", dry_run)


def migrate_parents(sb, df: pd.DataFrame, dry_run: bool) -> int:
    rows = []
    for _, r in df.iterrows():
        code = str(r.get(Parent.CODE, "")).strip()
        if not code:
            continue
        rows.append({
            "code": code, "full_name": r.get(Parent.NAME, ""), "phone": clean_phone(r.get(Parent.PHONE)),
            "whatsapp": clean_phone(r.get(Parent.WHATSAPP)), "address": r.get(Parent.ADDRESS, ""),
            "email": r.get(Parent.EMAIL, ""), "source": r.get(Parent.SOURCE, ""),
            "reg_date": str(to_date(r.get(Parent.REG_DATE)) or "") or None, "notes": r.get(Parent.NOTES, ""),
        })
    return _upsert(sb, "parents", rows, "code", dry_run)


def migrate_students(sb, df: pd.DataFrame, parent_ids: dict, branch_ids: dict, dry_run: bool) -> int:
    rows = []
    for _, r in df.iterrows():
        code = str(r.get(Student.CODE, "")).strip()
        if not code:
            continue
        rows.append({
            "code": code, "full_name": r.get(Student.NAME, ""),
            "birth_date": str(to_date(r.get(Student.BIRTH)) or "") or None,
            "gender": r.get(Student.GENDER, ""), "category": r.get(Student.CATEGORY, ""),
            "parent_id": parent_ids.get(str(r.get(Student.PARENT_CODE, "")).strip()),
            "relation": r.get(Student.RELATION, ""), "study_type": r.get(Student.STUDY_TYPE, ""),
            "branch_id": branch_ids.get(str(r.get(Student.BRANCH, "")).strip()),
            "level": r.get(Student.LEVEL, ""), "current_surah": r.get(Student.SURAH, ""),
            "status": r.get(Student.STATUS, ""), "stop_reason": r.get(Student.STOP_REASON, ""),
            "sub_system": r.get(Student.SUB_SYSTEM, ""),
            "sub_value": pd.to_numeric(r.get(Student.SUB_VALUE), errors="coerce"),
            "reg_date": str(to_date(r.get(Student.REG_DATE)) or "") or None,
            "preferred_days": r.get(Student.PREF_DAYS, ""), "notes": r.get(Student.NOTES, ""),
        })
    return _upsert(sb, "students", rows, "code", dry_run)


def migrate_enrollments(sb, df: pd.DataFrame, student_ids: dict, teacher_ids: dict,
                         program_ids: dict, dry_run: bool) -> tuple[int, int]:
    """يُرجع (عدد التسجيلات, عدد صفوف جدول الأيام) — كل يوم في DAY_SCHEDULE يصبح صفًا مستقلاً."""
    rows, schedule_rows = [], []
    for _, r in df.iterrows():
        code = str(r.get(Enrollment.CODE, "")).strip()
        s_code = code_of(r.get(Enrollment.STUDENT_CODE, "")) or str(r.get(Enrollment.STUDENT_CODE, "")).strip()
        t_code = code_of(r.get(Enrollment.TEACHER_CODE, "")) or str(r.get(Enrollment.TEACHER_CODE, "")).strip()
        if not code or s_code not in student_ids or t_code not in teacher_ids:
            continue
        rows.append({
            "code": code, "student_id": student_ids[s_code], "teacher_id": teacher_ids[t_code],
            "program_id": program_ids.get(str(r.get(Enrollment.STUDY_TYPE, "")).strip()),
            "study_type": r.get(Enrollment.STUDY_TYPE, ""),
            "start_date": str(to_date(r.get(Enrollment.START)) or "") or None,
            "end_date": str(to_date(r.get(Enrollment.END)) or "") or None,
            "sub_value": pd.to_numeric(r.get(Enrollment.SUB_VALUE), errors="coerce"),
            "session_price_ref": pd.to_numeric(r.get(Enrollment.SESS_PRICE), errors="coerce"),
            "student_hourly_rate": pd.to_numeric(r.get(Enrollment.STUDENT_RATE), errors="coerce"),
            "teacher_hourly_rate": pd.to_numeric(r.get(Enrollment.TEACHER_RATE), errors="coerce"),
            "status": r.get(Enrollment.STATUS, "نشط"), "notes": r.get(Enrollment.NOTES, ""),
        })
        for day, t, m in parse_day_schedule(r.get(Enrollment.DAY_SCHEDULE, "")):
            schedule_rows.append({
                "enrollment_code": code, "weekday": day, "session_time": t, "duration_minutes": m,
            })
    n = _upsert(sb, "enrollments", rows, "code", dry_run)
    if dry_run:
        print(f"[dry-run] enrollment_schedule_days: {len(schedule_rows)} rows")
        return n, len(schedule_rows)
    enrollment_ids = _code_map(sb, "enrollments")
    sched = [{
        "enrollment_id": enrollment_ids[s["enrollment_code"]], "weekday": s["weekday"],
        "session_time": s["session_time"], "duration_minutes": s["duration_minutes"],
    } for s in schedule_rows if s["enrollment_code"] in enrollment_ids]
    n_sched = _upsert(sb, "enrollment_schedule_days", sched, "enrollment_id,weekday", dry_run)
    return n, n_sched


def migrate_sessions(sb, df: pd.DataFrame, enrollment_ids: dict, dry_run: bool) -> int:
    rows = []
    for _, r in df.iterrows():
        code = str(r.get(Session.CODE, "")).strip()
        e_code = code_of(r.get(Session.ENROLL_CODE, "")) or str(r.get(Session.ENROLL_CODE, "")).strip()
        if not code or e_code not in enrollment_ids:
            continue
        d = to_date(r.get(Session.DATE))
        if not d:
            continue
        rows.append({
            "code": code, "enrollment_id": enrollment_ids[e_code], "session_date": str(d),
            "start_time": r.get(Session.START_TIME, ""), "end_time": r.get(Session.END_TIME, ""),
            "duration_minutes": pd.to_numeric(r.get(Session.DURATION), errors="coerce"),
            "status": r.get(Session.STATUS, "تمت"), "cancel_reason": r.get(Session.CANCEL_RSN, ""),
            "surah": r.get(Session.SURAH, ""), "ayah_from": r.get(Session.AYAH_FROM, ""),
            "ayah_to": r.get(Session.AYAH_TO, ""), "amount_memorized": r.get(Session.AMOUNT, ""),
            "rating": r.get(Session.RATING, ""), "notes": r.get(Session.NOTES, ""),
        })
    return _upsert(sb, "sessions", rows, "code", dry_run)


def migrate_parent_feedback(sb, df: pd.DataFrame, student_ids: dict, dry_run: bool) -> int:
    rows = []
    for _, r in df.iterrows():
        code = str(r.get(ParentFeedback.CODE, "")).strip()
        s_code = str(r.get(ParentFeedback.STUDENT_CODE, "")).strip()
        if not code or s_code not in student_ids:
            continue
        rows.append({
            "code": code, "student_id": student_ids[s_code], "month": r.get(ParentFeedback.MONTH, ""),
            "score": pd.to_numeric(r.get(ParentFeedback.SCORE), errors="coerce"),
            "satisfaction": r.get(ParentFeedback.SATISFACTION, ""), "notes": r.get(ParentFeedback.NOTES, ""),
            "feedback_date": str(to_date(r.get(ParentFeedback.DATE)) or "") or None,
            "source": r.get(ParentFeedback.SOURCE, ""),
        })
    return _upsert(sb, "parent_feedback", rows, "code", dry_run)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="اطبع الصفوف بدل الكتابة إلى Supabase")
    args = ap.parse_args()

    sb = None if args.dry_run else get_client()
    data = io.load_all()

    print("→ lookups");    migrate_lookups(sb, data["lookups"], args.dry_run)
    print("→ branches");   migrate_branches(sb, data["branches"], args.dry_run)
    print("→ programs");   migrate_programs(sb, data["programs"], args.dry_run)
    print("→ teachers");   migrate_teachers(sb, data["teachers"], args.dry_run)
    print("→ parents");    migrate_parents(sb, data["parents"], args.dry_run)

    branch_ids = {} if args.dry_run else _code_map(sb, "branches")
    parent_ids = {} if args.dry_run else _code_map(sb, "parents")
    print("→ students");   migrate_students(sb, data["students"], parent_ids, branch_ids, args.dry_run)

    student_ids = {} if args.dry_run else _code_map(sb, "students")
    teacher_ids = {} if args.dry_run else _code_map(sb, "teachers")
    program_ids = {} if args.dry_run else _code_map(sb, "programs")
    print("→ enrollments (+schedule days)")
    migrate_enrollments(sb, data["enrollments"], student_ids, teacher_ids, program_ids, args.dry_run)

    enrollment_ids = {} if args.dry_run else _code_map(sb, "enrollments")
    print("→ sessions");   migrate_sessions(sb, data["sessions"], enrollment_ids, args.dry_run)
    print("→ parent_feedback")
    migrate_parent_feedback(sb, data.get("pfeedback", pd.DataFrame()), student_ids, args.dry_run)

    print("done" + (" (dry-run — nothing written)" if args.dry_run else ""))


if __name__ == "__main__":
    sys.exit(main())
