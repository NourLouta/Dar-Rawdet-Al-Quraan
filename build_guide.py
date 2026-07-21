# -*- coding: utf-8 -*-
"""
مولّد دليل المستخدم (PDF) — دار روضة القرآن.
دليل عربي مبسّط جدًا خطوة بخطوة، بهوية الدار (تركواز + ذهبي)، مع إنفوجرافيك.
التشغيل:  python build_guide.py
الناتج:   data/دليل_استخدام_نظام_دار_روضة_القرآن.pdf
"""
from __future__ import annotations
import io
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, Flowable, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display

ROOT = Path(__file__).resolve().parent
FONTS = ROOT / "assets" / "fonts"
LOGO = ROOT / "Dar Logo.png"
OUT = ROOT / "docs" / "دليل_استخدام_نظام_دار_روضة_القرآن.pdf"

# ── الخطوط ───────────────────────────────────────────────────────────────────
pdfmetrics.registerFont(TTFont("Amiri", str(FONTS / "Amiri-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Amiri-Bold", str(FONTS / "Amiri-Bold.ttf")))
REG, BOLD = "Amiri", "Amiri-Bold"

# ── الألوان (هوية الدار) ─────────────────────────────────────────────────────
TEAL   = colors.Color(0.106, 0.420, 0.353)
TEAL_D = colors.Color(0.075, 0.306, 0.255)
TEAL_L = colors.Color(0.165, 0.549, 0.459)
GOLD   = colors.Color(0.788, 0.659, 0.298)
GOLD_L = colors.Color(0.886, 0.753, 0.416)
LIGHT  = colors.Color(0.941, 0.969, 0.961)
CARD   = colors.Color(0.968, 0.984, 0.976)
DARK   = colors.Color(0.10, 0.10, 0.10)
GREY   = colors.Color(0.42, 0.45, 0.50)
GREEN  = colors.Color(0.06, 0.60, 0.46)
AMBER  = colors.Color(0.85, 0.55, 0.10)
RED    = colors.Color(0.86, 0.20, 0.20)
BLUE   = colors.Color(0.20, 0.40, 0.75)
WHITE  = colors.white


import re as _re
# رموز تعبيرية/أسهم لا يدعمها خط Amiri — تُزال أو تُستبدل بفواصل مدعومة
_EMOJI_RE = _re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF\U00002B00-\U00002BFF️⁦-⁩‍]+")


def _clean(s: str) -> str:
    s = s.replace("←", "‹").replace("→", "›")
    s = _EMOJI_RE.sub("", s)
    s = _re.sub(r"«\s+", "«", s).replace("  ", " ").strip()
    return s


def ar(t) -> str:
    if t is None:
        return ""
    s = _clean(str(t))
    return get_display(arabic_reshaper.reshape(s)) if s.strip() else ""


# ── الأنماط ──────────────────────────────────────────────────────────────────
def P(txt, font=REG, size=11, color=DARK, align=TA_RIGHT, leading=None, space=2):
    style = ParagraphStyle("p", fontName=font, fontSize=size, textColor=color,
                           alignment=align, leading=leading or size * 1.55,
                           spaceBefore=space, spaceAfter=space, wordWrap="RTL")
    return Paragraph(ar(txt), style)


def _rich(txt, size=11):
    """فقرة تدعم <b> مع تشكيل عربي لكل جزء."""
    return Paragraph(ar(txt), ParagraphStyle(
        "r", fontName=REG, fontSize=size, textColor=DARK, alignment=TA_RIGHT,
        leading=size * 1.6, wordWrap="RTL"))


# ════════════════════════════════════════════════════════════════════════════
# 🧩 مكوّنات مرئية
# ════════════════════════════════════════════════════════════════════════════
def section_band(num, title, subtitle=""):
    """شريط عنوان قسم: رقم ذهبي دائري + عنوان على خلفية تركواز."""
    numcell = NumberCircle(num, r=0.52 * cm, fill=GOLD, txt=WHITE, fs=15)
    tt = [P(title, BOLD, 16, WHITE, TA_RIGHT, 20, 0)]
    if subtitle:
        tt.append(P(subtitle, REG, 10.5, GOLD_L, TA_RIGHT, 14, 0))
    inner = Table([[Table([[x] for x in tt]), numcell]], colWidths=[15.0 * cm, 1.4 * cm])
    inner.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_D),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
    ]))
    return inner


