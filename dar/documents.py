# -*- coding: utf-8 -*-
"""
توليد المستندات — تقاويم وتقارير PDF عربية بهوية دار روضة القرآن.

يعتمد على reportlab + arabic_reshaper + python-bidi لعرض العربية بشكل صحيح
(تشكيل الحروف + الاتجاه من اليمين لليسار)، مع خطوط Tajawal/Amiri المضمّنة.

الدوال العامة تُرجع bytes جاهزة للتنزيل عبر Streamlit:
  • monthly_calendar_pdf(...)   تقويم شهري لطالب أو معلم
  • student_report_pdf(...)     تقرير شهري لطالب
  • teacher_report_pdf(...)     تقرير شهري لمعلم
"""
from __future__ import annotations
import calendar as _cal
import io
from datetime import date

import pandas as pd

from .config import T, FONTS_DIR, LOGO_PATH, CURRENCY
from .schema import (
    Session, Student, Teacher, ARABIC_WEEKDAYS, to_date, weekday_to_pywd,
)

# ── reportlab ────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Frame,
    PageBreak,
)
from reportlab.lib.styles import ParagraphStyle

import arabic_reshaper
from bidi.algorithm import get_display

# ════════════════════════════════════════════════════════════════════════════
# 🔤 الخطوط والعربية
# ════════════════════════════════════════════════════════════════════════════
# Amiri يحتوي على أشكال العرض العربية كاملة (Presentation Forms) المطلوبة
# لـ reportlab الذي لا يطبّق تشكيل OpenType — فيظهر النص العربي سليمًا.
FONT_REG = "Amiri"
FONT_BOLD = "Amiri-Bold"
_FONTS_READY = False


