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

from .config import (
    VODAFONE_CASH_FEE, ROUND_TO, STUDENT_HOURLY, TEACHER_HOURLY_DEFAULT,
)
from .schema import Teacher, Enrollment, Session, SESSION_DONE


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
# 👩‍🏫 راتب المعلم
# ────────────────────────────────────────────────────────────────────────────
def teacher_salary(teacher_code: str, teacher_name: str, sessions_df: pd.DataFrame,
                   teachers_df: pd.DataFrame, month: str | None = None) -> dict:
    """
    احتساب راتب معلم واحد لشهر (أو كل الشهور). يُرجع قاموسًا بالتفاصيل.
    """
    df = sessions_df.copy() if sessions_df is not None else pd.DataFrame()
    if not df.empty:
        if teacher_code and Session.TEACHER_CODE in df.columns:
            df = df[df[Session.TEACHER_CODE].astype(str).str.strip() == str(teacher_code).strip()]
        elif teacher_name and Session.TEACHER_NAME in df.columns:
            df = df[df[Session.TEACHER_NAME].astype(str).str.strip() == str(teacher_name).strip()]
        if month and Session.MONTH in df.columns:
            df = df[df[Session.MONTH].astype(str).str.strip() == str(month).strip()]

    done = df[df[Session.STATUS].astype(str).str.strip() == SESSION_DONE] \
        if (not df.empty and Session.STATUS in df.columns) else df
    cancelled = len(df) - len(done) if not df.empty else 0

    hours = completed_hours(df)
    rate = teacher_hourly_rate(teacher_code or teacher_name, teachers_df)
    base = round(hours * rate, 2)
    fee = round(base * (VODAFONE_CASH_FEE - 1), 2)
    payout = vodafone_payout(base)

    return {
        "teacher_code": teacher_code,
        "teacher_name": teacher_name,
        "sessions_done": int(len(done)),
        "sessions_cancelled": int(cancelled),
        "hours": round(hours, 2),
        "rate": rate,
        "base_salary": base,        # قبل الرسوم
        "vodafone_fee": fee,        # قيمة رسوم 1%
        "net_payout": payout,       # صافي التحويل (مقرّب لـ5)
    }


def all_teacher_salaries(sessions_df: pd.DataFrame, teachers_df: pd.DataFrame,
                         month: str | None = None) -> pd.DataFrame:
    """كشف رواتب كل المعلمين الموجودين في جدول الحصص."""
    if sessions_df is None or sessions_df.empty:
        return pd.DataFrame()
    if Session.TEACHER_CODE not in sessions_df.columns and Session.TEACHER_NAME not in sessions_df.columns:
        return pd.DataFrame()
    has_code = Session.TEACHER_CODE in sessions_df.columns
    has_name = Session.TEACHER_NAME in sessions_df.columns

    # دمج حسب المفتاح الفعّال (الكود إن وُجد، وإلا الاسم) لتجنّب الاحتساب المزدوج
    seen, rows = set(), []
    for _, r in sessions_df.iterrows():
        code = str(r.get(Session.TEACHER_CODE, "")).strip() if has_code else ""
        name = str(r.get(Session.TEACHER_NAME, "")).strip() if has_name else ""
        if not code and not name:
            continue
        key = code if code else name
        if key in seen:
            continue
        seen.add(key)
        rows.append(teacher_salary(code, name, sessions_df, teachers_df, month))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.sort_values("net_payout", ascending=False).reset_index(drop=True)


# ────────────────────────────────────────────────────────────────────────────
# 👨‍🎓 إيراد الطالب
# ────────────────────────────────────────────────────────────────────────────
def student_rate(enroll_row, enrollments_df=None) -> float:
    """سعر ساعة الطالب — افتراضي عام 65، مع إمكانية التجاوز عبر قيمة الاشتراك."""
    # يمكن لاحقًا قراءة تجاوز لكل طالب؛ الافتراضي العام:
    return float(STUDENT_HOURLY)


def student_revenue(student_code: str, sessions_df: pd.DataFrame,
                    rate: float = STUDENT_HOURLY, month: str | None = None) -> dict:
    """إيراد طالب واحد = ساعاته المنفّذة × سعر الساعة."""
    df = sessions_df.copy() if sessions_df is not None else pd.DataFrame()
    if not df.empty and student_code and Session.STUDENT_CODE in df.columns:
        df = df[df[Session.STUDENT_CODE].astype(str).str.strip() == str(student_code).strip()]
    if not df.empty and month and Session.MONTH in df.columns:
        df = df[df[Session.MONTH].astype(str).str.strip() == str(month).strip()]
    hours = completed_hours(df)
    fee = round(hours * float(rate), 2)
    return {
        "student_code": student_code,
        "hours": round(hours, 2),
        "rate": float(rate),
        "fee_due": fee,
        "fee_rounded": ceil_to_5(fee),
    }


# ────────────────────────────────────────────────────────────────────────────
# 🏦 ملخص المركز
# ────────────────────────────────────────────────────────────────────────────
def center_summary(sessions_df: pd.DataFrame, teachers_df: pd.DataFrame,
                   student_hourly: float = STUDENT_HOURLY,
                   month: str | None = None) -> dict:
    """
    ملخص مالي للمركز لشهر (أو الكل):
    الإيراد = Σ ساعات كل الطلاب × سعر الطالب.
    المرتبات = Σ صافي تحويلات المعلمين.
    الربح = الإيراد − المرتبات.
    """
    df = sessions_df.copy() if sessions_df is not None else pd.DataFrame()
    if not df.empty and month and Session.MONTH in df.columns:
        df = df[df[Session.MONTH].astype(str).str.strip() == str(month).strip()]

    total_hours = float(completed_hours(df))
    revenue = round(total_hours * float(student_hourly), 2)

    sal = all_teacher_salaries(df, teachers_df, month=None)  # df مفلتر بالشهر مسبقًا
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
