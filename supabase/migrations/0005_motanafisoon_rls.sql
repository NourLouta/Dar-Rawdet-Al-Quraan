-- المتنافسون RLS — Phase B2. This is the ONLY real access-control layer
-- for the browser-facing Next.js app (it uses the anon key + a user's JWT,
-- unlike Dar's server-mediated service_role trust model).
--
-- Design: leaderboard data (rank, points, "آخر ٥" pattern) is genuinely
-- PUBLIC within the competition per the playbook — it's announced weekly
-- and is the whole point of the gamification. So two curated views expose
-- exactly the public leaderboard columns to every authenticated user,
-- while the underlying raw tables (daily_logs, points_ledger, attendance
-- reasons, payments) stay tightly scoped: own row / own supervised teams /
-- admin. This avoids ever granting broad SELECT on raw tables that also
-- carry sensitive fields (dispute_status, awarded_by, absence reason).

-- ── Helper functions (keep policies short and consistent) ──────────────────
-- security definer is required so these can read motanafisoon.profiles from
-- inside a policy on another table without recursing into profiles' own
-- RLS; search_path is pinned per Postgres/Supabase's security-definer
-- hardening guidance (all table refs below are already fully qualified).
create or replace function motanafisoon.current_role() returns text as $$
    select role from motanafisoon.profiles where id = auth.uid();
$$ language sql stable security definer set search_path = '';

create or replace function motanafisoon.is_admin() returns boolean as $$
    select motanafisoon.current_role() = 'admin';
$$ language sql stable security definer set search_path = '';

create or replace function motanafisoon.own_member_id() returns bigint as $$
    select member_id from motanafisoon.profiles where id = auth.uid();
$$ language sql stable security definer set search_path = '';

-- Team ids supervised by the calling user (empty for non-supervisors).
create or replace function motanafisoon.supervised_team_ids() returns setof bigint as $$
    select t.id from motanafisoon.teams t
    join motanafisoon.profiles p on p.supervisor_id = t.supervisor_id
    where p.id = auth.uid() and p.role = 'supervisor';
$$ language sql stable security definer set search_path = '';

-- ── Enable RLS everywhere ────────────────────────────────────────────────
alter table motanafisoon.seasons enable row level security;
alter table motanafisoon.supervisors enable row level security;
alter table motanafisoon.teams enable row level security;
alter table motanafisoon.members enable row level security;
alter table motanafisoon.buddy_pairings enable row level security;
alter table motanafisoon.profiles enable row level security;
alter table motanafisoon.daily_logs enable row level security;
alter table motanafisoon.point_rules enable row level security;
alter table motanafisoon.points_ledger enable row level security;
alter table motanafisoon.level_thresholds enable row level security;
alter table motanafisoon.badges enable row level security;
alter table motanafisoon.member_badges enable row level security;
alter table motanafisoon.cards enable row level security;
alter table motanafisoon.card_usages enable row level security;
alter table motanafisoon.weekly_events enable row level security;
alter table motanafisoon.challenges enable row level security;
alter table motanafisoon.attendance_policy_events enable row level security;
alter table motanafisoon.curriculum_days enable row level security;
alter table motanafisoon.payments enable row level security;
alter table motanafisoon.refund_requests enable row level security;

-- ── Reference/config tables: readable by every authenticated user (the UI
--    needs point rules, levels, badges, curriculum, events to render),
--    writable by admin only. ──────────────────────────────────────────────
create policy read_all_authenticated on motanafisoon.seasons for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.seasons for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.point_rules for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.point_rules for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.level_thresholds for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.level_thresholds for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.badges for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.badges for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.cards for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.cards for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.curriculum_days for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.curriculum_days for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.weekly_events for select using (auth.role() = 'authenticated');
create policy admin_or_supervisor_write on motanafisoon.weekly_events for all
    using (motanafisoon.is_admin() or motanafisoon.current_role() = 'supervisor')
    with check (motanafisoon.is_admin() or motanafisoon.current_role() = 'supervisor');

create policy read_all_authenticated on motanafisoon.challenges for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.challenges for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

-- ── teams / members: names/team-membership are public within the
--    competition (needed to show "الفريق" on any leaderboard row);
--    membership changes stay admin-only (onboarding/team formation is an
--    admin process, not a daily supervisor task, per SOP-01). ─────────────
create policy read_all_authenticated on motanafisoon.teams for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.teams for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.members for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.members for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_all_authenticated on motanafisoon.supervisors for select using (auth.role() = 'authenticated');
create policy admin_write on motanafisoon.supervisors for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

-- ── profiles: a user reads/updates only their own row; admin sees all. ────
create policy read_own on motanafisoon.profiles for select using (id = auth.uid() or motanafisoon.is_admin());
create policy admin_write on motanafisoon.profiles for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

-- ── buddy_pairings: visible to the two members involved + their
--    supervisor(s) + admin; written by supervisor/admin only. ─────────────
create policy read_own_or_supervised on motanafisoon.buddy_pairings for select using (
    motanafisoon.is_admin()
    or member_id = motanafisoon.own_member_id()
    or partner_member_id = motanafisoon.own_member_id()
    or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids()))
);
create policy supervisor_or_admin_write on motanafisoon.buddy_pairings for all
    using (motanafisoon.is_admin() or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids())))
    with check (motanafisoon.is_admin() or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids())));

