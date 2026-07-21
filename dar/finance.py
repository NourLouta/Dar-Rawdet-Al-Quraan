# -*- coding: utf-8 -*-
"""
محرّك المالية — الحساب بالساعة.

القواعد المعتمدة:
  • راتب المعلم الأساسي = ساعات الحصص المنفّذة × سعر ساعة المعلم.
  • صافي التحويل (فودافون كاش) = ceil_to_5( الأساسي × 1.01 ).
  • إيراد الطالب = ساعاته المنفّذة × سعر ساعة الطالب (65 افتراضيًا).
  • الربح = إجمالي إيراد الطلاب − إجمالي صافي تحويلات المعلمين.

الحصة "المنفّذة" = حالتها = "تمت". المدة بالدقائق ÷ 60 = ساعات.
"""
from __future__ import annotations
import math

import numpy as np
import pandas as pd

from . import config
from .config import (
    VODAFONE_CASH_FEE, ROUND_TO, STUDENT_HOURLY, TEACHER_HOURLY_DEFAULT,
)
from .schema import Teacher, Enrollment, Session, SESSION_DONE, code_of


# ────────────────────────────────────────────────────────────────────────────
# 🔢 التقريب
# ────────────────────────────────────────────────────────────────────────────
def ceil_to_5(x) -> int:
    """تقريب لأعلى لأقرب مضاعف لـ 5 (66→70، 101→105، 106→110)."""
    val = pd.to_numeric(x, errors="coerce")
    if val is None or pd.isna(val):
        return 0
    val = float(val)
    if val <= 0:
        return 0
    return int(math.ceil(val / ROUND_TO) * ROUND_TO)


def vodafone_payout(base_amount) -> int:
    """صافي التحويل المستحق عبر فودافون كاش = ceil_to_5(base × 1.01)."""
    amt = pd.to_numeric(base_amount, errors="coerce")
    if amt is None or pd.isna(amt) or float(amt) <= 0:
        return 0
    return ceil_to_5(float(amt) * VODAFONE_CASH_FEE)


def _num(v, default=0.0) -> float:
    n = pd.to_numeric(v, errors="coerce")
    if isinstance(n, (pd.Series, np.ndarray)):
        return n
    return float(n) if pd.notna(n) else float(default)


# ────────────────────────────────────────────────────────────────────────────
# ⏱️ الساعات المنفّذة
# ────────────────────────────────────────────────────────────────────────────
def completed_hours(sessions_df: pd.DataFrame) -> float:
    """مجموع ساعات الحصص المنفّذة (حالة = تمت) من جدول حصص."""
    if sessions_df is None or sessions_df.empty:
        return 0.0
    df = sessions_df
    if Session.STATUS in df.columns:
        df = df[df[Session.STATUS].astype(str).str.strip() == SESSION_DONE]
    if df.empty or Session.DURATION not in df.columns:
        return 0.0
    minutes = pd.to_numeric(df[Session.DURATION], errors="coerce").fillna(0).sum()
    return round(minutes / 60.0, 3)


def teacher_hourly_rate(teacher_code_or_name: str, teachers_df: pd.DataFrame) -> float:
    """سعر ساعة المعلم من ورقة المحفظين (بالكود أو الاسم)، أو الافتراضي."""
    if teachers_df is None or teachers_df.empty or not teacher_code_or_name:
        return float(TEACHER_HOURLY_DEFAULT)
    key = str(teacher_code_or_name).strip()
    for col in (Teacher.CODE, Teacher.NAME):
        if col in teachers_df.columns:
            hit = teachers_df[teachers_df[col].astype(str).str.strip() == key]
            if not hit.empty:
                rate = pd.to_numeric(hit.iloc[0].get(Teacher.HOURLY), errors="coerce")
                if pd.notna(rate) and rate > 0:
                    return float(rate)
    return float(TEACHER_HOURLY_DEFAULT)


# ────────────────────────────────────────────────────────────────────────────
# 💵 حلّ الأسعار لكل حصة (حسب البرنامج/التسجيل مع إمكانية التعديل)
# ────────────────────────────────────────────────────────────────────────────
def program_rates(program: str, program_map: dict | None = None):
    """
    (سعر ساعة الطالب، سعر ساعة المحفظ) للبرنامج — أو (None, None).
    program_map: {اسم البرنامج: (سعر الطالب, سعر المحفظ)} من ورقة «البرامج»
    (عبر state.program_rate_map())؛ إن لم يُمرَّر يُستخدم بذر افتراضي ثابت
    (للتوافق واختبارات الوحدة فقط — الواجهات يجب أن تمرّر الخريطة الحيّة دائمًا).
    """
    m = program_map if program_map is not None else config.SEED_PROGRAM_RATES
    return m.get(str(program or "").strip(), (None, None))


