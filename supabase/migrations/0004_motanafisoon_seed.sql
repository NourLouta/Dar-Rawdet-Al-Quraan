-- المتنافسون seed data — Phase B2.
-- Config values are seeded here, not hardcoded in application code, so
-- admin can retune points/levels/badges from the BI dashboard without a
-- redeploy (per the plan's point_rules/level_thresholds design).

insert into motanafisoon.seasons (name, start_date, end_date, price_egp, is_active)
values ('الموسم الأول', '2026-08-07', '2026-09-25', 637, true);

-- 10 activities, reconciled from the playbook's daily/weekly/appendix point
-- tables (confirmed as 10 distinct activities, not overlapping ranges).
insert into motanafisoon.point_rules (activity_type, points, unit, description) values
    ('تسميع للرفيق',           2,   'per_day',     'التسميع اليومي للرفيق'),
    ('حفظ الورد',              1,   'per_day',     'الحفظ اليومي'),
    ('مراجعة',                 1,   'per_day',     'المراجعة اليومية'),
    ('حضور الجلسة الأسبوعية',  3,   'per_week',    'حضور اللقاء الحيّ الأسبوعي (٩٠ د)'),
    ('سماع التفسير الأسبوعي',  1,   'per_week',    'سماع التفسير والأخطاء المتكررة'),
    ('أسبوع بلا غياب',         4,   'flat',        'مكافأة أسبوع كامل بلا غياب'),
    ('فوز تحدٍّ (فريق)',       4,   'flat',        'فوز الفريق في مواجهة أسبوعية'),
    ('مساعدة زميل',            1,   'flat',        'مساعدة زميل في الفريق'),
    ('وسام',                   2,   'flat',        'منح وسام تقديري'),
    ('إحضار صديق',             100, 'both_parties','إحالة ناجحة — ١٠٠ نقطة للطرفين');

-- Default curve — no thresholds are given in the source material.
-- Admin-tunable; adjust freely once real season-1 point totals are observed.
insert into motanafisoon.level_thresholds (level_order, level_name, icon, min_points) values
    (1, 'مبتدئ',        '🌱', 0),
    (2, 'حافظ مجتهد',   '📖', 30),
    (3, 'ثابت',          '⭐', 70),
    (4, 'سفير القرآن',   '🏆', 120),
    (5, 'نخبة الدار',    '👑', 180);

-- is_ad_hoc=false for the three streak-derivable badges (computable from
-- daily_logs/points_ledger); true for the two qualitative/teacher-judgment ones.
insert into motanafisoon.badges (code, name_ar, icon, description, is_ad_hoc) values
    ('full_week',        'أسبوع كامل',        '🔥', 'كل أيام الأسبوع بحالة كامل',        false),
    ('first_100',        'أول ١٠٠ نقطة',       '⭐', 'أول من يصل لـ١٠٠ نقطة تراكمية',      false),
    ('ten_day_streak',   '١٠ أيام متتالية',    '💎', '١٠ أيام متتالية بحالة كامل',         false),
    ('best_review',      'أقوى مراجعة',        '🧠', 'يُمنح بتقدير المعلمة',                true),
    ('best_buddy',       'أفضل رفيق',          '🤝', 'يُمنح بتقدير المعلمة/المشرفة',        true);

insert into motanafisoon.cards (code, scope, name_ar, icon, max_uses) values
    ('catch_up', 'member', 'استدراك',        '🌿', 1),
    ('rescue',   'member', 'إنقاذ',          '🛟', 1),
    ('pick_opponent', 'team', 'اختيار المنافس', '⚔️', 1);
