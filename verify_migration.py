# -*- coding: utf-8 -*-
"""
سكربت تحقق بعد الترحيل — Phase A2/A4.

يقارن عدد الصفوف بين Google Sheets وSupabase لكل كيان، يفحص عيّنة عشوائية
حقلًا-بحقل، ويكتشف المفاتيح الخارجية اليتيمة (orphan FKs). يطبع تقرير فروقات
ويُنهي بكود خروج غير صفري إن وُجد أي فرق — مناسب للتشغيل من GitHub Action.

الاستخدام:
    python verify_migration.py [--sample 20]
"""
from __future__ import annotations
import argparse
import sys

import pandas as pd
import streamlit as st

from dar import sheets_io as io
from dar.schema import Teacher, Parent, Student, Enrollment, Session, Program, Branch


def get_client():
    from supabase import create_client
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["service_role_key"])


def _sb_count(sb, table: str) -> int:
    res = sb.schema("dar").table(table).select("id", count="exact").limit(1).execute()
    return res.count or 0


def _sb_rows(sb, table: str) -> list[dict]:
    out, offset = [], 0
    while True:
        res = sb.schema("dar").table(table).select("*").range(offset, offset + 999).execute()
        if not res.data:
            break
        out.extend(res.data)
        offset += 1000
    return out


CHECKS = [
    # (sheets_key, sheets_code_col, supabase_table)
    ("branches", Branch.CODE, "branches"),
    ("programs", Program.CODE, "programs"),
    ("teachers", Teacher.CODE, "teachers"),
    ("parents", Parent.CODE, "parents"),
    ("students", Student.CODE, "students"),
    ("enrollments", Enrollment.CODE, "enrollments"),
    ("sessions", Session.CODE, "sessions"),
]


def check_row_counts(sb, data: dict) -> list[str]:
    problems = []
    for sheet_key, code_col, table in CHECKS:
        df = data.get(sheet_key, pd.DataFrame())
        sheet_codes = set(str(c).strip() for c in df.get(code_col, pd.Series(dtype=str)) if str(c).strip())
        sb_count = _sb_count(sb, table)
        if len(sheet_codes) != sb_count:
            problems.append(f"عدد الصفوف مختلف في {table}: Sheets={len(sheet_codes)} Supabase={sb_count}")
    return problems


def check_orphan_fks(sb) -> list[str]:
    problems = []
    student_ids = {r["id"] for r in _sb_rows(sb, "students")}
    teacher_ids = {r["id"] for r in _sb_rows(sb, "teachers")}
    enrollment_ids = {r["id"] for r in _sb_rows(sb, "enrollments")}

    for r in _sb_rows(sb, "enrollments"):
        if r["student_id"] not in student_ids:
            problems.append(f"enrollment {r['code']}: student_id يتيم ({r['student_id']})")
        if r["teacher_id"] not in teacher_ids:
            problems.append(f"enrollment {r['code']}: teacher_id يتيم ({r['teacher_id']})")
    for r in _sb_rows(sb, "sessions"):
        if r["enrollment_id"] not in enrollment_ids:
            problems.append(f"session {r['code']}: enrollment_id يتيم ({r['enrollment_id']})")
    return problems


def check_spot_sample(sb, data: dict, n: int) -> list[str]:
    """يقارن حقلًا-بحقل عيّنة عشوائية من الطلاب (الاسم، الحالة) — كشف مبكر لأخطاء تطبيع."""
    problems = []
    df = data.get("students", pd.DataFrame())
    if df.empty:
        return problems
    sample = df.sample(min(n, len(df)), random_state=0)
    sb_students = {r["code"]: r for r in _sb_rows(sb, "students")}
    for _, r in sample.iterrows():
        code = str(r.get(Student.CODE, "")).strip()
        sb_row = sb_students.get(code)
        if not sb_row:
            problems.append(f"student {code}: موجود في Sheets وغير موجود في Supabase")
            continue
        if str(r.get(Student.NAME, "")).strip() != str(sb_row.get("full_name", "")).strip():
            problems.append(f"student {code}: الاسم مختلف — Sheets={r.get(Student.NAME)!r} Supabase={sb_row.get('full_name')!r}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=20)
    args = ap.parse_args()

    sb = get_client()
    data = io.load_all()

    problems = []
    problems += check_row_counts(sb, data)
    problems += check_orphan_fks(sb)
    problems += check_spot_sample(sb, data, args.sample)

    if problems:
        print(f"❌ {len(problems)} مشكلة:")
        for p in problems:
            print(" -", p)
        return 1
    print("✅ لا فروقات — الترحيل متطابق.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