class NumberCircle(Flowable):
    def __init__(self, n, r=0.42 * cm, fill=GOLD, txt=WHITE, fs=13):
        super().__init__()
        self.n, self.r, self.fill, self.txt, self.fs = str(n), r, fill, txt, fs
        self.width = self.height = r * 2

    def draw(self):
        c = self.canv
        c.setFillColor(self.fill)
        c.circle(self.r, self.r, self.r, fill=1, stroke=0)
        c.setFillColor(self.txt)
        c.setFont(BOLD, self.fs)
        c.drawCentredString(self.r, self.r - self.fs * 0.35, self.n)


def step_card(num, title, body_lines):
    """بطاقة خطوة: رقم ذهبي + عنوان غامق + سطور شرح."""
    body = []
    if title:
        body.append(P(title, BOLD, 12, TEAL_D, TA_RIGHT, 16, 0))
    for ln in body_lines:
        body.append(P("•  " + ln, REG, 10.5, DARK, TA_RIGHT, 15, 1))
    txt_tbl = Table([[b] for b in body], colWidths=[14.2 * cm])
    txt_tbl.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 1),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    card = Table([[txt_tbl, NumberCircle(num, r=0.46 * cm)]],
                 colWidths=[14.6 * cm, 1.3 * cm])
    card.setStyle(TableStyle([
        ("VALIGN", (0, 0), (0, 0), "TOP"), ("VALIGN", (1, 0), (1, 0), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.Color(*[0.106, 0.420, 0.353], alpha=0.28)),
        ("LINEBEFORE", (1, 0), (1, 0), 0, WHITE),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [10, 10, 10, 10]),
    ]))
    return card


def callout(kind, text):
    """صندوق تنبيه: نصيحة (أخضر) / تحذير (كهرماني) / معلومة (تركواز) / خطأ شائع (أحمر)."""
    cfg = {
        "tip":  (GREEN, LIGHT, "نصيحة"),
        "warn": (AMBER, colors.Color(0.99, 0.96, 0.90), "تنبيه"),
        "info": (TEAL, LIGHT, "معلومة"),
        "err":  (RED, colors.Color(0.99, 0.93, 0.93), "خطأ شائع"),
    }[kind]
    bar, bg, label = cfg
    inner = [P(f"<b>{label}:</b> {text}", REG, 10.5, DARK, TA_RIGHT, 15, 0)]
    t = Table([[Table([[x] for x in inner], colWidths=[15.6 * cm])]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEAFTER", (0, 0), (0, 0), 3.2, bar),   # شريط يمين (RTL)
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


class FlowDiagram(Flowable):
    """إنفوجرافيك أفقي: خطوات مرقّمة بدوائر وأسهم بينها (من اليمين لليسار)."""
    def __init__(self, steps, width=16.4 * cm, height=3.0 * cm):
        super().__init__()
        self.steps = steps
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        n = len(self.steps)
        r = 0.62 * cm
        gap = self.width / n
        cy = self.height - r - 0.15 * cm
        centers = []
        for i in range(n):
            cx = self.width - gap * (i + 0.5)   # RTL: أول خطوة يمين
            centers.append(cx)
        # الأسهم
        c.setStrokeColor(GOLD)
        c.setLineWidth(2)
        for i in range(n - 1):
            x1 = centers[i] - r
            x2 = centers[i + 1] + r
            c.line(x1, cy, x2 + 0.18 * cm, cy)
            c.setFillColor(GOLD)
            p = c.beginPath()
            p.moveTo(x2, cy)
            p.lineTo(x2 + 0.24 * cm, cy + 0.13 * cm)
            p.lineTo(x2 + 0.24 * cm, cy - 0.13 * cm)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
        # الدوائر + النصوص
        for i, (cx, (num, label)) in enumerate(zip(centers, self.steps)):
            c.setFillColor(TEAL if i % 2 == 0 else TEAL_L)
            c.circle(cx, cy, r, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont(BOLD, 15)
            c.drawCentredString(cx, cy - 0.19 * cm, str(num))
            c.setFillColor(DARK)
            c.setFont(REG, 8.6)
            for j, part in enumerate(_wrap_label(label)):
                c.drawCentredString(cx, cy - r - 0.35 * cm - j * 0.33 * cm, ar(part))


def _wrap_label(label, maxlen=12):
    words = label.split(" ")
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= maxlen:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def pill(text, color=TEAL):
    t = Table([[P(text, BOLD, 9.5, WHITE, TA_CENTER, 12, 0)]])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("ROUNDEDCORNERS", [8, 8, 8, 8])]))
    return t


