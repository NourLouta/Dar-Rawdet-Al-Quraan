# -*- coding: utf-8 -*-
"""
الإعدادات — إدارة البرامج وأسعارها والفروع دون الحاجة لتعديل الكود.

هذا هو الحل العام لأي ملاحظة مستقبلية من نوع «عندنا فرع/برنامج جديد»:
يُضاف من هنا في دقيقة، ويظهر فورًا في كل شاشات الإدخال والمالية.
"""
from __future__ import annotations
import streamlit as st

from .. import ui, state
from ..config import SEED_PROGRAM_RATES, SEED_BRANCHES
from ..schema import Program, Branch
from ..crud import Field, simple_crud


def render():
    ui.header("⚙️ الإعدادات", "البرامج والأسعار والفروع — بلا حاجة لتعديل برمجي")
    ui.guide("عن هذه الشاشة", """
**ما هي؟** المكان الوحيد الذي تُدار منه بيانات "مرجعية" تتغيّر بين حين وآخر: البرامج
الدراسية وأسعارها، وفروع الدار — بدل أن تكون مكتوبة داخل الكود.

**متى تستخدمها؟**
- عند فتح فرع جديد.
- عند إضافة برنامج دراسي جديد أو تغيير سعر برنامج قائم.
- **هذا هو الحل العام لأي طلب مستقبلي مشابه** — لا حاجة لطلب تعديل برمجي، أضيفيه بنفسك هنا
  وسيظهر فورًا في شاشات «التسجيلات» و«الطلاب» و«المالية».
""")
    ui.insight(
        "أي برنامج أو فرع تضيفه هنا يظهر تلقائيًا في شاشات «التسجيلات» و«الطلاب» و«المالية». "
        "لا داعي لطلب تعديل من المطوّر عند تغيّر الأسعار أو فتح فرع جديد.", "info", "💡")

    t_prog, t_branch = st.tabs(["💰 البرامج والأسعار", "🏢 الفروع"])

    with t_prog:
        st.caption("سعر ساعة المحفظ: اتركه صفرًا لأخذه من ملف المحفظين لكل محفظة على حدة.")
        simple_crud(
            sheet_key="programs", code_field=Program.CODE, name_field=Program.NAME,
            code_prefix_key="program", label="البرنامج",
            empty_msg="لا توجد برامج مُضافة بعد — تُستخدم حاليًا أسعار افتراضية عامة.",
            fields=[
                Field(Program.NAME, "اسم البرنامج", required=True,
                     help="مثال: قرآن، نور البيان، القاعدة النورانية"),
                Field(Program.STUDENT_RATE, "سعر ساعة الطالب (ج.م)", kind="number",
                     min_value=0.0, step=5.0, default=65),
                Field(Program.TEACHER_RATE, "سعر ساعة المحفظ (ج.م)", kind="number",
                     min_value=0.0, step=5.0, default=0,
                     help="اتركه 0 لأخذ السعر من ملف المحفظين"),
                Field(Program.NOTES, "ملاحظات", kind="textarea", default=""),
            ],
            seed_rows=lambda: [
                {Program.NAME: name, Program.STUDENT_RATE: sr, Program.TEACHER_RATE: (tr or 0)}
                for name, (sr, tr) in SEED_PROGRAM_RATES.items()
            ],
        )

    with t_branch:
        simple_crud(
            sheet_key="branches", code_field=Branch.CODE, name_field=Branch.NAME,
            code_prefix_key="branch", label="الفرع",
            empty_msg="لا توجد فروع مُضافة بعد — تُستخدم حاليًا قائمة افتراضية عامة.",
            fields=[
                Field(Branch.NAME, "اسم الفرع", required=True),
                Field(Branch.ADDRESS, "العنوان", default=""),
                Field(Branch.NOTES, "ملاحظات", kind="textarea", default=""),
            ],
            seed_rows=lambda: [{Branch.NAME: name} for name in SEED_BRANCHES],
        )