def _register_fonts():
    global _FONTS_READY
    if _FONTS_READY:
        return
    pdfmetrics.registerFont(TTFont(FONT_REG, str(FONTS_DIR / "Amiri-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONTS_DIR / "Amiri-Bold.ttf")))
    _FONTS_READY = True


def ar(text) -> str:
    """تشكيل النص العربي وضبط اتجاهه للعرض الصحيح في PDF."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text)
    if not s.strip():
        return ""
    try:
        return get_display(arabic_reshaper.reshape(s))
    except Exception:
        return s


def _rgb(t):
    return colors.Color(*t)


C_TEAL = _rgb(T.PDF_TEAL)
C_TEAL_D = _rgb(T.PDF_TEAL_D)
C_GOLD = _rgb(T.PDF_GOLD)
C_GOLD_L = _rgb(T.PDF_GOLD_L)
C_LIGHT = _rgb(T.PDF_LIGHT)
C_DARK = _rgb(T.PDF_DARK)
C_GREY = _rgb(T.PDF_GREY)
C_WHITE = colors.white


# ════════════════════════════════════════════════════════════════════════════
# 🎨 الأنماط والترويسة
# ════════════════════════════════════════════════════════════════════════════
def _styles():
    _register_fonts()
    return {
        "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=20,
                                textColor=C_WHITE, alignment=TA_CENTER, leading=26),
        "subtitle": ParagraphStyle("subtitle", fontName=FONT_REG, fontSize=11,
                                   textColor=C_GOLD_L, alignment=TA_CENTER, leading=16),
        "h2": ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=14,
                             textColor=C_TEAL_D, alignment=TA_RIGHT, leading=20,
                             spaceBefore=10, spaceAfter=6),
        "body": ParagraphStyle("body", fontName=FONT_REG, fontSize=10,
                               textColor=C_DARK, alignment=TA_RIGHT, leading=16),
        "cell": ParagraphStyle("cell", fontName=FONT_REG, fontSize=8.5,
                               textColor=C_DARK, alignment=TA_CENTER, leading=11),
        "cellhead": ParagraphStyle("cellhead", fontName=FONT_BOLD, fontSize=10,
                                   textColor=C_WHITE, alignment=TA_CENTER, leading=13),
        "daynum": ParagraphStyle("daynum", fontName=FONT_BOLD, fontSize=11,
                                 textColor=C_TEAL_D, alignment=TA_CENTER, leading=13),
        "sess": ParagraphStyle("sess", fontName=FONT_REG, fontSize=7.5,
                               textColor=C_DARK, alignment=TA_CENTER, leading=10),
        "kpi_val": ParagraphStyle("kpi_val", fontName=FONT_BOLD, fontSize=18,
                                  textColor=C_WHITE, alignment=TA_CENTER, leading=20),
        "kpi_lbl": ParagraphStyle("kpi_lbl", fontName=FONT_REG, fontSize=8.5,
                                  textColor=C_WHITE, alignment=TA_CENTER, leading=11),
        "footer": ParagraphStyle("footer", fontName=FONT_REG, fontSize=8,
                                 textColor=C_GREY, alignment=TA_CENTER, leading=11),
    }


MONTHS_AR = {
    1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
    7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}


def _month_label(month_key: str) -> str:
    try:
        y, m = month_key.split("-")
        return f"{MONTHS_AR.get(int(m), m)} {y}"
    except Exception:
        return month_key


def _header_footer(title_txt, subtitle_txt):
    """دالة رسم الترويسة والتذييل على كل صفحة."""
    S = _styles()

    def draw(canvas, doc):
        canvas.saveState()
        w, h = A4
        # شريط علوي تركواز
        canvas.setFillColor(C_TEAL_D)
        canvas.rect(0, h - 3.0 * cm, w, 3.0 * cm, fill=1, stroke=0)
        canvas.setFillColor(C_GOLD)
        canvas.rect(0, h - 3.1 * cm, w, 0.12 * cm, fill=1, stroke=0)
        # الشعار
        try:
            if LOGO_PATH.exists():
                canvas.drawImage(str(LOGO_PATH), w - 3.0 * cm, h - 2.75 * cm,
                                 width=2.2 * cm, height=2.2 * cm,
                                 preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
        # العنوان
        p = Paragraph(ar(title_txt), S["title"])
        p.wrapOn(canvas, w - 5 * cm, 2 * cm)
        p.drawOn(canvas, 1 * cm, h - 1.7 * cm)
        ps = Paragraph(ar(subtitle_txt), S["subtitle"])
        ps.wrapOn(canvas, w - 5 * cm, 1 * cm)
        ps.drawOn(canvas, 1 * cm, h - 2.5 * cm)
        # التذييل
        canvas.setFillColor(C_GREY)
        f = Paragraph(ar("دار روضة القرآن — نظام الإدارة المتكامل"), S["footer"])
        f.wrapOn(canvas, w - 2 * cm, 1 * cm)
        f.drawOn(canvas, 1 * cm, 0.8 * cm)
        canvas.setFont(FONT_REG, 8)
        canvas.drawRightString(w - 1 * cm, 0.8 * cm, f"{doc.page}")
        canvas.restoreState()

    return draw


def _doc(buf, title, subtitle):
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=3.4 * cm, bottomMargin=1.6 * cm,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        title=title,
    )
    return doc


# ════════════════════════════════════════════════════════════════════════════
# 🧱 مكوّنات
# ════════════════════════════════════════════════════════════════════════════
def _kpi_row(items):
    """صف بطاقات KPI ملوّنة. items = [(value, label, color)]"""
    S = _styles()
    cells, bg = [], []
    for val, lbl, col in items:
        inner = Table(
            [[Paragraph(ar(str(val)), S["kpi_val"])],
             [Paragraph(ar(lbl), S["kpi_lbl"])]],
            rowHeights=[0.85 * cm, 0.6 * cm],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), col),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))
        cells.append(inner)
    n = len(cells)
    t = Table([cells], colWidths=[(18.0 / n) * cm] * n)
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _info_table(rows):
    """جدول مفتاح-قيمة (RTL: المفتاح يمين، القيمة يسار)."""
    S = _styles()
    data = []
    for k, v in rows:
        data.append([Paragraph(ar(str(v)), S["body"]), Paragraph(ar(str(k)), S["h2"])])
    t = Table(data, colWidths=[11.5 * cm, 6.3 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, -1), C_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(*T.PDF_TEAL, alpha=0.25)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _data_table(headers, rows, col_widths=None):
    """جدول بيانات عام بترويسة تركواز (يُعكس ترتيب الأعمدة لتكون RTL)."""
    S = _styles()
    head = [Paragraph(ar(h), S["cellhead"]) for h in reversed(headers)]
    body = [head]
    for r in rows:
        body.append([Paragraph(ar(str(c)), S["cell"]) for c in reversed(r)])
    if col_widths:
        col_widths = list(reversed(col_widths))
    t = Table(body, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), C_TEAL),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(*T.PDF_TEAL, alpha=0.3)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
    ]
    t.setStyle(TableStyle(style))
    return t


# ════════════════════════════════════════════════════════════════════════════
# 📅 التقويم الشهري
# ════════════════════════════════════════════════════════════════════════════
def _sessions_by_day(sessions_df, month_key):
    """تجميع الحصص حسب اليوم (1..31) لشهر محدد."""
    out = {}
    if sessions_df is None or sessions_df.empty:
        return out
    df = sessions_df
    if Session.MONTH in df.columns:
        df = df[df[Session.MONTH].astype(str).str.strip() == str(month_key)]
    for _, r in df.iterrows():
        d = to_date(r.get(Session.DATE))
        if not d:
            continue
        out.setdefault(d.day, []).append(r)
    return out


def monthly_calendar_pdf(month_key: str, sessions_df: pd.DataFrame,
                         title: str, subtitle: str, show_field: str = "student") -> bytes:
    """
    تقويم شهري بشبكة أسابيع (السبت→الجمعة). كل خلية: رقم اليوم + الحصص.
    show_field: 'student' يعرض اسم الطالب، 'teacher' يعرض اسم المحفظ، 'surah' السورة.
    """
    S = _styles()
    buf = io.BytesIO()
    doc = _doc(buf, title, subtitle)
    story = []

    try:
        y, m = int(month_key.split("-")[0]), int(month_key.split("-")[1])
    except Exception:
        today = date.today()
        y, m = today.year, today.month

    by_day = _sessions_by_day(sessions_df, month_key)
    total = sum(len(v) for v in by_day.values())

    story.append(Spacer(1, 0.3 * cm))
    story.append(_kpi_row([
        (total, "إجمالي الحصص", C_TEAL),
        (len(by_day), "أيام بها حصص", C_GOLD_DARK := _rgb(T.PDF_GOLD)),
        (_month_label(month_key), "الشهر", C_TEAL_D),
    ]))
    story.append(Spacer(1, 0.5 * cm))

    # ترويسة أيام الأسبوع
    head = [Paragraph(ar(d), S["cellhead"]) for d in reversed(ARABIC_WEEKDAYS)]
    grid = [head]

    # بناء الأسابيع (يبدأ الأسبوع بالسبت)
    _cal.setfirstweekday(_cal.SATURDAY)
    weeks = _cal.monthcalendar(y, m)
    for week in weeks:
        row = []
        for day in week:  # day=0 يعني خارج الشهر
            if day == 0:
                row.append("")
                continue
            parts = [Paragraph(ar(str(day)), S["daynum"])]
            for sr in by_day.get(day, [])[:4]:
                tm = str(sr.get(Session.START_TIME, "") or "")
                if show_field == "teacher":
                    label = str(sr.get(Session.TEACHER_NAME, "") or "")
                elif show_field == "surah":
                    label = str(sr.get(Session.SURAH, "") or "")
                else:
                    label = str(sr.get(Session.STUDENT_NAME, "") or "")
                txt = " · ".join([p for p in (tm, label) if p])
                parts.append(Paragraph(ar(txt), S["sess"]))
            extra = len(by_day.get(day, [])) - 4
            if extra > 0:
                parts.append(Paragraph(ar(f"+{extra}"), S["sess"]))
            cellt = Table([[p] for p in parts], colWidths=[2.45 * cm])
            cellt.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ]))
            row.append(cellt)
        grid.append(list(reversed(row)))

    tbl = Table(grid, colWidths=[2.55 * cm] * 7,
                rowHeights=[0.7 * cm] + [2.5 * cm] * (len(grid) - 1))
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_TEAL),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.Color(*T.PDF_TEAL, alpha=0.35)),
        ("VALIGN", (0, 1), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, -1), C_WHITE),
    ]))
    story.append(tbl)

    doc.build(story, onFirstPage=_header_footer(title, subtitle),
              onLaterPages=_header_footer(title, subtitle))
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
# 📄 تقرير الطالب
# ════════════════════════════════════════════════════════════════════════════
def student_report_pdf(student: dict, stats: dict, sessions_rows: list[dict],
                       month_key: str) -> bytes:
    S = _styles()
    name = student.get(Student.NAME, "")
    title = f"تقرير الطالب — {name}"
    subtitle = f"شهر {_month_label(month_key)}"
    buf = io.BytesIO()
    doc = _doc(buf, title, subtitle)
    story = [Spacer(1, 0.3 * cm)]

    story.append(_kpi_row([
        (stats.get("done", 0), "حصص منفّذة", C_TEAL),
        (stats.get("cancelled", 0), "حصص ملغية", _rgb(T.PDF_GOLD)),
        (f"{stats.get('attendance', 0)}%", "نسبة الحضور", C_TEAL_D),
        (f"{stats.get('hours', 0)}", "ساعات", _rgb((0.06, 0.6, 0.5))),
    ]))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(ar("بيانات الطالب"), S["h2"]))
    story.append(_info_table([
        ("كود الطالب", student.get(Student.CODE, "")),
        ("المحفظ/ة", stats.get("teacher", "")),
        ("المستوى", student.get(Student.LEVEL, "")),
        ("السورة الحالية", student.get(Student.SURAH, "")),
        ("متوسط تقييم المحفظ", stats.get("avg_rating", "—")),
        ("رضا ولي الأمر (من 10)", stats.get("parent_score", "—")),
        ("الرسوم المستحقة", f"{stats.get('fee', 0)} {CURRENCY}"),
    ]))
    story.append(Spacer(1, 0.4 * cm))

    if sessions_rows:
        story.append(Paragraph(ar("سجل الحصص"), S["h2"]))
        headers = ["التاريخ", "الوقت", "الحالة", "السورة", "التقييم", "ملاحظات"]
        rows = [[r.get(Session.DATE, ""), r.get(Session.START_TIME, ""),
                 r.get(Session.STATUS, ""), r.get(Session.SURAH, ""),
                 r.get(Session.RATING, ""), r.get(Session.NOTES, "")]
                for r in sessions_rows]
        story.append(_data_table(headers, rows,
                                 col_widths=[2.6*cm, 2.0*cm, 2.4*cm, 3.0*cm, 2.4*cm, 5.4*cm]))

    doc.build(story, onFirstPage=_header_footer(title, subtitle),
              onLaterPages=_header_footer(title, subtitle))
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
# 📄 تقرير المعلم
# ════════════════════════════════════════════════════════════════════════════
def teacher_report_pdf(teacher: dict, salary: dict, students_rows: list[dict],
                       month_key: str) -> bytes:
    S = _styles()
    name = teacher.get(Teacher.NAME, "") or salary.get("teacher_name", "")
    title = f"تقرير المحفظ/ة — {name}"
    subtitle = f"شهر {_month_label(month_key)}"
    buf = io.BytesIO()
    doc = _doc(buf, title, subtitle)
    story = [Spacer(1, 0.3 * cm)]

    story.append(_kpi_row([
        (salary.get("sessions_done", 0), "حصص منفّذة", C_TEAL),
        (salary.get("hours", 0), "ساعات", C_TEAL_D),
        (f"{salary.get('base_salary', 0)}", "الراتب الأساسي", _rgb(T.PDF_GOLD)),
        (f"{salary.get('net_payout', 0)}", f"صافي التحويل {CURRENCY}", _rgb((0.06, 0.6, 0.5))),
    ]))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(ar("بيانات المحفظ/ة والراتب"), S["h2"]))
    story.append(_info_table([
        ("كود المحفظ", teacher.get(Teacher.CODE, "") or salary.get("teacher_code", "")),
        ("سعر الساعة", f"{salary.get('rate', 0)} {CURRENCY}"),
        ("عدد الطلاب", len(students_rows)),
        ("حصص ملغية", salary.get("sessions_cancelled", 0)),
        ("رسوم فودافون (1%)", f"{salary.get('vodafone_fee', 0)} {CURRENCY}"),
        ("صافي التحويل (مقرّب)", f"{salary.get('net_payout', 0)} {CURRENCY}"),
        ("متوسط تقييم أولياء الأمور", salary.get("parent_score", "—")),
    ]))
    story.append(Spacer(1, 0.4 * cm))

    if students_rows:
        story.append(Paragraph(ar("طلاب المحفظ/ة"), S["h2"]))
        headers = ["كود الطالب", "اسم الطالب", "حصص منفّذة", "ساعات", "السورة"]
        rows = [[r.get("code", ""), r.get("name", ""), r.get("done", ""),
                 r.get("hours", ""), r.get("surah", "")] for r in students_rows]
        story.append(_data_table(headers, rows,
                                 col_widths=[3.0*cm, 5.5*cm, 3.0*cm, 2.5*cm, 3.8*cm]))

    doc.build(story, onFirstPage=_header_footer(title, subtitle),
              onLaterPages=_header_footer(title, subtitle))
    return buf.getvalue()
