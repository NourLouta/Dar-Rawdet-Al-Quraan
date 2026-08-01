# Plan: Migrate Dar to Supabase + Build المتنافسون (role-based dashboards)

> **Progress status (last updated during Phase A3/B2 execution):**
> - ✅ A0 (env/scaffolding), A1 (dar schema DDL), A2 (backfill run + verified,
>   31/32 enrollments migrated — the 1 gap is a pre-existing production data
>   issue, an enrollment with no teacher assigned, not a migration bug), A3
>   (Supabase read-path implemented in `dar/supabase_io.py`, full 9-page
>   AppTest regression passes reading from Supabase).
> - ✅ B1 (motanafisoon schema DDL), B2 (seed data + RLS — full RLS test
>   matrix passes: member/supervisor/admin boundaries, supervisor team-cap
>   trigger, all verified with real JWTs against the live project, test data
>   cleaned up afterward).
> - ⏳ Not started: A4 (dual-write), A5 (production cutover — deliberately
>   not rushed), A6 (Dar per-staff auth), B3 (Next.js frontend), B4 (admin BI
>   dashboard), B5 (alerts wiring), B6 (deployment).
>
> This file is the original approved plan, unedited below this notice —
> treat the status block above as the current source of truth on progress.

## Context

Dar (`E:\Dar`) is a live Streamlit app the secretary team uses daily, currently backed by Google Sheets through a clean abstraction (`dar/sheets_io.py`). The user wants two things done together: (1) move Dar off Sheets onto Supabase/Postgres for real scalability and role-based access, and (2) build a brand-new system for "المتنافسون" — an 8-week gamified Quran-memorization team competition run by the same organization — with three role-based dashboards (member, supervisor, admin) as described in the attached playbook (`motanafisoonplaybookmobile.html`) and the user's own detailed spec.

