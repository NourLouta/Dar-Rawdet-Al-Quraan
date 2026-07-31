-- المتنافسون schema — Phase B1. DDL only, no data (seed data is 0004).
-- Entity/rule numbers below are sourced from the playbook
-- (motanafisoonplaybookmobile.html) and the approved plan.

create schema if not exists motanafisoon;

create table motanafisoon.seasons (
    id                   bigint generated always as identity primary key,
    name                 text not null,
    start_date           date not null,
    end_date             date not null,
    price_egp            numeric(10,2) not null default 637,
    refund_policy_version int not null default 1,
    is_active            boolean not null default true
);

create table motanafisoon.supervisors (
    id        bigint generated always as identity primary key,
    name      text not null,
    phone     text not null unique,
    max_teams int not null default 3
);

create table motanafisoon.teams (
    id             bigint generated always as identity primary key,
    season_id      bigint not null references motanafisoon.seasons(id),
    name           text not null,
    color          text,
    logo_url       text,
    supervisor_id  bigint references motanafisoon.supervisors(id),
    unique (season_id, name)
    -- Deliberately no peer "team leader" column — per the playbook's RACI
    -- table, oversight is exclusively the assigned المشرفة (supervisor).
);

-- Enforces "max 3 teams per supervisor" (max_teams default 3). RLS can't
-- limit a role's row *count*, so this is a trigger, not a policy.
create or replace function motanafisoon.check_supervisor_team_cap()
returns trigger as $$
declare
    cap int;
    current_count int;
begin
    if new.supervisor_id is null then
        return new;
    end if;
    select max_teams into cap from motanafisoon.supervisors where id = new.supervisor_id;
    select count(*) into current_count from motanafisoon.teams
        where supervisor_id = new.supervisor_id and id <> coalesce(new.id, -1);
    if current_count >= cap then
        raise exception 'supervisor % already supervises the maximum % teams', new.supervisor_id, cap;
    end if;
    return new;
end;
$$ language plpgsql;

create trigger trg_supervisor_team_cap
    before insert or update of supervisor_id on motanafisoon.teams
    for each row execute function motanafisoon.check_supervisor_team_cap();

create table motanafisoon.members (
    id         bigint generated always as identity primary key,
    season_id  bigint not null references motanafisoon.seasons(id),
    team_id    bigint references motanafisoon.teams(id),
    full_name  text not null,
    phone      text not null,
    joined_at  timestamptz not null default now(),
    status     text not null default 'نشط',
    unique (season_id, phone)
);

-- Weekly-rotating رفيق (accountability buddy) history.
create table motanafisoon.buddy_pairings (
    id                bigint generated always as identity primary key,
    member_id         bigint not null references motanafisoon.members(id),
    partner_member_id bigint not null references motanafisoon.members(id),
    week_number       int not null check (week_number between 1 and 8),
    unique (member_id, week_number),
    check (member_id <> partner_member_id)
);

-- Links a Supabase Auth identity to a domain entity + role. Every RLS
-- policy below keys off this table.
create table motanafisoon.profiles (
    id            uuid primary key references auth.users(id) on delete cascade,
    role          text not null check (role in ('member','supervisor','admin')),
    member_id     bigint references motanafisoon.members(id),
    supervisor_id bigint references motanafisoon.supervisors(id),
    display_name  text,
    check (
        (role = 'member' and member_id is not null and supervisor_id is null) or
        (role = 'supervisor' and supervisor_id is not null and member_id is null) or
        (role = 'admin' and member_id is null and supervisor_id is null)
    )
);

-- Supervisor-entered only (confirmed decision — matches the playbook's
-- RACI table: member=C/consulted, supervisor=R/executor on data entry).
-- Source of the "✓ كامل / ~ جزئي / ✗ غياب" and "آخر ٥" streak columns.
create table motanafisoon.daily_logs (
    id                bigint generated always as identity primary key,
    member_id         bigint not null references motanafisoon.members(id),
    log_date          date not null,
    memorized         boolean not null default false,
    reviewed          boolean not null default false,
    recited_to_buddy  boolean not null default false,
    tajweed_score     numeric(5,2),
    status            text not null check (status in ('كامل','جزئي','غياب')),
    submitted_by      uuid references motanafisoon.profiles(id),
    created_at        timestamptz not null default now(),
    unique (member_id, log_date)
);