def _enroll_rate_map(enrollments) -> dict:
    """{كود التسجيل: (سعر الطالب|None, سعر المحفظ|None, البرنامج)}."""
    m = {}
    if enrollments is None or enrollments.empty or Enrollment.CODE not in enrollments.columns:
        return m
    for _, r in enrollments.iterrows():
        code = str(r.get(Enrollment.CODE, "")).strip()
        if not code:
            continue
        sr = pd.to_numeric(r.get(Enrollment.STUDENT_RATE), errors="coerce") \
            if Enrollment.STUDENT_RATE in enrollments.columns else float("nan")
        tr = pd.to_numeric(r.get(Enrollment.TEACHER_RATE), errors="coerce") \
            if Enrollment.TEACHER_RATE in enrollments.columns else float("nan")
        prog = str(r.get(Enrollment.STUDY_TYPE, "")).strip() if Enrollment.STUDY_TYPE in enrollments.columns else ""
        m[code] = (float(sr) if pd.notna(sr) and sr > 0 else None,
                   float(tr) if pd.notna(tr) and tr > 0 else None, prog)
    return m


def _resolve_rates(row, emap, teachers, program_map=None) -> tuple:
    """سعر ساعة الطالب والمحفظ لحصة: التسجيل ← البرنامج ← ملف المحفظين/الافتراضي."""
    ecode = code_of(row.get(Session.ENROLL_CODE, "")) if Session.ENROLL_CODE in row.index else ""
    sr = tr = None
    prog = ""
    if ecode and ecode in emap:
        sr, tr, prog = emap[ecode]
    ps, pt = program_rates(prog, program_map)
    if sr is None:
        sr = ps if ps is not None else STUDENT_HOURLY
    if tr is None:
        tr = pt if pt is not None else teacher_hourly_rate(
            row.get(Session.TEACHER_CODE) or row.get(Session.TEACHER_NAME), teachers)
    return float(sr), float(tr)


def _amounts(sessions_df, teachers, enrollments, month=None, program_map=None) -> pd.DataFrame:
    """يُرجع نسخة من الحصص بأعمدة: _done, _hours, _srate, _trate, _samt, _tamt."""
    df = sessions_df.copy() if sessions_df is not None else pd.DataFrame()
    if df.empty:
        return df
    if month and Session.MONTH in df.columns:
        df = df[df[Session.MONTH].astype(str).str.strip() == str(month).strip()].copy()
    if df.empty:
        return df
    emap = _enroll_rate_map(enrollments)
    dur = pd.to_numeric(df[Session.DURATION], errors="coerce").fillna(0) \
        if Session.DURATION in df.columns else pd.Series(0.0, index=df.index)
    done = df[Session.STATUS].astype(str).str.strip() == SESSION_DONE \
        if Session.STATUS in df.columns else pd.Series(True, index=df.index)
    df["_done"] = done.values
    df["_hours"] = (dur / 60.0).where(done, 0.0).values
    srates, trates = [], []
    for _, r in df.iterrows():
        s, t = _resolve_rates(r, emap, teachers, program_map)
        srates.append(s)
        trates.append(t)
    df["_srate"] = srates
    df["_trate"] = trates
    df["_samt"] = df["_hours"] * df["_srate"]
    df["_tamt"] = df["_hours"] * df["_trate"]
    return df


# ────────────────────────────────────────────────────────────────────────────
# 👩‍🏫 راتب المعلم
# ────────────────────────────────────────────────────────────────────────────
def teacher_salary(teacher_code: str, teacher_name: str, sessions_df: pd.DataFrame,
                   teachers_df: pd.DataFrame, month: str | None = None,
                   enrollments=None, program_map=None) -> dict:
    """احتساب راتب معلم واحد (بأسعار كل تسجيل)."""
    df = _amounts(sessions_df, teachers_df, enrollments, month=month, program_map=program_map)
    if not df.empty:
        if teacher_code and Session.TEACHER_CODE in df.columns:
            df = df[df[Session.TEACHER_CODE].astype(str).str.strip() == str(teacher_code).strip()]
        elif teacher_name and Session.TEACHER_NAME in df.columns:
            df = df[df[Session.TEACHER_NAME].astype(str).str.strip() == str(teacher_name).strip()]
    done = df[df["_done"]] if (not df.empty and "_done" in df.columns) else df
    cancelled = int((~df["_done"]).sum()) if (not df.empty and "_done" in df.columns) else 0
    hours = round(float(done["_hours"].sum()) if not done.empty else 0.0, 2)
    base = round(float(done["_tamt"].sum()) if not done.empty else 0.0, 2)
    rate = float(done["_trate"].mode().iloc[0]) if (not done.empty and not done["_trate"].mode().empty) \
        else teacher_hourly_rate(teacher_code or teacher_name, teachers_df)
    return {
        "teacher_code": teacher_code, "teacher_name": teacher_name,
        "sessions_done": int(len(done)) if not df.empty else 0,
        "sessions_cancelled": cancelled,
        "hours": hours, "rate": rate,
        "base_salary": base,
        "vodafone_fee": round(base * (VODAFONE_CASH_FEE - 1), 2),
        "net_payout": vodafone_payout(base),
    }


