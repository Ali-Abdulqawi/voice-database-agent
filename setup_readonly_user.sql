-- Creates a read-only database user for "Talk or Type to your Database".
-- Run this once in Supabase: SQL Editor -> New query -> paste -> Run.
-- Replace CHANGE_ME with your own strong password (letters and numbers only).

-- 1. Create the user
CREATE ROLE app_readonly WITH LOGIN PASSWORD 'CHANGE_ME';

-- 2. Let it see the tables in the public schema
GRANT USAGE ON SCHEMA public TO app_readonly;

-- 3. Allow reading only (no insert, update or delete)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

-- 4. Give it read access to tables created later too
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_readonly;

-- 5. Extra safety: every session is read-only and queries stop after 10 seconds
ALTER ROLE app_readonly SET default_transaction_read_only = on;
ALTER ROLE app_readonly SET statement_timeout = '10s';

-- Note: if Row Level Security (RLS) is enabled on a table, add a SELECT policy
-- for app_readonly, or the app will see no rows from that table.
