# -*- coding: utf-8 -*-
"""
محرّك عام لإدارة أي قائمة بسيطة (كود + حقول) بثلاث شاشات: قائمة / إضافة / تعديل-حذف.

الهدف: أي «ملاحظة مشابهة» مستقبلية من نوع «نحتاج نضيف/نعدّل نوع بيانات جديد»
(فرع، برنامج، مصدر تسويق، مستوى دراسي جديد...) تُحل بإضافة سطر واحد يستدعي
simple_crud() بدل كتابة شاشة كاملة من الصفر. هذا هو "الحل العام" المطلوب.
"""
from __future__ import annotations
from dataclasses import dataclass, field as _field
from typing import Any, Callable

import pandas as pd
import streamlit as st

from . import sheets_io as io
from . import state as state_mod
from . import ui


@dataclass
class Field:
    key: str                      # اسم العمود (ثابت من schema)
    label: str                    # التسمية المعروضة
    kind: str = "text"            # text | number | textarea | select
    options: list | Callable[[], list] | None = None
    default: Any = ""
    required: bool = False
    min_value: float | None = None
    step: float = 1.0
    help: str | None = None


def _widget(f: Field, value, key: str):
    opts = f.options() if callable(f.options) else f.options
    if f.kind == "number":
        v = pd.to_numeric(value, errors="coerce")
        v = float(v) if pd.notna(v) else float(f.default or 0)
        return st.number_input(f.label, value=v, min_value=f.min_value, step=f.step, key=key, help=f.help)
    if f.kind == "select":
        opts = opts or []
        idx = opts.index(value) if value in opts else 0
        return st.selectbox(f.label, opts, index=idx, key=key, help=f.help)
    if f.kind == "textarea":
        return st.text_area(f.label, value=str(value or ""), key=key, help=f.help)
    return st.text_input(f.label, value=str(value or ""), key=key, help=f.help)


def simple_crud(*, sheet_key: str, code_field: str, name_field: str | None,
                fields: list[Field], code_prefix_key: str, empty_msg: str = "لا توجد سجلات بعد.",
                list_cols: list[str] | None = None,
                seed_rows: Callable[[], list[dict]] | None = None,
                seed_label: str = "🌱 إضافة القيم الافتراضية دفعة واحدة"):
    """
    يعرض 3 تبويبات (قائمة / إضافة / تعديل-حذف) لورقة بسيطة ذات كود فريد.

    seed_rows: دالة تُرجع صفوفًا افتراضية (بلا عمود الكود) لتعبئة الورقة أول مرة
    بضغطة واحدة بدل إدخالها يدويًا واحدًا تلو الآخر.
    """
    data = state_mod.get_data()
    df = data.get(sheet_key, pd.DataFrame())
    t_list, t_add, t_edit = st.tabs(["📋 القائمة", "➕ إضافة", "✏️ تعديل / حذف"])

    with t_list:
        if df.empty:
            st.info(empty_msg)
            if seed_rows and state_mod.write_banner():
                if st.button(seed_label, key=f"crud_seed_{sheet_key}"):
                    rows = seed_rows()
                    prefix, width = _prefixed(code_prefix_key)
                    out = []
                    n = _max_existing(df, code_field, prefix)
                    for r in rows:
                        n += 1
                        out.append({code_field: f"{prefix}{n:0{width}d}", **r})
                    try:
                        io.append_rows(sheet_key, out)
                        state_mod.get_data(force=True)
                        st.success(f"✅ أُضيفت {len(out)} قيمة افتراضية — يمكنك الآن تعديلها من تبويب «تعديل / حذف».")
                        st.rerun()
                    except Exception as e:
                        st.error(f"تعذّر الإضافة: {e}")
        else:
            cols = list_cols or ([code_field] + ([name_field] if name_field else []) + [f.key for f in fields])
            cols = [c for c in dict.fromkeys(cols) if c in df.columns]
            ui.display_table(df[cols], download_name=f"{sheet_key}.csv")

    with t_add:
        can = state_mod.write_banner()
        next_code = io.next_code(code_prefix_key, df, code_field)
        st.markdown(f"**الكود الجديد:** `{next_code}`")
        values = {f.key: _widget(f, f.default, key=f"crud_add_{sheet_key}_{f.key}") for f in fields}
        if st.button("💾 حفظ", key=f"crud_add_btn_{sheet_key}"):
            missing = [f.label for f in fields if f.required and not str(values.get(f.key, "")).strip()]
            if missing:
                st.error("الحقول التالية مطلوبة: " + "، ".join(missing))
            else:
                row = {code_field: next_code, **values}
                if not can:
                    st.json({k: str(v) for k, v in row.items()})
                else:
                    try:
                        io.append_row(sheet_key, row)
                        state_mod.get_data(force=True)
                        st.success(f"✅ تم الحفظ بالكود {next_code}.")
                    except Exception as e:
                        st.error(f"تعذّر الحفظ: {e}")

    with t_edit:
        can = state_mod.write_banner()
        if df.empty:
            st.info(empty_msg)
        else:
            labels = df[code_field].astype(str)
            if name_field and name_field in df.columns:
                labels = labels + " — " + df[name_field].astype(str)
            label_list = labels.tolist()
            sel = st.selectbox("اختر السجل", label_list, key=f"crud_sel_{sheet_key}")
            row = df.iloc[label_list.index(sel)].to_dict()
            code_val = row.get(code_field)
            updates = {f.key: _widget(f, row.get(f.key, f.default), key=f"crud_edit_{sheet_key}_{f.key}")
                      for f in fields}
            b1, b2 = st.columns(2)
            if b1.button("💾 حفظ التعديلات", disabled=not can, key=f"crud_save_{sheet_key}"):
                missing = [f.label for f in fields if f.required and not str(updates.get(f.key, "")).strip()]
                if missing:
                    st.error("الحقول التالية مطلوبة: " + "، ".join(missing))
                else:
                    try:
                        io.update_row_by_code(sheet_key, code_field, code_val, updates)
                        state_mod.get_data(force=True)
                        st.success("✅ تم حفظ التعديلات.")
                    except Exception as e:
                        st.error(f"تعذّر التعديل: {e}")
            with b2.expander("🗑️ حذف هذا السجل"):
                st.warning("سيُحذف السجل نهائيًا.")
                if st.button("تأكيد الحذف", disabled=not can, key=f"crud_del_{sheet_key}"):
                    try:
                        io.delete_row_by_code(sheet_key, code_field, code_val)
                        state_mod.get_data(force=True)
                        st.success("🗑️ تم الحذف.")
                    except Exception as e:
                        st.error(f"تعذّر الحذف: {e}")


def _prefixed(code_prefix_key: str):
    from . import config
    return config.CODE_PREFIX[code_prefix_key]


def _max_existing(df, code_field, prefix) -> int:
    n = 0
    if df is None or df.empty or code_field not in df.columns:
        return n
    for v in df[code_field].astype(str):
        v = v.strip()
        if v.startswith(prefix) and v[len(prefix):].isdigit():
            n = max(n, int(v[len(prefix):]))
    return n
