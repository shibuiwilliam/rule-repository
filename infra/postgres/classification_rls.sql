-- Classification-Based Row-Level Security Policies
-- ==================================================
--
-- These policies restrict row visibility based on data classification
-- (PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED) and the user's clearance,
-- department membership, and capacity assignments.
--
-- These policies COEXIST with the tenant isolation RLS in rls_policies.sql.
-- Both layers must pass for a row to be visible.
--
-- PREREQUISITES:
--   1. Tables have a `classification` column (added in migration 029).
--   2. The application sets per-session variables via core/db_context.py:
--      - app.user_id          (authenticated user ID)
--      - app.user_clearance   (user's max clearance: public|internal|confidential|restricted)
--      - app.user_departments (comma-separated department IDs the user belongs to)
--   3. The `capacity_assignments` table exists (migration 028).
--   4. The `rule_ownerships` table exists (migration 028).
--
-- Safe defaults so queries don't fail when variables are not set.
ALTER DATABASE ruledb SET app.user_id = '';
ALTER DATABASE ruledb SET app.user_clearance = 'public';
ALTER DATABASE ruledb SET app.user_departments = '';

-- ---------------------------------------------------------------
-- Rules table — classification-based RLS
-- ---------------------------------------------------------------

-- Note: RLS is already enabled on `rules` by rls_policies.sql.
-- We add classification policies that coexist with tenant policies.

CREATE POLICY classification_rules_select ON rules
    FOR SELECT
    USING (
        -- PUBLIC and INTERNAL: visible to any authenticated user
        (classification IN ('public', 'internal')
         AND current_setting('app.user_id', true) <> '')
        OR
        -- CONFIDENTIAL: visible to department members or auditors
        (classification = 'confidential'
         AND current_setting('app.user_id', true) <> ''
         AND (
             EXISTS (
                 SELECT 1 FROM rule_ownerships ro
                 WHERE ro.rule_id = rules.id
                   AND ro.owner_department_id::text = ANY (
                       string_to_array(current_setting('app.user_departments', true), ',')
                   )
             )
             OR EXISTS (
                 SELECT 1 FROM rule_ownerships ro
                 JOIN capacity_assignments ca
                   ON ca.department_id = ro.owner_department_id
                 WHERE ro.rule_id = rules.id
                   AND ca.user_id = current_setting('app.user_id', true)
                   AND ca.capacity IN ('owner', 'auditor')
             )
         ))
        OR
        -- RESTRICTED: visible only to owner/auditor capacity holders
        (classification = 'restricted'
         AND current_setting('app.user_id', true) <> ''
         AND EXISTS (
             SELECT 1 FROM rule_ownerships ro
             JOIN capacity_assignments ca
               ON ca.department_id = ro.owner_department_id
             WHERE ro.rule_id = rules.id
               AND ca.user_id = current_setting('app.user_id', true)
               AND ca.capacity IN ('owner', 'auditor')
         ))
    );

-- ---------------------------------------------------------------
-- Evaluations table — classification-based RLS
-- ---------------------------------------------------------------

ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;

CREATE POLICY classification_evaluations_select ON evaluations
    FOR SELECT
    USING (
        -- PUBLIC and INTERNAL: visible to any authenticated user
        (classification IN ('public', 'internal')
         AND current_setting('app.user_id', true) <> '')
        OR
        -- CONFIDENTIAL: clearance check
        (classification = 'confidential'
         AND current_setting('app.user_clearance', true) IN ('confidential', 'restricted'))
        OR
        -- RESTRICTED: clearance check
        (classification = 'restricted'
         AND current_setting('app.user_clearance', true) = 'restricted')
    );

ALTER TABLE evaluations FORCE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------
-- Audit log table — classification-based RLS
-- ---------------------------------------------------------------

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY classification_audit_log_select ON audit_log
    FOR SELECT
    USING (
        -- PUBLIC and INTERNAL: visible to any authenticated user
        (classification IN ('public', 'internal')
         AND current_setting('app.user_id', true) <> '')
        OR
        -- CONFIDENTIAL: clearance check
        (classification = 'confidential'
         AND current_setting('app.user_clearance', true) IN ('confidential', 'restricted'))
        OR
        -- RESTRICTED: only restricted clearance
        (classification = 'restricted'
         AND current_setting('app.user_clearance', true) = 'restricted')
    );

ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;
