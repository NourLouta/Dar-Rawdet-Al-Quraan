# -*- coding: utf-8 -*-
"""
الإعدادات والثوابت والهوية البصرية — دار روضة القرآن.

كل القيم القابلة للتعديل في مكان واحد: معرّف ملف Google، ثوابت المالية،
ألوان وخطوط الهوية. لا منطق هنا — مجرد إعدادات.
"""
from __future__ import annotations
import os
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# 📁 المسارات
# ────────────────────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
FONTS_DIR  = ASSETS_DIR / "fonts"
LOGO_PATH  = ROOT_DIR / "Dar Logo.png"

# ────────────────────────────────────────────────────────────────────────────
# 📊 Google Sheets — الملف الجديد (قاعدة البيانات)
# ────────────────────────────────────────────────────────────────────────────
# الملف الجديد المنظّم (علائقي). يمكن تجاوزه عبر st.secrets["sheet"]["id"].
SHEET_ID = "1U5h-2Z6_Qt_RvdGN7mw-rArDt_dfbRojdUyu-jXeDmY"

# أسماء أوراق العمل في الملف الجديد
WS_LOOKUPS     = "القوائم المرجعية"
WS_TEACHERS    = "المحفظين"
WS_PARENTS     = "أولياء الأمور"
WS_STUDENTS    = "الطلاب"
WS_ENROLLMENTS = "التسجيلات"
WS_SESSIONS    = "الحصص"
WS_DASHBOARD   = "لوحة التحكم"

# أوراق جديدة للتقييمات (ينشئها التطبيق تلقائيًا إذا لم تكن موجودة)
WS_PARENT_FEEDBACK  = "تقييمات أولياء الأمور"
WS_TEACHER_FEEDBACK = "ردود تقييم المحفظين"   # ردود Google Form للمعلمين

# أوراق الإعدادات القابلة للتعديل من شاشة «الإعدادات» (تُنشأ تلقائيًا عند أول إضافة)
WS_PROGRAMS = "البرامج"     # البرامج الدراسية وأسعارها (بدل الأسعار المكتوبة في الكود)
WS_BRANCHES = "الفروع"      # فروع الدار

# ────────────────────────────────────────────────────────────────────────────
# 💾 مصدر بيانات محلي (وضع التجربة دون اتصال)
# ────────────────────────────────────────────────────────────────────────────
# لو ضُبط مسار ملف xlsx محلي (متغيّر بيئة DAR_LOCAL_XLSX أو ملف data/قاعدة_البيانات.xlsx)
# يقرأ التطبيق منه عند غياب حساب خدمة Google — مفيد للتجربة والعرض دون إنترنت.
def _resolve_local_xlsx():
    env = os.environ.get("DAR_LOCAL_XLSX")
    if env and Path(env).exists():
        return Path(env)
    candidate = ROOT_DIR / "data" / "قاعدة_البيانات.xlsx"
    if candidate.exists():
        return candidate
    return None

LOCAL_XLSX = _resolve_local_xlsx()

# كل الأوراق المقروءة عند بدء التشغيل
READ_WORKSHEETS = [
    WS_LOOKUPS, WS_TEACHERS, WS_PARENTS, WS_STUDENTS,
    WS_ENROLLMENTS, WS_SESSIONS, WS_PARENT_FEEDBACK, WS_TEACHER_FEEDBACK,
    WS_PROGRAMS, WS_BRANCHES,
]

# ────────────────────────────────────────────────────────────────────────────
# 💰 ثوابت المالية
# ────────────────────────────────────────────────────────────────────────────
VODAFONE_CASH_FEE = 1.01    # مضاعف رسوم تحويل فودافون كاش (1%)
ROUND_TO          = 5       # تقريب صافي التحويل لأعلى لأقرب 5 جنيه
STUDENT_HOURLY    = 65      # سعر الساعة الافتراضي للطالب (ج.م)
TEACHER_HOURLY_DEFAULT = 35  # سعر ساعة المعلم الافتراضي إن لم يُحدَّد
TEACHER_HOURLY_EXPERT  = 40  # سعر ساعة المعلم الخبير (مرجعي فقط)
CURRENCY = "ج.م"

# أسعار البرامج وفروع الدار: القيم الحقيقية تُدار من شاشة «⚙️ الإعدادات» وتُخزَّن
# في ورقتي "البرامج" و"الفروع" على Google Sheet — لا حاجة لتعديل الكود أبدًا لإضافة
# برنامج أو فرع جديد. القوائم أدناه هي بذور افتراضية تُستخدم فقط أول مرة (قبل أن
# يضيف أحد أي صف في الورقتين)، حتى لا تظهر الشاشة فارغة تمامًا في أول استخدام.
# سعر ساعة المحفظ None يعني: يُؤخذ من ملف المحفظين.
SEED_PROGRAM_RATES = {
    "قرآن":                    (65, None),
    "نور البيان":              (70, 50),
    "قرآن و نور البيان":       (70, 50),
    "القاعدة النورانية":       (100, 60),
    "النورانية":               (100, 60),
}

