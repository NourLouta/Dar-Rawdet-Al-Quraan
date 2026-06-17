# -*- coding: utf-8 -*-
"""
مخطط البيانات (أسماء الأعمدة) + دوال التطبيع والتحقق.

كل أسماء الأعمدة العربية تُعرَّف هنا مرة واحدة كي لا تتكرر في باقي الوحدات،
ويسهل تعديلها لو تغيّر الملف. كما يحتوي على دوال تنظيف الإدخال:
الأرقام العربية، الهواتف، التواريخ، الأوقات.
"""
from __future__ import annotations
import re
from datetime import datetime, date

import pandas as pd

# ════════════════════════════════════════════════════════════════════════════
# 🏷️  أعمدة كل ورقة (مطابقة للملف الجديد)
# ════════════════════════════════════════════════════════════════════════════

class Teacher:
    CODE       = "كود المحفظ"
    NAME       = "الاسم الكامل"
    GENDER     = "النوع"
    PHONE      = "رقم الهاتف"
    WHATSAPP   = "واتساب"
    GOV        = "المحافظة"
    QUALIFY    = "المؤهل/الإجازة"
    EXPERIENCE = "سنوات الخبرة"
    TEACHES    = "الفئة التي يدرّسها"
    STUDY_TYPE = "نوع الدراسة"
    WORK_SYS   = "نظام العمل"
    HOURLY     = "سعر الساعة"
    MIN_SESS   = "الحد الأدنى للحصص"
    CONTRACT   = "حالة التعاقد"
    START      = "تاريخ البداية"
    TIMING     = "التوقيت المفضل"
    PAY_METHOD = "طريقة الدفع"
    SPECIAL    = "مميز في"
    NOTES      = "ملاحظات"
    DISPLAY    = "عرض (كود — اسم)"


class Parent:
    CODE     = "كود ولي الأمر"
    NAME     = "الاسم الكامل"
    PHONE    = "رقم الهاتف"
    WHATSAPP = "واتساب"
    ADDRESS  = "العنوان"
    EMAIL    = "البريد الإلكتروني"
    SOURCE   = "مصدر الاشتراك"
    REG_DATE = "تاريخ التسجيل"
    N_KIDS   = "عدد الأبناء المسجلين"
    NOTES    = "ملاحظات"
    DISPLAY  = "عرض (كود — اسم)"


class Student:
    CODE        = "كود الطالب"
    NAME        = "الاسم الكامل"
    BIRTH       = "تاريخ الميلاد"
    AGE         = "العمر"
    GENDER      = "النوع"
    CATEGORY    = "الفئة"
    PARENT_CODE = "كود ولي الأمر"
    RELATION    = "صلة القرابة"
    PARENT_NAME = "اسم ولي الأمر"
    PARENT_PHONE= "رقم هاتف ولي الأمر"
    STUDY_TYPE  = "نوع الدراسة"
    LEVEL       = "المستوى"
    SURAH       = "السورة الحالية"
    STATUS      = "حالة الاشتراك"
    STOP_REASON = "سبب الإيقاف"
    SUB_SYSTEM  = "نظام الاشتراك"
    SUB_VALUE   = "قيمة الاشتراك"
    REG_DATE    = "تاريخ التسجيل"
    PREF_DAYS   = "أيام الحضور المفضلة"
    NOTES       = "ملاحظات"
    DISPLAY     = "عرض (كود — اسم)"


class Enrollment:
    CODE        = "كود التسجيل"
    STUDENT_CODE= "كود الطالب"
    STUDENT_NAME= "اسم الطالب"
    TEACHER_CODE= "كود المحفظ"
    TEACHER_NAME= "اسم المحفظ"
    STUDY_TYPE  = "نوع الدراسة"
    START       = "تاريخ البداية"
    END         = "تاريخ الانتهاء"
    SUB_VALUE   = "قيمة الاشتراك"
    SESS_PRICE  = "سعر الحصة للمعلم"   # يبقى مرجعيًا؛ الحساب بالساعة
    STATUS      = "حالة التسجيل"
    NOTES       = "ملاحظات"
    DISPLAY     = "عرض (كود — طالب / محفظ)"
    # أعمدة النمط الأسبوعي المُضافة (لتوليد الحصص تلقائيًا)
    WEEK_DAYS   = "أيام الأسبوع"
    SESS_TIME   = "وقت الحصة"
    SESS_MIN    = "مدة الحصة (دقيقة)"
    DAY_SCHEDULE = "جدول الأيام"   # وقت/مدة مختلفة لكل يوم (اختياري)