-- Config, not code — 10 confirmed activities (seeded in 0004), admin-tunable
-- via the BI dashboard without a redeploy.
create table motanafisoon.point_rules (
    id            bigint generated always as identity primary key,
    activity_type text not null unique,
    points        int not null,
    unit          text not null check (unit in ('per_day','per_week','flat','both_parties')),
    description   text,
    is_active     boolean not null default true
);

-- Append-only ledger — no mutation of past rows. Disputes (48h window per
-- the playbook) and the week-6 "جولة الحسم" ×2 event become new rows
-- referencing the original, so totals stay a plain SUM() and every point
-- award has a full audit trail.
create table motanafisoon.points_ledger (
    id                   bigint generated always as identity primary key,
    member_id            bigint references motanafisoon.members(id),
    team_id              bigint references motanafisoon.teams(id),
    activity_type        text not null references motanafisoon.point_rules(activity_type),
    points               int not null,
    log_date             date not null,
    source_daily_log_id  bigint references motanafisoon.daily_logs(id),
    week_number          int check (week_number between 1 and 8),
    is_doubled           boolean not null default false,
    awarded_by           uuid references motanafisoon.profiles(id),
    dispute_status       text not null default 'none' check (dispute_status in ('none','disputed','resolved')),
    dispute_deadline     timestamptz,
    created_at           timestamptz not null default now(),
    check (member_id is not null or team_id is not null)
);

-- 5 rows, 🌱→📖→⭐→🏆→👑. No thresholds exist in the source material —
-- seeded with a starting default curve (0004), fully admin-tunable.
create table motanafisoon.level_thresholds (
    id          bigint generated always as identity primary key,
    level_order int not null unique,
    level_name  text not null,
    icon        text not null,
    min_points  int not null
);

-- 🔥/⭐/💎 are rule-computable from daily_logs/points_ledger streaks;
-- 🧠/🤝 are inherently qualitative (teacher/admin discretion) — is_ad_hoc
-- distinguishes which is which for the awarding UI.
create table motanafisoon.badges (
    id          bigint generated always as identity primary key,
    code        text not null unique,
    name_ar     text not null,
    icon        text not null,
    description text,
    is_ad_hoc   boolean not null default true
);

create table motanafisoon.member_badges (
    id          bigint generated always as identity primary key,
    member_id   bigint not null references motanafisoon.members(id),
    badge_id    bigint not null references motanafisoon.badges(id),
    awarded_by  uuid references motanafisoon.profiles(id),
    awarded_at  timestamptz not null default now(),
    week_number int check (week_number between 1 and 8)
);

-- 🌿 استدراك / 🛟 إنقاذ (member scope), ⚔️ اختيار المنافس (team scope).
create table motanafisoon.cards (
    id        bigint generated always as identity primary key,
    code      text not null unique,
    scope     text not null check (scope in ('member','team')),
    name_ar   text not null,
    icon      text not null,
    max_uses  int not null default 1
);

create table motanafisoon.card_usages (
    id        bigint generated always as identity primary key,
    card_id   bigint not null references motanafisoon.cards(id),
    member_id bigint references motanafisoon.members(id),
    team_id   bigint references motanafisoon.teams(id),
    used_at   timestamptz not null default now(),
    week_number int check (week_number between 1 and 8),
    notes     text,
    check (member_id is not null or team_id is not null)
);

-- week 4 "فلنرتقي" (adjacent-rank matchups), week 5 "اختيار المنافس"
-- (tier picks: 🥇1-4 🥈5-7 🥉8-10 🔴last), week 6 "جولة الحسم" (×2 all week).
-- is_locked enforces the playbook's "irrevocable once announced" rule for
-- week 5's opponent choice.
create table motanafisoon.weekly_events (
    id           bigint generated always as identity primary key,
    season_id    bigint not null references motanafisoon.seasons(id),
    week_number  int not null check (week_number between 1 and 8),
    event_type   text not null check (event_type in ('فلنرتقي','اختيار المنافس','جولة الحسم')),
    config       jsonb not null default '{}'::jsonb,
    announced_at timestamptz,
    is_locked    boolean not null default false,
    unique (season_id, week_number, event_type)
);

create table motanafisoon.challenges (
    id               bigint generated always as identity primary key,
    season_id        bigint not null references motanafisoon.seasons(id),
    week_number      int not null check (week_number between 1 and 8),
    team_a_id        bigint not null references motanafisoon.teams(id),
    team_b_id        bigint not null references motanafisoon.teams(id),
    winner_team_id   bigint references motanafisoon.teams(id),
    points_awarded   int,
    decided_at       timestamptz,
    check (team_a_id <> team_b_id)
);

