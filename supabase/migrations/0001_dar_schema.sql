-- Dar (تسجيلات/حصص) normalized schema — Phase A1.
-- DDL only, no data. Mirrors dar/schema.py's field lists but with real FKs
-- instead of denormalized name/phone copies, and a real day-schedule table
-- instead of the encoded "يوم@وقت@دقائق؛..." string.

create schema if not exists dar;

-- ── قوائم مرجعية (يحل محل ورقة "القوائم المرجعية" الواحدة) ──────────────────
create table dar.lookup_lists (
    id          bigint generated always as identity primary key,
    list_key    text not null,          -- e.g. 'time_slots', 'levels', 'surahs'
    value_ar    text not null,
    sort_order  int not null default 0,
    is_active   boolean not null default true,
    unique (list_key, value_ar)
);

create table dar.branches (
    id       bigint generated always as identity primary key,
    code     text not null unique,
    name     text not null,
    address  text default '',
    notes    text default '',
    is_active boolean not null default true
);

create table dar.programs (
    id                 bigint generated always as identity primary key,
    code               text not null unique,
    name               text not null,
    student_hourly_rate numeric(10,2),
    teacher_hourly_rate numeric(10,2),  -- null = take from the teacher's own rate
    notes              text default '',
    is_active          boolean not null default true
);

create table dar.teachers (
    id               bigint generated always as identity primary key,
    code             text not null unique,
    full_name        text not null,
    gender           text,
    phone            text,
    whatsapp         text,
    governorate      text,
    qualification    text,
    experience_years numeric(5,1),
    teaches_category text,
    study_type       text,
    work_system      text,
    hourly_rate      numeric(10,2),
    min_sessions     int,
    contract_status  text,
    start_date       date,
    preferred_timing text,
    pay_method       text,
    special_in       text,
    notes            text default ''
);

create table dar.parents (
    id        bigint generated always as identity primary key,
    code      text not null unique,
    full_name text not null,
    phone     text,
    whatsapp  text,
    address   text,
    email     text,
    source    text,
    reg_date  date,
    notes     text default ''
    -- n_kids is derived via count(students) at query time, not stored
);

create table dar.students (
    id              bigint generated always as identity primary key,
    code            text not null unique,
    full_name       text not null,
    birth_date      date,
    gender          text,
    category        text,
    parent_id       bigint references dar.parents(id),
    relation        text,               -- ولي الأمر relation to student
    study_type      text,
    branch_id       bigint references dar.branches(id),
    level           text,
    current_surah   text,
    status          text,
    stop_reason     text,
    sub_system      text,
    sub_value       numeric(10,2),
    reg_date        date,
    preferred_days  text,
    notes           text default ''
    -- age is derived from birth_date at query time, not stored
);

create table dar.enrollments (
    id                  bigint generated always as identity primary key,
    code                text not null unique,
    student_id          bigint not null references dar.students(id),
    teacher_id          bigint not null references dar.teachers(id),
    program_id          bigint references dar.programs(id),
    study_type          text,
    start_date          date,
    end_date            date,
    sub_value           numeric(10,2),
    session_price_ref   numeric(10,2),
    student_hourly_rate numeric(10,2),  -- per-enrollment override; falls back to program rate
    teacher_hourly_rate numeric(10,2),
    status              text not null default 'نشط',
    notes               text default ''
);

-- Replaces WEEK_DAYS / SESS_TIME / SESS_MIN / DAY_SCHEDULE — one row per
-- weekday so each day can carry its own time/duration natively.
create table dar.enrollment_schedule_days (
    id                bigint generated always as identity primary key,
    enrollment_id     bigint not null references dar.enrollments(id) on delete cascade,
    weekday           text not null check (weekday in
                        ('السبت','الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة')),
    session_time      text not null,   -- kept as Arabic-formatted text ("5:00 م") for display fidelity
    duration_minutes  int not null,
    unique (enrollment_id, weekday)
);

create table dar.sessions (
    id                bigint generated always as identity primary key,
    code              text not null unique,
    enrollment_id     bigint not null references dar.enrollments(id),
    session_date      date not null,
    month             text generated always as (to_char(session_date, 'YYYY-MM')) stored,
    start_time        text,
    end_time          text,
    duration_minutes  int,
    status            text not null default 'تمت',
    cancel_reason     text,
    surah             text,
    ayah_from         text,
    ayah_to           text,
    amount_memorized  text,
    rating            text,
    notes             text default ''
);

create table dar.parent_feedback (
    id           bigint generated always as identity primary key,
    code         text not null unique,
    student_id   bigint not null references dar.students(id),
    month        text,
    score        numeric(4,1),
    satisfaction text,
    notes        text default '',
    feedback_date date,
    source       text
);

create table dar.teacher_feedback (
    id            bigint generated always as identity primary key,
    teacher_id    bigint references dar.teachers(id),
    submitted_at  timestamptz not null default now(),
    raw_response  jsonb not null default '{}'::jsonb  -- Google Form response capture, v1
);

-- ── Indexes ──────────────────────────────────────────────────────────────
create index idx_students_parent on dar.students(parent_id);
create index idx_students_branch on dar.students(branch_id);
create index idx_enrollments_student on dar.enrollments(student_id);
create index idx_enrollments_teacher on dar.enrollments(teacher_id);
create index idx_enrollments_program on dar.enrollments(program_id);
create index idx_enrollments_status on dar.enrollments(status);
create index idx_schedule_days_enrollment on dar.enrollment_schedule_days(enrollment_id);
create index idx_sessions_enrollment on dar.sessions(enrollment_id);
create index idx_sessions_date on dar.sessions(session_date);
create index idx_sessions_month on dar.sessions(month);
create index idx_parent_feedback_student on dar.parent_feedback(student_id);