class Session:
    CODE        = "كود الحصة"
    ENROLL_CODE = "كود التسجيل"
    STUDENT_CODE= "كود الطالب"
    STUDENT_NAME= "اسم الطالب"
    TEACHER_CODE= "كود المحفظ"
    TEACHER_NAME= "اسم المحفظ"
    DATE        = "التاريخ"
    MONTH       = "الشهر"
    START_TIME  = "وقت البداية"
    END_TIME    = "وقت النهاية"
    DURATION    = "مدة الحصة (دقيقة)"
    STATUS      = "حالة الحصة"
    CANCEL_RSN  = "سبب الإلغاء"
    SURAH       = "السورة"
    AYAH_FROM   = "من آية"
    AYAH_TO     = "إلى آية"
    AMOUNT      = "مقدار الحفظ"
    RATING      = "تقييم الأداء"
    NOTES       = "ملاحظات المحفظ"


class ParentFeedback:
    CODE         = "كود التقييم"
    STUDENT_CODE = "كود الطالب"
    STUDENT_NAME = "اسم الطالب"
    MONTH        = "الشهر"
    SCORE        = "التقييم (1-10)"
    SATISFACTION = "الرضا"
    NOTES        = "ملاحظات ولي الأمر"
    DATE         = "التاريخ"
    SOURCE       = "المصدر"


# ترتيب أعمدة كل ورقة عند الإنشاء/الكتابة
HEADERS = {
    "teachers": [getattr(Teacher, a) for a in
        ("CODE","NAME","GENDER","PHONE","WHATSAPP","GOV","QUALIFY","EXPERIENCE",
         "TEACHES","STUDY_TYPE","WORK_SYS","HOURLY","MIN_SESS","CONTRACT","START",
         "TIMING","PAY_METHOD","SPECIAL","NOTES","DISPLAY")],
    "parents": [getattr(Parent, a) for a in
        ("CODE","NAME","PHONE","WHATSAPP","ADDRESS","EMAIL","SOURCE","REG_DATE",
         "N_KIDS","NOTES","DISPLAY")],
    "students": [getattr(Student, a) for a in
        ("CODE","NAME","BIRTH","AGE","GENDER","CATEGORY","PARENT_CODE","RELATION",
         "PARENT_NAME","PARENT_PHONE","STUDY_TYPE","LEVEL","SURAH","STATUS",
         "STOP_REASON","SUB_SYSTEM","SUB_VALUE","REG_DATE","PREF_DAYS","NOTES","DISPLAY")],
    "enrollments": [getattr(Enrollment, a) for a in
        ("CODE","STUDENT_CODE","STUDENT_NAME","TEACHER_CODE","TEACHER_NAME",
         "STUDY_TYPE","START","END","SUB_VALUE","SESS_PRICE","STATUS","NOTES",
         "WEEK_DAYS","SESS_TIME","SESS_MIN","DAY_SCHEDULE","DISPLAY")],
    "sessions": [getattr(Session, a) for a in
        ("CODE","ENROLL_CODE","STUDENT_CODE","STUDENT_NAME","TEACHER_CODE",
         "TEACHER_NAME","DATE","MONTH","START_TIME","END_TIME","DURATION","STATUS",
         "CANCEL_RSN","SURAH","AYAH_FROM","AYAH_TO","AMOUNT","RATING","NOTES")],
    "pfeedback": [getattr(ParentFeedback, a) for a in
        ("CODE","STUDENT_CODE","STUDENT_NAME","MONTH","SCORE","SATISFACTION",
         "NOTES","DATE","SOURCE")],
}

