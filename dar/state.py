# -*- coding: utf-8 -*-
"""وصول مركزي للبيانات والقوائم المرجعية + أدوات مساعدة مشتركة للواجهات."""
from __future__ import annotations
import pandas as pd
import streamlit as st

from . import sheets_io as io
from .schema import Session, Student


def get_data(force: bool = False) -> dict:
    if force:
        io.clear_cache()
    return io.load_all()


def get_lookups() -> dict:
    data = get_data()
    return io.get_lookups(data.get("lookups"))


def lk(key: str, fallback=None) -> list:
    vals = get_lookups().get(key, [])
    return vals if vals else (fallback or [])


def num(v, default=0.0) -> float:
    n = pd.to_numeric(v, errors="coerce")
    return float(n) if pd.notna(n) else float(default)


def months_available(sessions_df: pd.DataFrame) -> list[str]:
    if sessions_df is None or sessions_df.empty or Session.MONTH not in sessions_df.columns:
        return []
    vals = [str(m).strip() for m in sessions_df[Session.MONTH].dropna().unique() if str(m).strip()]
    return sorted(set(vals), reverse=True)


def active_mask(df: pd.DataFrame, col=Student.STATUS):
    if df is None or df.empty or col not in df.columns:
        return pd.Series([False] * (0 if df is None else len(df)))
    return df[col].astype(str).str.contains("نشط", na=False)


def write_banner():
    """تنبيه أعلى صفحات الإدخال يوضّح وضع الكتابة."""
    tgt = io.write_target()
    if tgt == "google":
        st.success("✅ متصل بـ Google Sheets — الإدخال يُحفظ مباشرة في الملف.", icon="✅")
        return True
    if tgt == "script":
        st.success("✅ متصل بـ Google Sheets (عبر Apps Script) — الإدخال يُحفظ مباشرة.", icon="✅")
        return True
    if tgt == "local":
        st.info("💾 وضع الحفظ المحلي: يُحفظ الإدخال في ملف Excel المحلي (للتجربة). "
                "لتفعيل الحفظ في Google Sheets راجع SETUP.md.", icon="💾")
        return True
    st.warning(
        "⚠️ وضع القراءة فقط: لم يُضبط حساب خدمة Google ولا ملف محلي، فلا يمكن الحفظ. "
        "راجع SETUP.md لتفعيل الحفظ.", icon="⚠️")
    return False
