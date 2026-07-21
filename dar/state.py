# -*- coding: utf-8 -*-
"""وصول مركزي للبيانات والقوائم المرجعية + أدوات مساعدة مشتركة للواجهات."""
from __future__ import annotations
import pandas as pd
import streamlit as st

from . import sheets_io as io
from . import config
from .schema import Session, Student, Program, Branch


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


# ────────────────────────────────────────────────────────────────────────────
# ⚙️ إعدادات قابلة للتعديل من التطبيق (البرامج والفروع)
# ────────────────────────────────────────────────────────────────────────────
def get_programs() -> pd.DataFrame:
    """
    ورقة البرامج وأسعارها. لو فارغة (أول استخدام)، تُرجَع بذور افتراضية للعرض فقط
    (لا تُكتب في الشيت تلقائيًا — الإضافة الحقيقية تتم من شاشة الإعدادات).
    """
    df = get_data().get("programs")
    if df is not None and not df.empty:
        return df
    seed = [{Program.CODE: f"PR-{i+1:02d}", Program.NAME: name,
            Program.STUDENT_RATE: sr, Program.TEACHER_RATE: (tr if tr is not None else "")}
            for i, (name, (sr, tr)) in enumerate(config.SEED_PROGRAM_RATES.items())]
    return pd.DataFrame(seed)


def program_rate_map() -> dict:
    """{اسم البرنامج: (سعر الطالب|None, سعر المحفظ|None)} من ورقة البرامج."""
    df = get_programs()
    out = {}
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        name = str(r.get(Program.NAME, "")).strip()
        if not name:
            continue
        sr = pd.to_numeric(r.get(Program.STUDENT_RATE), errors="coerce")
        tr = pd.to_numeric(r.get(Program.TEACHER_RATE), errors="coerce")
        out[name] = (float(sr) if pd.notna(sr) and sr > 0 else None,
                     float(tr) if pd.notna(tr) and tr > 0 else None)
    return out


def get_branches() -> pd.DataFrame:
    """ورقة الفروع؛ بذور افتراضية للعرض إن كانت فارغة (أول استخدام)."""
    df = get_data().get("branches")
    if df is not None and not df.empty:
        return df
    seed = [{Branch.CODE: f"BR-{i+1:02d}", Branch.NAME: name}
            for i, name in enumerate(config.SEED_BRANCHES)]
    return pd.DataFrame(seed)


def branch_names() -> list[str]:
    df = get_branches()
    if df is None or df.empty or Branch.NAME not in df.columns:
        return list(config.SEED_BRANCHES)
    return [n for n in df[Branch.NAME].astype(str).tolist() if n.strip()]


def study_type_options() -> list[str]:
    """
    خيارات «نوع الدراسة» = برامج ورقة «البرامج» + القائمة المرجعية القديمة، مدمجة.
    هذا يضمن أن أي برنامج جديد يُضاف من شاشة الإعدادات يظهر فورًا كخيار في كل
    شاشات الإدخال، دون الحاجة لتحديث ورقة القوائم المرجعية يدويًا أيضًا.
    """
    programs = [n for n in program_rate_map().keys() if n]
    legacy = lk("study_type")
    return list(dict.fromkeys(programs + legacy))


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