# مفتاح الورقة في القوائم المرجعية المرتبط بكل عمود قائمة
LOOKUP_COLS = {
    "time_slots":   "الفترات الزمنية",
    "levels":       "المستويات",
    "juz":          "أجزاء القرآن",
    "surahs":       "السور",
    "amount":       "مقدار الحفظ",
    "sub_status":   "حالة الاشتراك",
    "study_type":   "نوع الدراسة",
    "age_cat":      "الفئة العمرية",
    "gender":       "النوع",
    "source":       "مصدر الاشتراك",
    "relation":     "صلة القرابة",
    "contract":     "حالة التعاقد",
    "pay_method":   "طريقة الدفع",
    "sess_status":  "حالة الحصة",
    "pay_status":   "حالة الدفع",
    "week_days":    "أيام الأسبوع",
    "contact_type": "نوع التواصل",
    "followup":     "حالة المتابعة",
    "achievement":  "نوع الإنجاز",
    "rating":       "التقييم",
}

# حالة الحصة المنفّذة (المحسوبة في الراتب/الإيراد)
SESSION_DONE = "تمت"

# ترتيب أيام الأسبوع العربية (السبت أول الأسبوع) → weekday بايثون (Mon=0)
ARABIC_WEEKDAYS = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
_AR_DAY_TO_PYWD = {  # السبت=5, الأحد=6, الاثنين=0 ...
    "السبت": 5, "الأحد": 6, "الاثنين": 0, "الثلاثاء": 1,
    "الأربعاء": 2, "الخميس": 3, "الجمعة": 4,
}

# ════════════════════════════════════════════════════════════════════════════
# 🧹  التطبيع والتحقق
# ════════════════════════════════════════════════════════════════════════════
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate(_ARABIC_DIGITS)}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate(_PERSIAN_DIGITS)})


def normalize_digits(s) -> str:
    """تحويل الأرقام العربية/الفارسية إلى أرقام لاتينية."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return str(s).translate(_DIGIT_MAP)


def clean_phone(s) -> str:
    """
    تطبيع رقم الهاتف المصري إلى صيغة 01XXXXXXXXX (11 رقمًا) كنص.
    يتعامل مع الأرقام المخزّنة كأرقام عشرية (1276598955.0) أو بأرقام عربية.
    """
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    raw = normalize_digits(s).strip()
    # إزالة .0 الناتجة عن float و أي رموز غير رقمية
    raw = re.sub(r"\.0$", "", raw)
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    # إزالة كود الدولة 20 إن وُجد (00 ثم 20، أو 20 مباشرة)
    if digits.startswith("0020"):
        digits = digits[4:]
    if digits.startswith("20") and len(digits) == 12:
        digits = digits[2:]
    # إضافة الصفر البادئ (الأرقام المخزّنة كأرقام تفقده)
    if len(digits) == 10 and digits[0] == "1":
        digits = "0" + digits
    return digits


def is_valid_egypt_phone(s) -> bool:
    d = clean_phone(s)
    return bool(re.fullmatch(r"01[0125]\d{8}", d))


def to_date(s):
    """تحويل أي صيغة تاريخ (نص/Timestamp/أرقام عربية) إلى date أو None."""
    try:
        if s is None or pd.isna(s):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    txt = normalize_digits(s).strip()
    if not txt or txt.lower() in ("nan", "none", "nat", "/////"):
        return None
    txt = txt.replace("\\", "/").replace("-", "/").replace(".", "/")
    for fmt in ("%Y/%m/%d", "%d/%m/%Y", "%m/%Y", "%Y/%m", "%d/%m/%y", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(txt, errors="coerce", dayfirst=True)
        return None if pd.isna(ts) else ts.date()
    except Exception:
        return None


def month_key(d) -> str:
    """مفتاح الشهر بصيغة YYYY-MM من تاريخ."""
    d = to_date(d)
    if d is None or (not isinstance(d, (date, datetime))):
        return ""
    return d.strftime("%Y-%m")


# ── الأوقات العربية (8:00 ص / 5:30 م) ──────────────────────────────────────
def parse_arabic_time(s):
    """تحويل '5:30 م' إلى datetime.time، أو None."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    txt = normalize_digits(s).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(ص|م)?\s*$", txt)
    if not m:
        return None
    h, mn, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap and not (1 <= h <= 12):   # صيغة 12 ساعة يجب أن تكون 1..12
        return None
    if ap == "م" and h != 12:
        h += 12
    elif ap == "ص" and h == 12:
        h = 0
    if not (0 <= h <= 23 and 0 <= mn <= 59):
        return None
    from datetime import time as _t
    return _t(h, mn)