Both must stay **completely free** and must not put the live Dar system at risk. Two research passes (full codebase architecture read + full playbook extraction) plus two confirmed product decisions ground everything below:
- **Daily logs are supervisor-entered only** (matches the playbook's own RACI table: member=C/consulted, supervisor=R/executor) — members are read-only in this system, which materially simplifies the member-side RLS/auth surface.
- **Members log in with phone + admin-provisioned PIN**, not email — no SMS/email dependency, works for a WhatsApp-first audience.

## Architecture decisions

- **One Supabase project, two Postgres schemas**: `dar` and `motanafisoon`. Clean permission boundaries, no name collisions, mirrors the real org boundary (two apps, one free bill).
- **Trust model differs by app:**
  - Dar (Streamlit) stays server-mediated — uses the Supabase **service_role key** server-side only, same trust posture as today's gspread service account. Authorization stays app-level in Python; RLS on `dar.*` is defense-in-depth (deny-all for anon/authenticated, only service_role touches it).
  - المتنافسون's Next.js frontend talks to Supabase directly from the browser with the **anon key** + a user's Auth JWT — **RLS on `motanafisoon.*` is the only real access-control layer** and must be correct before the frontend ships.
  - The admin BI dashboard (Streamlit) uses the service_role key like Dar does.
- **Two work tracks, sequenced independently:**
  - **Track A (Dar)** — cautious, gated, real production data at stake. The write cutover is the single most carefully gated step in this whole plan.
  - **Track B (المتنافسون)** — greenfield, zero live-data risk, starts in parallel as soon as the Supabase project exists.

---

## Track A — Migrate Dar to Supabase

### A0 — Environment & safety net (no prod risk)
- Create the Supabase project (free tier). Store URL/anon/service_role keys the same way `gcp_service_account` is stored today — never in the repo.
- Add a version-controlled `supabase/migrations/*.sql` folder for schema-as-code.
- On a branch: add `supabase-py` to `requirements.txt` (+ `psycopg2-binary` as a dev-only dependency for migration/verification scripts).
- Stand up a **staging** Streamlit deployment (second free Streamlit Cloud app, or local-only) to test against without touching production.
- *Exit:* empty Supabase project live, schema folder scaffolded, staging slot ready.

### A1 — Normalized `dar` schema (DDL only, zero data)
Real FKs replace every denormalized name/phone copy; a real `enrollment_schedule_days` table replaces the encoded `DAY_SCHEDULE` string; a real `lookup_lists` table replaces the single "لوكابس" sheet's ~20 crammed lists.

| Table | Purpose |
|---|---|
| `lookup_lists` | `(id, list_key, value_ar, sort_order, is_active)` — all ~20 dropdown lists (time_slots, levels, surahs, statuses, etc.), still admin-editable without a code change. |
| `branches`, `programs` | Direct equivalents of today's sheets. |
| `teachers` | 1:1 with `schema.Teacher` (20 fields), minus the computed `DISPLAY` column. |
| `parents` | `n_kids` becomes `COUNT(students)`, not stored. |
| `students` | FK to `parents`/`branches`; `PARENT_NAME`/`PARENT_PHONE` dropped (join instead); `AGE` derived from `birth_date`. |
| `enrollments` | FK to `students`/`teachers`/`programs`; name columns dropped. |
| `enrollment_schedule_days` | `(id, enrollment_id FK, weekday, session_time, duration_minutes)` — one row per weekday, replaces `WEEK_DAYS`/`SESS_TIME`/`SESS_MIN`/`DAY_SCHEDULE`. |
| `sessions` | FK to `enrollments`; `month` as a **generated column** (immutable `extract()`-based expression, not `to_char()` — see migration notes) so `state.months_available()` keeps working with minimal rewrites. |
| `parent_feedback`, `teacher_feedback` | Direct equivalents. |

Every `code` column gets a UNIQUE index (needed for `next_code()`/`update_row_by_code()`/`delete_row_by_code()` semantics); FK columns and `sessions.date` get btree indexes.

*Exit:* schema applied and verified in the SQL editor, zero data.

### A2 — One-time backfill + shadow verification (Sheets stays authoritative)
- Build `migrate_to_supabase.py` on the same pattern as the existing `migrate.py` (reuses `clean_phone`, `normalize_digits`, `to_date`, `month_key`; reads only via `sheets_io.read_ws()`, never gspread directly). Splits denormalized copies, parses `DAY_SCHEDULE` into `enrollment_schedule_days` rows, **upserts by `code`** — idempotent, safe to re-run.
- Build `verify_migration.py`: row counts, field-level spot checks, orphan-FK checks, diff report.
- Run daily against live Sheets data as a one-way shadow sync while Sheets remains sole source of truth.
- *Exit:* ≥1–2 weeks of daily verification runs, zero discrepancies.

### A3 — Read-path in `sheets_io.py` (staging only)
- Add a `"supabase"` read branch to `read_ws()`/`load_all()`, gated by a config toggle **independent of `write_target()`** so it can never accidentally affect writes.
- Deploy to staging with reads from Supabase; production untouched.
- Manually compare all 9 pages, prod vs. staging.
- *Exit:* staging matches prod across all 9 pages for ≥1 week.

### A4 — Write-path + dual-write mirroring (Sheets still primary in prod)
- Implement the `"supabase"` branch for `append_row`/`append_rows`/`update_row_by_code`/`delete_row_by_code`/`next_code`, preserving exact current signatures — **zero changes needed in `crud.py` or any of the 9 view files**, confirmed by the isolation audit.
- In production, Sheets stays primary; every successful write best-effort mirrors to Supabase (try/except, logged not raised — a Supabase hiccup must never block a real save).
- Extend verification to cover live production writes.
- *Exit:* ≥2 weeks of production dual-write, zero unresolved discrepancies.

### A5 — Production cutover (most-gated step in the whole plan)
- Pre-flight: verification shows 0 diffs; confirm DB size is trivial; take an explicit `pg_dump`/CSV backup immediately before flipping (Supabase free tier has no automatic backups).
- **Prerequisite: set up a keep-alive ping** (free GitHub Action hitting a trivial query every few days) — Supabase free projects auto-pause on inactivity, which would take a *live* app offline. This is the top practical risk in the whole migration, bigger than storage limits.
- Flip fallback-chain priority to `supabase → google → script → local → none` via one config toggle — trivially revertible.
- Keep dual-write active **in reverse** (Supabase→Sheets) for 3–7 days, so Sheets stays a warm backup — this is what makes rollback lossless.
- Brief the secretary team: nothing should look different; who to call if it does.
- *Exit:* 1–2 weeks stable, zero incidents → retire the reverse mirror.
- *Rollback:* revert the one priority-order toggle → Sheets instantly authoritative again, no data loss.

### A6 — Dar auth upgrade (decoupled, do anytime after A5)
- New `dar.staff_profiles` (`id uuid = auth.uid(), name, role CHECK IN ('admin','secretary','viewer'), phone, is_active`).
- Replace the single shared `admin/dar2026` password with real per-staff Supabase Auth logins; `st.session_state` holds identity + role.
- Add role gates on sensitive pages (الإعدادات, المالية) as the real control; RLS on `dar.*` stays deny-all-except-service_role as a backstop.
- *Exit:* every staff member has an individual login; shared password retired.

---

## Track B — Build المتنافسون (starts in parallel with A1)

### B1 — `motanafisoon` schema (DDL only)

| Table | Purpose |
|---|---|
| `seasons` | `(id, name, start_date, end_date, price_egp default 637, refund_policy_version, is_active)` |
| `teams` | `(id, season_id, name, color, logo_url, supervisor_id)` — no peer-leader field; supervisor is the only leadership FK, per the RACI table. |
| `supervisors` | `(id, name, phone, max_teams default 3)` — cap enforced via a CHECK/trigger on `teams.supervisor_id` assignment (RLS can't limit row *counts*). |
| `members` | `(id, season_id, team_id, full_name, phone, joined_at, status)` |
| `buddy_pairings` | `(id, member_id, partner_member_id, week_number)` UNIQUE(member_id, week_number) — history of the weekly-rotating رفيق. |
| `profiles` | `(id uuid = auth.uid(), role CHECK IN ('member','supervisor','admin'), member_id, supervisor_id, display_name)` — links a Supabase Auth identity to a domain entity + role; every RLS policy keys off this. |
| `daily_logs` | `(id, member_id, log_date, memorized, reviewed, recited_to_buddy, tajweed_score, status CHECK IN ('كامل','جزئي','غياب'), submitted_by uuid)` UNIQUE(member_id, log_date) — **supervisor-entered only**, per the confirmed decision. Source of the "✓/~/✗" + "آخر 5" streak columns. |
| `point_rules` | `(id, activity_type UNIQUE, points, unit CHECK IN ('per_day','per_week','flat','both_parties'), description, is_active)` — seeded with the 10 confirmed values below; config, not code. |
| `points_ledger` | `(id, member_id, team_id, activity_type FK, points, log_date, source_daily_log_id, week_number, is_doubled, awarded_by, dispute_status CHECK IN ('none','disputed','resolved'), dispute_deadline)` — **append-only**. No mutation of past rows; disputes and the week-6 ×2 event become new rows referencing the original. Totals are plain `SUM()` queries. Matches the playbook's explicit 48-hour dispute window. |
| `level_thresholds` | `(id, level_order UNIQUE, level_name, icon, min_points)` — 5 rows, 🌱→📖→⭐→🏆→👑. No thresholds exist in the source material; seed with a reasonable default curve (0 / 30 / 70 / 120 / 180 points, scaled off the season's expected point totals) as an **admin-tunable config table**, not a guess baked into code. |
| `badges` | `(id, code, name_ar, icon, description, is_ad_hoc)` — 🔥/⭐/💎 are computable from `daily_logs`/`points_ledger` streaks and can be rule-evaluated; 🧠 أقوى مراجعة and 🤝 أفضل رفيق are inherently qualitative/teacher-discretion, `is_ad_hoc=true`. |
| `member_badges` | `(id, member_id, badge_id, awarded_by, awarded_at, week_number)` |
| `cards` | `(id, code, scope CHECK IN ('member','team'), name_ar, icon, max_uses default 1)` — 🌿 استدراك, 🛟 إنقاذ (member), ⚔️ اختيار المنافس (team). |
| `card_usages` | `(id, card_id, member_id, team_id, used_at, week_number, notes)` — tracks single-use consumption. |
| `weekly_events` | `(id, season_id, week_number, event_type CHECK IN ('فلنرتقي','اختيار المنافس','جولة الحسم'), config jsonb, announced_at, is_locked default false)` — tier assignments (🥇1-4/🥈5-7/🥉8-10/🔴last) in `config`; `is_locked` enforces the playbook's "irrevocable once announced" rule for week 5. |
| `challenges` | `(id, season_id, week_number, team_a_id, team_b_id, winner_team_id, points_awarded, decided_at)` |
| `attendance_policy_events` | `(id, member_id, event_type CHECK IN ('reminder','supervisor_call','warning','exit','excuse_granted'), reason, event_date, recorded_by)` — implements the escalation table (day-1→buddy reminder, 2–3 days→supervisor call, >4/week or >3/month→exit unless عذر قهري freezes it). |
| `curriculum_days` | `(id, season_id, calendar_date, day_type CHECK IN ('memorize','rest','cumulative_review','exam'), surah, ayah_range, review_target)` UNIQUE(season_id, calendar_date) — the full Aug 7–Sep 25 2026 day-by-day calendar from the playbook. |
| `payments`, `refund_requests` | Built now, **UI deferred** — v1 tracking stays manual/WhatsApp as the user's original note implies; avoids a future schema migration if brought in-app later. |
| `v_followup_zone` (view) | Computed live from `daily_logs` — the <60%-for-2-days auto-flag. A plain view, not a cron job — trivial data volume makes on-read computation fine and avoids depending on scheduled-job behavior on the free tier. |

**Point rules to seed** (reconciled from the playbook's two point tables — confirmed as 10 distinct activities, not overlapping ranges): تسميع للرفيق=2/day, حفظ الورد=1/day, مراجعة=1/day, حضور الجلسة الأسبوعية=3/week, سماع التفسير=1/week, أسبوع بلا غياب=+4, فوز تحدٍّ (فريق)=+4, مساعدة زميل=+1, وسام=+2, إحضار صديق (referral, **both parties**)=+100.

*Exit:* schema applied, zero collision with `dar.*`.

### B2 — Seed data + Supabase Auth + RLS
- Seed `point_rules`, `curriculum_days`, one `seasons` row, default `level_thresholds`.
- **Auth implementation for phone+PIN** (Supabase has no native phone-without-SMS method): map each member to a synthetic email (`<phone>@motanafisoon.internal`) and use their PIN as the Supabase Auth password under the hood. Supervisor/admin provisions accounts server-side via the Supabase Admin API (`auth.admin.createUser`, service_role key only, never in the browser) during onboarding. The Next.js login screen just asks for phone + PIN and translates to the synthetic email client-side before calling `signInWithPassword`. Free, no SMS provider needed.
- RLS policies (this is the *only* access-control layer for the browser app, since daily logs are supervisor-only, member policies are simple):
  - **member**: `SELECT` own `daily_logs`/`points_ledger` rows + own team's public leaderboard fields. **No write access at all** — matches the confirmed supervisor-only entry decision.
  - **supervisor**: `SELECT`/`INSERT`/`UPDATE` on `daily_logs`/`points_ledger` scoped to `member_id IN (members of teams they supervise)`, via a policy joining `profiles → supervisors → teams → members`.
  - **admin**: full access via a `role = 'admin'` bypass in each policy.
- *Exit:* a written RLS test matrix passes with real JWTs — member blocked from other teams' data and from any write; supervisor blocked from an unassigned team — verified before frontend work starts.

### B3 — Next.js frontend (member + supervisor dashboards)
- New Next.js app in a **separate repo** (different hosting platform than Dar; keeps deploy/CI simple). Reuses the playbook's teal (#1e5c59/#287f79) + gold (#c39b3c/#e1bf65) CSS custom properties, RTL layout, light/dark mode — it's already fully themed in the HTML you attached.
- **Member dashboard (read-only):** points/streak, team + individual leaderboard position ("12 points to catch #17"), progress bar toward next level, badges/cards inventory, "آخر 5" history, current week's curriculum.
- **Supervisor dashboard:** daily entry grid for assigned team(s) (≤3), the follow-up queue (from `v_followup_zone`), point-award actions (writes `points_ledger`, referencing `source_daily_log_id`), weekly-event results posting, card-usage recording.
- Auth pages + role-based route guarding from `profiles`.
- *Exit:* both dashboards functional against seeded data, deployed to a Vercel/Cloudflare preview, signed off.

### B4 — Admin BI dashboard (Streamlit)
- Separate Streamlit app/repo path, own free Streamlit Cloud slot, service_role key, reusing Dar's theme/PDF-export patterns.
- KPIs: participation rate, cohort completion, team standings, points distribution, attendance heatmaps, org-wide follow-up queue; actions: exam approval, results announcement, point-rule tuning (writes to `point_rules`/`level_thresholds` so tuning never needs a redeploy).
- *Exit:* admin can view org-wide KPIs and perform approvals.

### B5 — Alerts
- Wire `v_followup_zone` into both the supervisor dashboard (own teams) and admin dashboard (org-wide) — the one explicit real-time behavior spec in the playbook (<60% commitment for 2 consecutive days → auto-flag).
- *Exit:* a simulated test member with <60% for 2 consecutive days correctly flags in both dashboards.

### B6 — Deployment
- Next.js → Vercel or Cloudflare Pages; anon key only in frontend env vars, service_role key never shipped client-side.
- Streamlit admin app → Streamlit Community Cloud, same secrets pattern as Dar.

---

## Free-tier watch list

- **Supabase auto-pause on inactivity** is the real risk for a live app (not storage) — mitigated by the A5 keep-alive ping; this is also the most likely eventual reason to go paid, well before storage ever matters.
- **500MB DB cap**: comfortably sized for years at this scale (Dar: ~32 students/12 teachers/55 enrollments; المتنافسون: 40–80 members) — mostly short text rows.
- **Streamlit Community Cloud**: apps cold-start after inactivity (no data loss); need to confirm the account's current limit on simultaneously-hosted free apps, since this plan needs slots for both Dar and the المتنافسون admin app.
- **Vercel/Cloudflare Pages bandwidth**: irrelevant at 40–80 users on either provider.

## Verification

- Track A: `verify_migration.py` diff reports at each phase gate (A2/A3/A4/A5); manual 9-page prod-vs-staging comparison at A3; the A5 backup + reverse-mirror overlap is itself the rollback test.
- Track B: RLS test matrix with real JWTs per role before B3 starts; end-to-end manual walkthrough of both dashboards against seeded data before B6; simulated follow-up-zone trigger test at B5.

## Sequencing note

Track B can start immediately (B1 right after A0, since it's a separate schema with no live-data risk). Track A's pace is deliberately conservative — A5 (the actual cutover) should not be rushed to match Track B's timeline; it's fine for المتنافسون to ship well before Dar's write-path ever moves off Sheets.

---

## Migration notes discovered during execution

Real bugs found and fixed while actually applying the plan (kept here so they're not re-discovered):

1. **`to_char()` is not immutable in Postgres** — can't be used in a generated column expression. `sessions.month` uses an `extract()`-based expression instead (`lpad(extract(year...)::text,4,'0') || '-' || lpad(extract(month...)::text,2,'0')`).
2. **Custom Postgres schemas don't inherit any role grants** — Supabase's "Exposed schemas"/"Exposed tables" Data API settings only control what PostgREST will serve, not the underlying `GRANT` privileges. Even `service_role` got `permission denied for schema` until explicit `GRANT USAGE ON SCHEMA ... TO service_role` (+ table/sequence grants + `ALTER DEFAULT PRIVILEGES` for future tables) were added — see `supabase/migrations/0006_grants.sql`.
3. **`numpy.int64`/`float64` aren't JSON-serializable** — `pd.to_numeric()` results must be converted to native Python types before building rows for `supabase-py`'s `.upsert()`.
4. **Windows console defaults to cp1252** — scripts that print Arabic text or Unicode symbols (→, ✓, etc.) crash with `UnicodeEncodeError` unless `sys.stdout.reconfigure(encoding="utf-8")` is called at the top.