def all_teacher_salaries(sessions_df: pd.DataFrame, teachers_df: pd.DataFrame,
                         month: str | None = None, enrollments=None, program_map=None) -> pd.DataFrame:
    """كشف رواتب كل المعلمين (بأسعار كل تسجيل)."""
    df = _amounts(sessions_df, teachers_df, enrollments, month=month, program_map=program_map)
    if df.empty or (Session.TEACHER_CODE not in df.columns and Session.TEACHER_NAME not in df.columns):
        return pd.DataFrame()
    code = df[Session.TEACHER_CODE].astype(str).str.strip() if Session.TEACHER_CODE in df.columns else pd.Series("", index=df.index)
    name = df[Session.TEACHER_NAME].astype(str).str.strip() if Session.TEACHER_NAME in df.columns else pd.Series("", index=df.index)
    df["_key"] = code.where(code != "", name)
    rows = []
    for k, g in df.groupby("_key"):
        if not str(k).strip():
            continue
        done = g[g["_done"]]
        base = round(float(done["_tamt"].sum()), 2)
        rate = float(done["_trate"].mode().iloc[0]) if not done.empty and not done["_trate"].mode().empty else 0.0
        rows.append({
            "teacher_code": str(g[Session.TEACHER_CODE].iloc[0]).strip() if Session.TEACHER_CODE in g.columns else "",
            "teacher_name": str(g[Session.TEACHER_NAME].iloc[0]).strip() if Session.TEACHER_NAME in g.columns else "",
            "sessions_done": int(len(done)),
            "sessions_cancelled": int(len(g) - len(done)),
            "hours": round(float(done["_hours"].sum()), 2),
            "rate": rate, "base_salary": base,
            "vodafone_fee": round(base * (VODAFONE_CASH_FEE - 1), 2),
            "net_payout": vodafone_payout(base),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("net_payout", ascending=False).reset_index(drop=True)


# ────────────────────────────────────────────────────────────────────────────
# 👨‍🎓 إيراد الطالب
# ────────────────────────────────────────────────────────────────────────────
def student_revenue(student_code: str, sessions_df: pd.DataFrame,
                    rate: float = STUDENT_HOURLY, month: str | None = None,
                    enrollments=None, teachers=None, program_map=None) -> dict:
    """إيراد طالب واحد = Σ (ساعات × سعر ساعته لكل تسجيل)."""
    df = _amounts(sessions_df, teachers, enrollments, month=month, program_map=program_map)
    if not df.empty and student_code and Session.STUDENT_CODE in df.columns:
        df = df[df[Session.STUDENT_CODE].astype(str).str.strip() == str(student_code).strip()]
    done = df[df["_done"]] if (not df.empty and "_done" in df.columns) else df
    hours = round(float(done["_hours"].sum()) if not done.empty else 0.0, 2)
    fee = round(float(done["_samt"].sum()) if not done.empty else 0.0, 2)
    disp = float(done["_srate"].mode().iloc[0]) if (not done.empty and not done["_srate"].mode().empty) \
        else (float(rate) if rate else STUDENT_HOURLY)
    return {
        "student_code": student_code, "hours": hours, "rate": disp,
        "fee_due": fee, "fee_rounded": ceil_to_5(fee),
    }


# ────────────────────────────────────────────────────────────────────────────
# 🏦 ملخص المركز
# ────────────────────────────────────────────────────────────────────────────
def center_summary(sessions_df: pd.DataFrame, teachers_df: pd.DataFrame,
                   student_hourly: float = STUDENT_HOURLY,
                   month: str | None = None, enrollments=None, program_map=None) -> dict:
    """ملخص مالي للمركز: الإيراد − مرتبات المحفظين = الربح (بأسعار كل تسجيل)."""
    df = _amounts(sessions_df, teachers_df, enrollments, month=month, program_map=program_map)
    if df is None or df.empty:
        total_hours, revenue = 0.0, 0.0
    else:
        done = df[df["_done"]]
        total_hours = float(done["_hours"].sum())
        revenue = round(float(done["_samt"].sum()), 2)

    sal = all_teacher_salaries(sessions_df, teachers_df, month=month, enrollments=enrollments, program_map=program_map)
    total_base = float(sal["base_salary"].sum()) if not sal.empty else 0.0
    total_payout = float(sal["net_payout"].sum()) if not sal.empty else 0.0

    profit = round(revenue - total_payout, 2)
    margin = round(profit / revenue * 100, 1) if revenue else 0.0

    return {
        "month": month or "الكل",
        "total_hours": round(total_hours, 2),
        "revenue": revenue,
        "salaries_base": round(total_base, 2),
        "salaries_payout": round(total_payout, 2),
        "profit": profit,
        "margin_pct": margin,
        "teacher_count": int(len(sal)),
    }