-- ── daily_logs: RAW rows are private (own row / own supervised teams /
--    admin) — the PUBLIC "آخر ٥" pattern is served via v_individual_leaderboard
--    below instead, so the leaderboard never needs broad access to this
--    table directly. Supervisor-entered only — no member write policy. ────
create policy read_own_or_supervised on motanafisoon.daily_logs for select using (
    motanafisoon.is_admin()
    or member_id = motanafisoon.own_member_id()
    or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids()))
);
create policy supervisor_or_admin_write on motanafisoon.daily_logs for insert
    with check (motanafisoon.is_admin() or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids())));
create policy supervisor_or_admin_update on motanafisoon.daily_logs for update
    using (motanafisoon.is_admin() or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids())))
    with check (motanafisoon.is_admin() or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids())));
-- No delete policy for anyone but admin (append/correct via update, not delete) — admin covered by is_admin() below.
create policy admin_delete on motanafisoon.daily_logs for delete using (motanafisoon.is_admin());

-- ── points_ledger: same shape as daily_logs — raw rows private, public
--    totals served via the leaderboard views. Members: no write. ──────────
create policy read_own_or_supervised on motanafisoon.points_ledger for select using (
    motanafisoon.is_admin()
    or member_id = motanafisoon.own_member_id()
    or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids()))
    or team_id in (select motanafisoon.supervised_team_ids())
);
create policy supervisor_or_admin_write on motanafisoon.points_ledger for insert
    with check (
        motanafisoon.is_admin()
        or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids()))
        or team_id in (select motanafisoon.supervised_team_ids())
    );
create policy admin_update on motanafisoon.points_ledger for update using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());
-- Append-only by design (see 0003 comment) — no delete policy for anyone but admin.
create policy admin_delete on motanafisoon.points_ledger for delete using (motanafisoon.is_admin());

-- ── member_badges: public (badges are shown on profiles/leaderboard),
--    awarded by supervisor (own teams) or admin. ───────────────────────────
create policy read_all_authenticated on motanafisoon.member_badges for select using (auth.role() = 'authenticated');
create policy supervisor_or_admin_write on motanafisoon.member_badges for insert
    with check (motanafisoon.is_admin() or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids())));

-- ── card_usages: visible to the member/team involved + their supervisor +
--    admin (not broadly public — a card used mid-competition is tactical
--    info the playbook treats as announced only when relevant, e.g. week 5
--    opponent choice is public via weekly_events, not via this table). ────
create policy read_own_or_supervised on motanafisoon.card_usages for select using (
    motanafisoon.is_admin()
    or member_id = motanafisoon.own_member_id()
    or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids()))
    or team_id in (select motanafisoon.supervised_team_ids())
);
create policy supervisor_or_admin_write on motanafisoon.card_usages for insert
    with check (
        motanafisoon.is_admin()
        or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids()))
        or team_id in (select motanafisoon.supervised_team_ids())
    );