SEED_BRANCHES = [
    "فرع مدينة نصر — 42 ش متولي الشعراوي (أمام مستشفى الماسة)",
    "فرع الشيمي — 16 ش د. الشيمي (أمام مدرسة منارة الإيمان)",
    "أونلاين",
    "درس منزلي",
]

# ────────────────────────────────────────────────────────────────────────────
# 🔢 توليد الأكواد
# ────────────────────────────────────────────────────────────────────────────
CODE_PREFIX = {
    "student":    ("S-",  5),   # S-00001
    "teacher":    ("T-",  4),   # T-0001
    "parent":     ("P-",  4),   # P-0001
    "enrollment": ("E-",  5),   # E-00001
    "session":    ("SS-", 6),   # SS-000001
    "pfeedback":  ("PF-", 5),   # PF-00001
    "program":    ("PR-", 2),   # PR-01
    "branch":     ("BR-", 2),   # BR-01
}

# ────────────────────────────────────────────────────────────────────────────
# 🎨 الهوية البصرية — تركواز + ذهبي (مطابق للشعار: تركواز #105050 / ذهبي #D0B050)
# ────────────────────────────────────────────────────────────────────────────
class DarTheme:
    PRIMARY        = "#1B6B5A"
    PRIMARY_DARK   = "#134E41"
    PRIMARY_LIGHT  = "#2A8C75"
    PRIMARY_GLOW   = "rgba(27,107,90,0.25)"
    GOLD           = "#C9A84C"
    GOLD_DARK      = "#A8892E"
    GOLD_LIGHT     = "#E2C06A"
    GOLD_GLOW      = "rgba(201,168,76,0.25)"
    SECONDARY      = "#1A1A1A"
    SECONDARY_SOFT = "#2C2C2C"
    ACCENT_EMERALD  = "#10B981"
    ACCENT_AMBER    = "#F59E0B"
    ACCENT_CRIMSON  = "#EF4444"
    ACCENT_SAPPHIRE = "#3B82F6"
    ACCENT_VIOLET   = "#8B5CF6"
    ACCENT_ROSE     = "#F43F5E"
    ACCENT_TEAL     = "#14B8A6"
    ACCENT_ORANGE   = "#F97316"
    BG_WHITE        = "#FFFFFF"
    BG_LIGHT        = "#F0F7F5"
    BG_CARD         = "#F7FBF9"
    BG_DARK         = "#0A1A16"
    TEXT_PRIMARY    = "#1A1A1A"
    TEXT_SECONDARY  = "#6B7280"
    TEXT_LIGHT      = "#FFFFFF"
    TEXT_TEAL       = "#1B6B5A"
    TEXT_GOLD       = "#C9A84C"
    BORDER_RADIUS        = "14px"
    BORDER_RADIUS_LARGE  = "22px"
    BORDER_RADIUS_PILL   = "50px"
    SHADOW_SMALL  = "0 2px 8px rgba(27,107,90,0.12)"
    SHADOW_MEDIUM = "0 6px 20px rgba(27,107,90,0.18)"
    SHADOW_LARGE  = "0 12px 40px rgba(27,107,90,0.22)"
    SHADOW_HOVER  = "0 20px 60px rgba(27,107,90,0.30)"
    SHADOW_GLOW   = "0 0 30px rgba(27,107,90,0.35)"
    SHADOW_GOLD   = "0 0 30px rgba(201,168,76,0.35)"
    FONT_FAMILY   = "'Cairo', 'Tajawal', 'Arial', sans-serif"

    # ألوان PDF (RGB 0-1) — للتقارير والتقاويم
    PDF_TEAL   = (0.106, 0.420, 0.353)   # #1B6B5A
    PDF_TEAL_D = (0.075, 0.306, 0.255)   # #134E41
    PDF_GOLD   = (0.788, 0.659, 0.298)   # #C9A84C
    PDF_GOLD_L = (0.886, 0.753, 0.416)   # #E2C06A
    PDF_LIGHT  = (0.941, 0.969, 0.961)   # #F0F7F5
    PDF_WHITE  = (1, 1, 1)
    PDF_DARK   = (0.10, 0.10, 0.10)
    PDF_GREY   = (0.42, 0.45, 0.50)

    @staticmethod
    def gradient(c1, c2, angle=135):
        return f"linear-gradient({angle}deg, {c1} 0%, {c2} 100%)"

    @staticmethod
    def teal_gradient(angle=135):
        return DarTheme.gradient(DarTheme.PRIMARY_DARK, DarTheme.PRIMARY_LIGHT, angle)

    @staticmethod
    def gold_gradient(angle=135):
        return DarTheme.gradient(DarTheme.GOLD_DARK, DarTheme.GOLD_LIGHT, angle)

    @staticmethod
    def hero_gradient(angle=135):
        return DarTheme.gradient(DarTheme.PRIMARY_DARK, DarTheme.PRIMARY, angle)


T = DarTheme

CHART_COLORS = [
    T.PRIMARY, T.GOLD, T.ACCENT_EMERALD, T.ACCENT_SAPPHIRE,
    T.ACCENT_VIOLET, T.ACCENT_AMBER, T.ACCENT_ROSE, T.ACCENT_TEAL,
    T.ACCENT_ORANGE, T.ACCENT_CRIMSON, "#06B6D4", "#84CC16",
]