def price_table():
    rows = [["البرنامج", "يدفعه الطالب/ساعة", "يأخذه المحفظ/ساعة"],
            ["قرآن", "65 ج.م", "35 ج.م (بثينة 40)"],
            ["نور البيان", "70 ج.م", "50 ج.م"],
            ["القاعدة النورانية", "100 ج.م", "60 ج.م"]]
    data = [[P(c, BOLD if i == 0 else REG, 10.5, WHITE if i == 0 else DARK, TA_CENTER, 14, 0)
             for c in reversed(r)] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[5.4 * cm, 5.4 * cm, 5.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.106, 0.420, 0.353, alpha=0.3)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ════════════════════════════════════════════════════════════════════════════
# 🖼️ الصفحات (غلاف + ترويسة/تذييل)
# ════════════════════════════════════════════════════════════════════════════
def cover(c, doc):
    w, h = A4
    c.setFillColor(TEAL_D)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, h * 0.55, w, h * 0.45, fill=1, stroke=0)
    # زخرفة ذهبية
    c.setStrokeColor(GOLD)
    c.setLineWidth(3)
    c.line(w * 0.2, h * 0.54, w * 0.8, h * 0.54)
    if LOGO.exists():
        c.drawImage(str(LOGO), w / 2 - 2.6 * cm, h * 0.60, width=5.2 * cm, height=5.2 * cm,
                    preserveAspectRatio=True, mask="auto")
    c.setFillColor(GOLD_L)
    c.setFont(BOLD, 30)
    c.drawCentredString(w / 2, h * 0.46, ar("دليل استخدام النظام"))
    c.setFillColor(WHITE)
    c.setFont(BOLD, 20)
    c.drawCentredString(w / 2, h * 0.40, ar("دار روضة القرآن"))
    c.setFillColor(colors.Color(1, 1, 1, alpha=0.85))
    c.setFont(REG, 13)
    c.drawCentredString(w / 2, h * 0.34, ar("خطوة بخطوة — بأبسط طريقة ممكنة"))
    c.setFont(REG, 11)
    c.setFillColor(GOLD_L)
    c.drawCentredString(w / 2, h * 0.06, ar("نظام الإدارة المتكامل — إصدار 2026"))


