-- Row-Level Security (RLS) Policies for Multi-Tenant Isolation
-- =============================================================
--
-- These policies ensure each tenant can only access their own data,
-- even if application-level checks are bypassed.
--
-- PREREQUISITES:
--   1. The `rules` table has a `tenant_id` column (added in migration 024).
--   2. The application sets `rulerepo.current_tenant_id` per session.
--   3. The application connects with a non-superuser role (e.g., `rule`).
--
-- STATUS: ACTIVE for rules table. Other tables will be enabled as
-- their tenant_id columns are added.
-- =============================================================

-- Safe default so queries don't fail when no tenant is set
ALTER DATABASE ruledb SET rulerepo.current_tenant_id = '00000000-0000-0000-0000-000000000000';

-- ---------------------------------------------------------------
-- Rules table — RLS active
-- ---------------------------------------------------------------

ALTER TABLE rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_rules_select ON rules
    FOR SELECT
    USING (tenant_id::text = current_setting('rulerepo.current_tenant_id', true));

CREATE POLICY tenant_isolation_rules_insert ON rules
    FOR INSERT
    WITH CHECK (tenant_id::text = current_setting('rulerepo.current_tenant_id', true));

CREATE POLICY tenant_isolation_rules_update ON rules
    FOR UPDATE
    USING (tenant_id::text = current_setting('rulerepo.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('rulerepo.current_tenant_id', true));

CREATE POLICY tenant_isolation_rules_delete ON rules
    FOR DELETE
    USING (tenant_id::text = current_setting('rulerepo.current_tenant_id', true));

ALTER TABLE rules FORCE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------
-- Pattern for additional tables (apply as tenant_id columns are added):
--
--   ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
--   CREATE POLICY tenant_isolation_<table>_select ON <table>
--       FOR SELECT
--       USING (tenant_id::text = current_setting('rulerepo.current_tenant_id', true));
--   CREATE POLICY tenant_isolation_<table>_insert ON <table>
--       FOR INSERT
--       WITH CHECK (tenant_id::text = current_setting('rulerepo.current_tenant_id', true));
--   ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
-- ---------------------------------------------------------------