-- Escalation table: day-1 absence -> buddy reminder; 2-3 days -> supervisor
-- call; >4 days/week or >3/month -> exit unless عذر قهري freezes the count
-- (illness/travel/exams per the excuse policy).
create table motanafisoon.attendance_policy_events (
    id           bigint generated always as identity primary key,
    member_id    bigint not null references motanafisoon.members(id),
    event_type   text not null check (event_type in
                    ('reminder','supervisor_call','warning','exit','excuse_granted')),
    reason       text,
    event_date   date not null default current_date,
    recorded_by  uuid references motanafisoon.profiles(id)
);

-- Full 8-week (Aug 7 - Sep 25 2026) day-by-day memorization/review calendar.
create table motanafisoon.curriculum_days (
    id            bigint generated always as identity primary key,
    season_id     bigint not null references motanafisoon.seasons(id),
    calendar_date date not null,
    day_type      text not null check (day_type in ('memorize','rest','cumulative_review','exam')),
    surah         text,
    ayah_range    text,
    review_target text,
    unique (season_id, calendar_date)
);

-- Built now, UI deferred per the plan — v1 payment tracking stays
-- manual/WhatsApp; these tables just avoid a future schema migration if
-- brought in-app later.
create table motanafisoon.payments (
    id         bigint generated always as identity primary key,
    member_id  bigint not null references motanafisoon.members(id),
    season_id  bigint not null references motanafisoon.seasons(id),
    amount_egp numeric(10,2) not null default 637,
    paid_at    timestamptz,
    method     text,
    status     text not null default 'pending',
    notes      text
);

create table motanafisoon.refund_requests (
    id           bigint generated always as identity primary key,
    payment_id   bigint not null references motanafisoon.payments(id),
    requested_at timestamptz not null default now(),
    tier         text,          -- matches the playbook's refund-tier table (100%/80%/50%/0%)
    amount_egp   numeric(10,2),
    status       text not null default 'pending',
    decided_by   uuid references motanafisoon.profiles(id),
    decided_at   timestamptz
);

-- The one explicit real-time dashboard behavior in the playbook:
-- "أي فرد التزامه أقل من ٦٠٪ ليومين متتاليين يُرفَع تلقائيًا... إلى «منطقة
-- المتابعة»" — a plain view (not a cron job), trivial at 40-80 members.
create view motanafisoon.v_followup_zone as
with daily_commitment as (
    select
        member_id,
        log_date,
        case status when 'كامل' then 100.0 when 'جزئي' then 50.0 else 0.0 end as commitment_pct
    from motanafisoon.daily_logs
),
last_two_days as (
    select
        member_id,
        log_date,
        commitment_pct,
        row_number() over (partition by member_id order by log_date desc) as rn
    from daily_commitment
)
select m.id as member_id, m.full_name, m.team_id
from motanafisoon.members m
where (
    select bool_and(commitment_pct < 60.0)
    from last_two_days d
    where d.member_id = m.id and d.rn <= 2
) is true
and (select count(*) from last_two_days d where d.member_id = m.id) >= 2;

-- ── Indexes ──────────────────────────────────────────────────────────────
create index idx_teams_season on motanafisoon.teams(season_id);
create index idx_teams_supervisor on motanafisoon.teams(supervisor_id);
create index idx_members_season on motanafisoon.members(season_id);
create index idx_members_team on motanafisoon.members(team_id);
create index idx_buddy_pairings_member on motanafisoon.buddy_pairings(member_id);
create index idx_daily_logs_member_date on motanafisoon.daily_logs(member_id, log_date);
create index idx_points_ledger_member on motanafisoon.points_ledger(member_id);
create index idx_points_ledger_team on motanafisoon.points_ledger(team_id);
create index idx_points_ledger_week on motanafisoon.points_ledger(week_number);
create index idx_member_badges_member on motanafisoon.member_badges(member_id);
create index idx_card_usages_member on motanafisoon.card_usages(member_id);
create index idx_card_usages_team on motanafisoon.card_usages(team_id);
create index idx_challenges_season_week on motanafisoon.challenges(season_id, week_number);
create index idx_attendance_events_member on motanafisoon.attendance_policy_events(member_id);
create index idx_curriculum_days_season on motanafisoon.curriculum_days(season_id);
create index idx_payments_member on motanafisoon.payments(member_id);