def later(c, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(TEAL_D)
    c.rect(0, h - 1.15 * cm, w, 1.15 * cm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, h - 1.22 * cm, w, 0.07 * cm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD, 11)
    c.drawRightString(w - 1.2 * cm, h - 0.8 * cm, ar("دليل استخدام نظام دار روضة القرآن"))
    if LOGO.exists():
        c.drawImage(str(LOGO), 1.0 * cm, h - 1.08 * cm, width=1.0 * cm, height=1.0 * cm,
                    preserveAspectRatio=True, mask="auto")
    c.setFillColor(GREY)
    c.setFont(REG, 9)
    c.drawCentredString(w / 2, 0.7 * cm, ar("دار روضة القرآن"))
    c.setFillColor(TEAL)
    c.drawString(1.2 * cm, 0.7 * cm, str(doc.page))
    c.restoreState()


# ════════════════════════════════════════════════════════════════════════════
# 📚 المحتوى
# ════════════════════════════════════════════════════════════════════════════
def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(OUT), pagesize=A4,
                          topMargin=1.6 * cm, bottomMargin=1.3 * cm,
                          leftMargin=1.3 * cm, rightMargin=1.3 * cm,
                          title="دليل استخدام نظام دار روضة القرآن")
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=cover),
        PageTemplate(id="body", frames=[frame], onPage=later),
    ])

    S = []
    from reportlab.platypus import NextPageTemplate
    S.append(NextPageTemplate("body"))
    S.append(PageBreak())   # الغلاف صفحة مستقلة

    def sec(num, title, subtitle=""):
        S.append(section_band(num, title, subtitle))
        S.append(Spacer(1, 0.35 * cm))

    def sp(x=0.28):
        S.append(Spacer(1, x * cm))

    # ── 0) مقدمة ──────────────────────────────────────────────────────────────
    sec("١", "ما هذا النظام؟ وكيف أدخل؟", "ابدأ من هنا")
    S.append(_rich("هذا النظام يسجّل الطلاب والمحفظات والحصص، ويحسب المرتبات والإيرادات، "
                   "ويطبع تقارير وتقاويم جاهزة للإرسال. كل شيء يُحفظ مباشرة على ملف Google Sheets."))
    sp()
    S.append(step_card("١", "افتح الرابط", ["افتحي رابط النظام من المتصفح على الموبايل أو الكمبيوتر."]))
    sp(0.15)
    S.append(step_card("٢", "سجّلي الدخول", ["اسم المستخدم: admin", "كلمة المرور: dar2026"]))
    sp(0.15)
    S.append(step_card("٣", "القائمة الجانبية", ["كل الشاشات موجودة في القائمة على اليمين — اضغطي أي اسم للتنقّل."]))
    sp()
    S.append(callout("tip", "لو ظهرت أعلى الشاشة «✅ Google (حفظ مباشر)» فكل ما تدخلينه يُحفظ فورًا في الشيت."))

    # ── 2) خريطة الشاشات ──────────────────────────────────────────────────────
    sp(0.5)
    sec("٢", "خريطة الشاشات الثماني", "لمحة سريعة")
    screens = [
        ("لوحة المتابعة", "أرقام وإحصائيات سريعة"),
        ("الطلاب", "إضافة/تعديل/حذف الطلاب"),
        ("المحفظون", "بيانات المحفظات والأداء"),
        ("التسجيلات", "ربط الطالب بمحفظة + السعر + الجدول"),
        ("الحصص والإدخال", "توليد الحصص + التقييم + الإلغاء"),
        ("المالية", "المرتبات والإيرادات والأرباح"),
        ("التقييمات", "رضا الأهل وتقييم المحفظات"),
        ("التقارير والتقاويم", "طباعة تقويم/تقرير PDF"),
        ("الإعدادات", "إضافة برامج وفروع بنفسك"),
    ]
    for i in range(0, len(screens), 2):
        pair = screens[i:i + 2]
        cells = []
        for name, desc in pair:
            inner = Table([[P(name, BOLD, 11.5, TEAL_D, TA_RIGHT, 15, 0)],
                           [P(desc, REG, 9.5, GREY, TA_RIGHT, 13, 0)]])
            inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 8),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                       ("TOPPADDING", (0, 0), (-1, -1), 6),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                       ("BACKGROUND", (0, 0), (-1, -1), CARD),
                                       ("BOX", (0, 0), (-1, -1), 0.6, colors.Color(0.106, 0.420, 0.353, alpha=0.25)),
                                       ("LINEAFTER", (0, 0), (0, -1), 3, GOLD),
                                       ("ROUNDEDCORNERS", [8, 8, 8, 8])]))
            cells.append(inner)
        if len(cells) == 1:
            cells.append("")
        row = Table([list(reversed(cells))], colWidths=[8.1 * cm, 8.1 * cm])
        row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 4),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                 ("TOPPADDING", (0, 0), (-1, -1), 3),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                 ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        S.append(row)

    # ── 3) الترتيب الذهبي (الأهم) ──────────────────────────────────────────────
    sp(0.5)
    sec("٣", "الترتيب الذهبي — احفظيه جيدًا!", "لماذا لا يظهر الطالب أحيانًا؟")
    S.append(_rich("الطالب لا يظهر في «الحصص» إلا بعد أن تمرّي على هذه الخطوات بالترتيب. "
                   "هذا هو سبب أن البحث لا يُظهر الطالب أحيانًا:"))
    sp()
    S.append(FlowDiagram([("١", "أضف ولي الأمر والطالب"), ("٢", "أنشئ تسجيلًا"),
                          ("٣", "ولّد حصص الشهر"), ("٤", "سجّل التقييم"),
                          ("٥", "اطبع التقارير")]))
    sp(0.2)
    S.append(callout("err", "لو بحثتِ عن طالب في «الحصص» ولم يظهر: غالبًا لم تولّدي حصصه بعد. "
                            "ارجعي لخطوة «⚡ توليد حصص تسجيل»."))

    # ── 4) إضافة ولي أمر وطالب ──────────────────────────────────────────────────
    sp(0.5)
    sec("٤", "تسجيل طالب جديد", "شاشة: الطلاب ← ➕ إضافة طالب")
    S.append(step_card("١", "املئي بيانات الطالب", ["الاسم، تاريخ الميلاد (يحسب العمر تلقائيًا)، النوع، الفئة."]))
    sp(0.15)
    S.append(step_card("٢", "اختاري الفرع", ["مدينة نصر / الشيمي / أونلاين / درس منزلي."]))
    sp(0.15)
    S.append(step_card("٣", "ولي الأمر", ["اختاري وليّ أمر مسجّلًا، أو «➕ ولي أمر جديد» واكتبي اسمه وهاتفه."]))
    sp(0.15)
    S.append(step_card("٤", "احفظي", ["اضغطي «💾 حفظ الطالب» — سيظهر له كود مثل S-00045."]))
    sp()
    S.append(callout("info", "الكود يُنشأ تلقائيًا، ولا داعي لكتابته بنفسك."))

    # ── 5) التسجيل + الأسعار + الجدول ───────────────────────────────────────────
    sp(0.5)
    sec("٥", "إنشاء تسجيل: البرنامج + السعر + الجدول", "شاشة: التسجيلات ← ➕ تسجيل جديد")
    S.append(_rich("«التسجيل» يربط الطالب بمحفظة، ويحدّد البرنامج وسعره وأيام الحصص. "
                   "هذه أهم شاشة لأن منها تُولّد الحصص."))
    sp()
    S.append(step_card("١", "اختاري الطالب والمحفظة", ["من القائمتين المنسدلتين."]))
    sp(0.15)
    S.append(step_card("٢", "اختاري البرنامج (نوع الدراسة)", [
        "قرآن / نور البيان / القاعدة النورانية.",
        "بمجرد اختياره تظهر أسعاره تلقائيًا (الطالب والمحفظة)."]))
    sp(0.2)
    S.append(price_table())
    sp(0.2)
    S.append(step_card("٣", "تعديل السعر عند اللزوم", [
        "فعّلي «✏️ تعديل الأسعار يدويًا» لو السعر مختلف لهذا الطالب (مثل درس منزلي 150 ج.م)."]))
    sp(0.15)
    S.append(step_card("٤", "الجدول الأسبوعي", [
        "اختاري الأيام، ثم لكل يوم حدّدي وقته ومدته.",
        "يمكن أن يختلف الوقت أو المدة من يوم لآخر (مثال: السبت 8:00ص 60د، الاثنين 5:00م 30د)."]))
    sp(0.15)
    S.append(step_card("٥", "احفظي التسجيل", ["اضغطي «💾 حفظ التسجيل»."]))
    sp()
    S.append(callout("tip", "الحلقة المشتركة (مثل ليلى + منى معًا): سجّلي كل طالبة في تسجيل مستقل، "
                            "واكتبي في «تعديل الأسعار» ما تدفعه كل واحدة."))

    # ── 6) توليد الحصص ──────────────────────────────────────────────────────────
    sp(0.5)
    sec("٦", "توليد حصص الشهر", "شاشة: الحصص والإدخال ← ⚡ توليد حصص تسجيل")
    S.append(step_card("١", "اختاري التسجيل والشهر", ["ثم الحالة الافتراضية (تمت)."]))
    sp(0.15)
    S.append(step_card("٢", "بداية التوليد", [
        "«من أول الشهر» (الوضع المعتاد)، أو",
        "«من تاريخ محدّد» لو الطالب بدأ في منتصف الشهر (مثال يبدأ 24/7 — لن تُحسب أيام قبله)."]))
    sp(0.15)
    S.append(step_card("٣", "راجعي ثم ولّدي", ["ستظهر قائمة الحصص المتوقعة — اضغطي «⚡ توليد الحصص»."]))
    sp()
    S.append(callout("warn", "لو ظهرت حصص زائدة قبل تاريخ البدء: استخدمي «من تاريخ محدّد»، "
                            "أو احذفي الزائدة من «🗓️ إلغاء/تعديل حالات الحصص»."))
    S.append(callout("info", "زر «🔁 ترحيل شهري جماعي» يولّد حصص كل التسجيلات النشطة دفعة واحدة."))

    # ── 7) حصة مفردة (يوم إضافي) ─────────────────────────────────────────────────
    sp(0.5)
    sec("٧", "إضافة حصة مفردة (يوم إضافي/تعويض)", "شاشة: الحصص والإدخال ← ➕ إضافة حصة مفردة")
    S.append(_rich("لو أخذ الطالب يومًا إضافيًا خارج جدوله الثابت (مثل: كثّف أسبوعًا، أو عوّض حصة)، "
                   "لا تعيدي كل الجدول — أضيفي حصة واحدة فقط."))
    sp()
    S.append(step_card("١", "اختاري التسجيل", ["ثم التاريخ والوقت والمدة والحالة."]))
    sp(0.15)
    S.append(step_card("٢", "أضيفي", ["اضغطي «➕ إضافة الحصة» — تُضاف حصة واحدة بذلك التاريخ."]))
    sp()
    S.append(callout("tip", "حالة «محمد معتز» (٣ أيام ثابتة + يوم رابع في أول أسبوع): "
                            "ولّدي الجدول الثابت، ثم أضيفي اليوم الرابع كحصة مفردة."))

    # ── 8) الإلغاء وتعديل الحالة ─────────────────────────────────────────────────
    sp(0.5)
    sec("٨", "إلغاء أو تعديل حالة الحصص", "شاشة: الحصص والإدخال ← 🗓️ إلغاء/تعديل حالات الحصص")
    S.append(step_card("١", "اختاري الشهر (والطالب)", ["ستظهر جميع حصصه في جدول قابل للتعديل."]))
    sp(0.15)
    S.append(step_card("٢", "غيّري الحالة", ["اختاري «ملغية - طالب» أو غيرها لأي حصة، واكتبي سبب الإلغاء."]))
    sp(0.15)
    S.append(step_card("٣", "احفظي", ["اضغطي «💾 حفظ التغييرات»."]))
    sp()
    S.append(callout("info", "الحصة الملغية لا تُحسب في المرتبات ولا الإيرادات تلقائيًا."))

    # ── 9) تسجيل/تقييم الحصة ─────────────────────────────────────────────────────
    sp(0.5)
    sec("٩", "تسجيل وتقييم الحصة", "شاشة: الحصص والإدخال ← ✍️ تسجيل/تقييم حصة")
    S.append(step_card("١", "ابحثي عن الطالب", ["اكتبي اسم الطالب أو المحفظة في خانة البحث."]))
    sp(0.15)
    S.append(step_card("٢", "اختاري الحصة", ["ثم سجّلي التقييم: السورة، من آية – إلى آية، مقدار الحفظ، ملاحظات."]))
    sp(0.15)
    S.append(step_card("٣", "احفظي التقييم", []))
    sp()
    S.append(callout("err", "لا يظهر الطالب في البحث؟ تأكدي أنك ولّدتِ حصصه لهذا الشهر أولًا."))

    # ── 10) تعديل/حذف البيانات ───────────────────────────────────────────────────
    sp(0.5)
    sec("١٠", "تعديل أو حذف البيانات", "تبويب «✏️ تعديل / حذف» في الطلاب والتسجيلات")
    S.append(step_card("١", "افتحي تبويب «✏️ تعديل / حذف»", ["موجود في شاشة الطلاب وشاشة التسجيلات."]))
    sp(0.15)
    S.append(step_card("٢", "اختاري السجل وعدّلي", ["غيّري ما تريدين ثم «💾 حفظ التعديلات»."]))
    sp(0.15)
    S.append(step_card("٣", "الحذف", ["افتحي «🗑️ حذف» ثم «تأكيد الحذف»."]))
    sp()
    S.append(callout("warn", "لتغيير جدول طالب: عدّلي التسجيل، ثم أعيدي «توليد حصص الشهر» لتطبيق الجدول الجديد."))

    # ── 11) المالية ──────────────────────────────────────────────────────────────
    sp(0.5)
    sec("١١", "المالية والمرتبات", "شاشة: المالية")
    S.append(_rich("النظام يحسب تلقائيًا حسب أسعار كل تسجيل:"))
    sp(0.1)
    S.append(step_card("١", "راتب المحفظة", [
        "ساعات الحصص المنفّذة × سعر ساعتها، ثم رسوم فودافون 1٪ وتقريب لأقرب 5 ج.م."]))
    sp(0.15)
    S.append(step_card("٢", "إيراد الطالب", ["ساعاته × سعر ساعته (حسب البرنامج)."]))
    sp(0.15)
    S.append(step_card("٣", "الأرباح والفواتير", ["تظهر كشوف المرتبات وفواتير الطلاب — يمكن تحميلها CSV."]))
    sp()
    S.append(callout("warn", "لو ظهرت الأرقام «صفر»: تأكدي من تعبئة «مدة الحصة» وأن حالتها «تمت»."))

    # ── 12) التقارير والتقويم ─────────────────────────────────────────────────────
    sp(0.5)
    sec("١٢", "التقارير والتقويم", "شاشة: التقارير والتقاويم")
    S.append(step_card("١", "تقويم شهري", ["اختاري طالب/محفظة والشهر ← «📄 توليد التقويم (PDF)»."]))
    sp(0.15)
    S.append(step_card("٢", "حمّلي الملف", ["اضغطي «⬇️ تحميل التقويم» — ملف PDF جميل بهوية الدار."]))
    sp(0.15)
    S.append(step_card("٣", "أرسلي عبر واتساب", [
        "اضغطي «📲 إرسال عبر واتساب» (يفتح المحادثة برسالة جاهزة)، ثم أرفقي ملف الـPDF المحمّل."]))
    sp()
    S.append(callout("info", "يوجد أيضًا «تقرير طالب» و«تقرير محفظة» شهري بنفس الطريقة."))

    # ── 13) الإعدادات: أضيفي برنامجًا أو فرعًا بنفسك ──────────────────────────────
    sp(0.5)
    sec("١٣", "الإعدادات: أضيفي برنامجًا أو فرعًا بنفسك", "شاشة: الإعدادات")
    S.append(_rich("لو فتحت الدار فرعًا جديدًا، أو بدأت برنامجًا جديدًا بسعر مختلف — "
                   "لا داعي لطلب تعديل في النظام نفسه. أضيفيه بنفسك من هنا في دقيقة، "
                   "وسيظهر فورًا في كل شاشات الإدخال والمالية."))
    sp()
    S.append(step_card("١", "افتحي «⚙️ الإعدادات»", ["من القائمة الجانبية — آخر عنصر."]))
    sp(0.15)
    S.append(step_card("٢", "تبويب «البرامج والأسعار»", [
        "اضغطي «➕ إضافة»، اكتبي اسم البرنامج وسعر ساعة الطالب وسعر ساعة المحفظة، ثم احفظي.",
        "سيظهر البرنامج فورًا ضمن خيارات «نوع الدراسة» عند تسجيل أي طالب."]))
    sp(0.15)
    S.append(step_card("٣", "تبويب «الفروع»", ["بنفس الطريقة: أضيفي اسم الفرع وعنوانه."]))
    sp(0.15)
    S.append(step_card("٤", "تعديل سعر برنامج قائم", [
        "من «✏️ تعديل / حذف» غيّري السعر واحفظي — يُطبَّق تلقائيًا على كل تسجيل جديد."]))
    sp()
    S.append(callout("tip", "هذه الشاشة هي الحل لأي طلب مستقبلي شبيه: فرع جديد، برنامج جديد، "
                            "أو تغيير سعر — كله من هنا دون انتظار تعديل برمجي."))

    # ── 14) أسئلة شائعة ──────────────────────────────────────────────────────────
    sp(0.5)
    sec("١٤", "حل المشاكل الشائعة", "لو واجهتك أي عقبة")
    faqs = [
        ("الطالب لا يظهر في «الحصص»؟", "لم تُولّدي حصصه بعد — اذهبي إلى «⚡ توليد حصص تسجيل»."),
        ("الأرقام المالية صفر؟", "تأكدي من «مدة الحصة» وأن حالتها «تمت»."),
        ("حصص زائدة أول الشهر؟", "استخدمي «من تاريخ محدّد» عند التوليد، أو احذفي الزائدة."),
        ("عايزة أعدّل بيانات؟", "من تبويب «✏️ تعديل / حذف» في الطلاب أو التسجيلات."),
        ("سعر مختلف لطالب؟", "فعّلي «تعديل الأسعار يدويًا» داخل التسجيل."),
        ("حلقة مشتركة؟", "سجّلي كل طالبة على حدة بسعرها الخاص."),
        ("فرع أو برنامج جديد؟", "أضيفيه بنفسك من «⚙️ الإعدادات» — لا حاجة لتعديل برمجي."),
    ]
    for q, a in faqs:
        S.append(_rich(f"<b>س: {q}</b>", 11))
        S.append(P("ج: " + a, REG, 10.5, TEAL_D, TA_RIGHT, 15, 1))
        sp(0.12)
    sp()
    S.append(callout("tip", "احفظي هذا الدليل على موبايلك، وارجعي إليه وقت الحاجة. النظام سهل بعد أول مرّة 🌸"))

    doc.build(S)
    print("✅ تم إنشاء الدليل:", OUT, "-", OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    build()
