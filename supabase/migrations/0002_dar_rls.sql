-- Dar RLS — defense-in-depth only (Phase A1/A4).
-- Dar's Streamlit app is server-mediated and uses the service_role key,
-- which bypasses RLS entirely — authorization stays app-level in Python,
-- same trust model as today's gspread service account. These policies exist
-- so that if the anon/authenticated keys ever leaked or were used by mistake,
-- nothing in dar.* is readable/writable from outside the server.

alter table dar.lookup_lists enable row level security;
alter table dar.branches enable row level security;
alter table dar.programs enable row level security;
alter table dar.teachers enable row level security;
alter table dar.parents enable row level security;
alter table dar.students enable row level security;
alter table dar.enrollments enable row level security;
alter table dar.enrollment_schedule_days enable row level security;
alter table dar.sessions enable row level security;
alter table dar.parent_feedback enable row level security;
alter table dar.teacher_feedback enable row level security;

-- No policies are created for anon/authenticated on any dar.* table —
-- RLS enabled with zero policies means those roles get zero rows,
-- for both reads and writes. Only service_role (which bypasses RLS by
-- design in Postgres/Supabase) can touch these tables.