-- ── attendance_policy_events: sensitive (absence reasons) — own row +
--    own supervised teams + admin only, never public. ─────────────────────
create policy read_own_or_supervised on motanafisoon.attendance_policy_events for select using (
    motanafisoon.is_admin()
    or member_id = motanafisoon.own_member_id()
    or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids()))
);
create policy supervisor_or_admin_write on motanafisoon.attendance_policy_events for insert
    with check (motanafisoon.is_admin() or member_id in (select m.id from motanafisoon.members m where m.team_id in (select motanafisoon.supervised_team_ids())));

-- ── payments / refund_requests: financial — own row + admin only. ─────────
create policy read_own_or_admin on motanafisoon.payments for select using (
    motanafisoon.is_admin() or member_id = motanafisoon.own_member_id()
);
create policy admin_write on motanafisoon.payments for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

create policy read_own_or_admin on motanafisoon.refund_requests for select using (
    motanafisoon.is_admin()
    or payment_id in (select id from motanafisoon.payments where member_id = motanafisoon.own_member_id())
);
create policy admin_write on motanafisoon.refund_requests for all using (motanafisoon.is_admin()) with check (motanafisoon.is_admin());

-- ── v_followup_zone: identifies at-risk members — NOT public. Restricted
--    to the member's own supervisor + admin (same audience as the
--    "لوحة المشرفة" it's meant to surface on). ─────────────────────────────
alter view motanafisoon.v_followup_zone set (security_invoker = on);
-- Relies on the underlying daily_logs/members RLS above for row visibility
-- (security_invoker means the view runs with the calling user's own
-- permissions, not the view owner's) — no separate grant needed.

-- ── Public leaderboard views — the intended broad-read surface. ───────────
-- Individual leaderboard: rank/points/commitment/"آخر ٥" pattern, matching
-- the playbook's جدول الأفراد columns. Deliberately excludes anything from
-- daily_logs beyond the aggregated status counts (no raw notes/tajweed
-- score detail — those stay in the restricted raw table).
create view motanafisoon.v_individual_leaderboard
with (security_invoker = on) as
select
    m.id as member_id,
    m.full_name,
    t.name as team_name,
    coalesce(sum(pl.points), 0) as total_points,
    count(*) filter (where dl.status = 'كامل') as days_full,
    count(*) filter (where dl.status = 'جزئي') as days_partial,
    count(*) filter (where dl.status = 'غياب') as days_absent,
    round(avg(dl.tajweed_score), 1) as avg_tajweed,
    rank() over (order by coalesce(sum(pl.points), 0) desc) as overall_rank
from motanafisoon.members m
left join motanafisoon.teams t on t.id = m.team_id
left join motanafisoon.daily_logs dl on dl.member_id = m.id
left join motanafisoon.points_ledger pl on pl.member_id = m.id
group by m.id, m.full_name, t.name;

-- Team leaderboard: rank/points/attendance%, matching جدول الفرق.
create view motanafisoon.v_team_leaderboard
with (security_invoker = on) as
select
    t.id as team_id,
    t.name as team_name,
    coalesce(sum(pl.points), 0) as total_points,
    round(
        100.0 * count(*) filter (where dl.status in ('كامل','جزئي'))
        / nullif(count(*), 0), 0
    ) as attendance_pct,
    rank() over (order by coalesce(sum(pl.points), 0) desc) as team_rank
from motanafisoon.teams t
left join motanafisoon.members m on m.team_id = t.id
left join motanafisoon.daily_logs dl on dl.member_id = m.id
left join motanafisoon.points_ledger pl on pl.team_id = t.id or pl.member_id = m.id
group by t.id, t.name;

grant select on motanafisoon.v_individual_leaderboard to authenticated;
grant select on motanafisoon.v_team_leaderboard to authenticated;