def format_arabic_time(t) -> str:
    """تحويل datetime.time إلى '5:30 م'."""
    if t is None:
        return ""
    h, mn = t.hour, t.minute
    ap = "ص" if h < 12 else "م"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{mn:02d} {ap}"


def add_minutes(t, minutes: int):
    """إضافة دقائق إلى time وإرجاع time."""
    if t is None:
        return None
    base = datetime(2000, 1, 1, t.hour, t.minute)
    from datetime import timedelta
    return (base + timedelta(minutes=int(minutes))).time()


def arabic_weekday(d) -> str:
    """اسم اليوم العربي من تاريخ."""
    d = to_date(d)
    if not d:
        return ""
    inv = {v: k for k, v in _AR_DAY_TO_PYWD.items()}
    return inv.get(d.weekday(), "")


def parse_weekdays(s) -> list[str]:
    """تفكيك 'السبت، الاثنين' إلى قائمة أيام صحيحة بالترتيب."""
    if not s:
        return []
    txt = str(s).replace("،", ",").replace("/", ",").replace("-", ",")
    parts = [p.strip() for p in txt.split(",") if p.strip()]
    return [d for d in ARABIC_WEEKDAYS if d in parts]


def weekday_to_pywd(day_ar: str):
    return _AR_DAY_TO_PYWD.get(day_ar)


# ── جدول الأيام (وقت/مدة لكل يوم) ─────────────────────────────────────────────
# الصيغة المخزّنة: "السبت@8:00 ص@60 ؛ الاثنين@5:00 م@30"
_SCHED_DAY_SEP = " ؛ "
_SCHED_FLD_SEP = "@"


def format_day_schedule(items) -> str:
    """items = [(day_ar, time_str, minutes), ...] → نص مخزّن."""
    parts = []
    for day, t, m in items:
        if not day:
            continue
        parts.append(f"{day}{_SCHED_FLD_SEP}{t}{_SCHED_FLD_SEP}{int(m)}")
    return _SCHED_DAY_SEP.join(parts)


def parse_day_schedule(s):
    """نص جدول الأيام → [(day_ar, time_str, minutes:int), ...]، مرتّبة بترتيب الأسبوع."""
    out = []
    if not s or str(s).strip().lower() in ("", "nan", "none"):
        return out
    txt = str(s).replace("؛", ";").replace("|", ";")
    for part in txt.split(";"):
        fields = [f.strip() for f in part.split(_SCHED_FLD_SEP)]
        if len(fields) >= 3 and fields[0] in ARABIC_WEEKDAYS:
            mins = normalize_digits(fields[2])
            out.append((fields[0], fields[1], int(mins) if mins.isdigit() else 30))
    # ترتيب حسب أيام الأسبوع
    order = {d: i for i, d in enumerate(ARABIC_WEEKDAYS)}
    return sorted(out, key=lambda x: order.get(x[0], 99))


# ── حقول العرض "الكود — الاسم" ───────────────────────────────────────────────
DISPLAY_SEP = " — "


def make_display(code: str, name: str) -> str:
    code, name = str(code or "").strip(), str(name or "").strip()
    if code and name:
        return f"{code}{DISPLAY_SEP}{name}"
    return code or name


def code_of(label) -> str:
    """استخراج الكود من 'S-00001 — اسم'."""
    if not label:
        return ""
    return str(label).split(DISPLAY_SEP)[0].strip()


def options_from(df, code_col, name_col):
    """بناء قائمة خيارات [(label, code)] من جدول."""
    if df is None or df.empty or code_col not in df.columns:
        return []
    out = []
    for _, r in df.iterrows():
        code = str(r.get(code_col, "")).strip()
        if not code:
            continue
        name = str(r.get(name_col, "")).strip() if name_col in df.columns else ""
        out.append((make_display(code, name), code))
    return out
