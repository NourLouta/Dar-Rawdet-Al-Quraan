-- Postgres GRANTs for the two custom schemas — Phase A1/B1 follow-up.
-- Supabase's "Exposed schemas"/"Exposed tables" Data API settings only
-- control what PostgREST is willing to serve; they do NOT issue the
-- underlying Postgres GRANT statements. Custom schemas (unlike the
-- built-in public/storage/auth) don't inherit any role privileges
-- automatically, so every role that needs to reach these tables — even
-- service_role, which bypasses RLS but still needs USAGE/SELECT grants —
-- must be granted explicitly. ALTER DEFAULT PRIVILEGES covers tables
-- created after this migration too (e.g. Phase A6's dar.staff_profiles).

-- dar: service_role only (server-mediated trust model — see 0002_dar_rls.sql).
grant usage on schema dar to service_role;
grant all on all tables in schema dar to service_role;
grant all on all sequences in schema dar to service_role;
alter default privileges in schema dar grant all on tables to service_role;
alter default privileges in schema dar grant all on sequences to service_role;

-- motanafisoon: authenticated (RLS-scoped per role) + service_role (admin/bulk, bypasses RLS).
grant usage on schema motanafisoon to authenticated, service_role;
grant select, insert, update, delete on all tables in schema motanafisoon to authenticated, service_role;
grant usage on all sequences in schema motanafisoon to authenticated, service_role;
alter default privileges in schema motanafisoon grant select, insert, update, delete on tables to authenticated, service_role;
alter default privileges in schema motanafisoon grant usage on sequences to authenticated, service_role;
