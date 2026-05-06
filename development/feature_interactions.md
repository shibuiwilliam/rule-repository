# Feature Interactions

> Documents intended behavior, current behavior, gaps, and remediation for cross-feature interaction pairs.
> Referenced by CLAUDE.md §15.1 (Tier 0). Each pair has a corresponding test in `tests/integration/feature_matrix/`.

---

## Interaction Pairs

### 1. Federation x Snapshot

**Question**: Does a snapshot freeze federation resolution?

**Intended behavior**: When a snapshot is created from a federation node, it should capture the effective rule set _as resolved at creation time_, including inherited and overridden rules from ancestors. Deploying that snapshot should use the frozen set, not re-resolve the live federation.

**Current behavior**: Snapshots and federation are **independent mechanisms**. `create_snapshot()` queries all active rules matching an optional scope filter — it does not accept a `federation_id` parameter or invoke `resolve_effective_rules()`. Federation resolution only happens at evaluation time when `federation_id` is passed to `rule_selector.select_rules()`. Snapshots deployed to an environment bypass federation entirely.

**Gap**: A snapshot cannot capture a federation-resolved rule set. If a user deploys a snapshot to production while also using federation, the two mechanisms may return different rule sets for the same context. There is no way to say "snapshot this federation's effective rules."

**Remediation**:
- Add optional `federation_id` parameter to `create_snapshot()`.
- When provided, resolve effective rules via `resolve_effective_rules()` and capture that set.
- Store `source_federation_id` in the snapshot metadata for traceability.
- In `rule_selector`, if both `environment` (snapshot) and `federation_id` are provided, prefer the snapshot (it's the frozen authority).

**Priority**: Tier 2 (after domain adapter refactor stabilizes the evaluation pipeline).

---

### 2. Snapshot x Marketplace

**Question**: Does a snapshot include subscribed package updates?

**Intended behavior**: Snapshots should capture the full rule set at creation time, including any rules imported from marketplace packages.

**Current behavior**: **Marketplace has been removed** (commit `8fc7e6c`). All marketplace models, services, routers, and schemas have been cleanly deleted. There are no package subscriptions, no rule packages, and no composition conflicts in the codebase.

**Gap**: N/A — marketplace does not exist. If marketplace is re-introduced in the future, the snapshot service should be updated to include package-sourced rules and record `source_package_id` in snapshot metadata.

**Remediation**: None required now. When marketplace is re-introduced, add a feature interaction test for this pair.

**Priority**: Deferred until marketplace re-introduction.

---

### 3. Proposal x Federation

**Question**: Who approves a child override of a parent rule?

**Intended behavior**: When a child federation node overrides a parent rule, the override should go through a proposal workflow. Parent federation owners should be notified or included as required approvers, since the override affects the governance of inherited rules.

**Current behavior**: Federation overrides are **immediate and ungoverned**. Calling `add_rule(federation_id, rule_id, override_parent_rule_id)` directly creates a `RuleFederationMembershipModel` with no proposal, no voting, and no notification to parent federation owners. The override takes effect on the next `resolve_effective_rules()` call.

Separately, the proposal service operates within a single `project_id` scope. When a proposal is enacted, it modifies rules in its project — it does not notify parent/child federations of the change, nor does it check whether the affected rule is inherited via federation.

**Gap**: Two gaps exist:
1. Federation overrides bypass governance entirely — no proposal, no approval, no audit trail beyond the membership record.
2. Proposal enactment is federation-unaware — retiring a parent rule via proposal does not propagate to child federations that inherit it.

**Remediation**:
- When `override_parent_rule_id` is set during `add_rule()`, auto-create a `Proposal(type=OVERRIDE)` requiring approval from the parent federation's owner.
- When a proposal retires a rule, query federation memberships to find child nodes that inherit it, and create notification records for affected federation owners.
- Add `federation_id` to the proposal model for cross-federation governance.

**Priority**: Tier 2 (requires both proposal and federation maturity).

---

### 4. Agent Governance x Federation

**Question**: Does personalization walk the federation chain?

**Intended behavior**: When delivering personalized rules to an agent, the system should resolve the agent's project's federation hierarchy first (inherited + overridden rules), then apply agent-specific personalization (suppressed rules, weights) on top of that resolved set.

**Current behavior**: `get_personalized_rules()` in `AgentGovernanceService` queries **all active rules globally** (`status IN ('EFFECTIVE', 'APPROVED')`), then applies the agent's `suppressed_rule_ids` and `personalized_rule_weights`. It does **not** accept a `federation_id` or `project_id` parameter, does not call `resolve_effective_rules()`, and does not filter by project scope.

**Gap**: Agent personalization ignores federation boundaries. An agent in project X receives rules from all projects, not just the rules inherited through X's federation chain. This means:
- Agents see rules they shouldn't (from unrelated federations).
- Override semantics are lost (a child override doesn't suppress the parent rule in the personalized set).

**Remediation**:
- Accept optional `federation_id` (or derive it from the agent's `project_id`) in `get_personalized_rules()`.
- Resolve effective rules via federation first, then apply personalization filters.
- The personalization layer should operate on the federation-resolved set, not the global corpus.

**Priority**: Tier 2.

---

### 5. Maturity x Snapshot

**Question**: Does an experimental rule keep shadow behavior in deployed snapshots?

**Intended behavior**: When a snapshot is created, it should freeze each rule's `maturity_level` at that point in time. If an experimental rule is later promoted to stable, the deployed snapshot should still treat it as experimental (shadow mode) until the snapshot is updated.

**Current behavior**: `serialize_rules()` in `snapshots/serializer.py` captures only 7 fields per rule: `statement`, `modality`, `severity`, `status`, `scope`, `tags`, and `rationale`. **`maturity_level` is NOT serialized.** When rules are deserialized from a snapshot, the maturity level is absent.

However, `rule_selector._rule_to_dict()` does include `maturity_level` (defaulting to `"proven"` if missing). This means:
- Snapshot-sourced rules lose their maturity level.
- The default of `"proven"` means experimental rules in a snapshot are treated as fully enforced — the opposite of shadow mode.

**Gap**: Critical. Experimental rules deployed via snapshot lose their shadow-mode protection. A rule that should produce `NEEDS_CONFIRMATION` in shadow mode will instead produce `DENY` when served from a snapshot, because the maturity level defaults to "proven."

**Remediation**:
- Add `maturity_level` to `serialize_rules()` output.
- Add `maturity_level` to `deserialize_snapshot()` parsing.
- Ensure `rule_selector._rule_to_dict()` preserves the snapshot's frozen maturity level instead of defaulting.
- Add a test verifying that experimental rules in snapshots retain shadow behavior.

**Priority**: Tier 1 (data integrity issue — can cause unexpected enforcement).

---

### 6. Marketplace x Maturity

**Question**: Are imported rules subject to local maturity lifecycle?

**Intended behavior**: Rules imported from marketplace packages should start at `experimental` maturity and progress through the local maturity lifecycle independently of their maturity in the source package.

**Current behavior**: **Marketplace has been removed** (commit `8fc7e6c`). No imported rules exist.

**Gap**: N/A. When marketplace is re-introduced, imported rules should:
- Always start at `experimental` regardless of source maturity.
- Progress through `experimental → stable → proven` based on local false-positive rates.
- Track both `source_maturity` (from package) and `local_maturity` (from local evaluation).

**Remediation**: None required now. Document this requirement for marketplace re-introduction.

**Priority**: Deferred until marketplace re-introduction.

---

### 7. Proposal x Snapshot

**Question**: What happens to live snapshots when a referenced rule is retired by proposal?

**Intended behavior**: Deployed snapshots should be immutable — a retired rule should continue to be enforced under the deployed snapshot until the snapshot is replaced. However, operators should be notified that a deployed snapshot contains retired rules so they can take action.

**Current behavior**: When `ProposalEnactor` retires a rule (sets `effective_period.valid_until`), it modifies the rule in Postgres. Deployed snapshots store a frozen copy of rule data in a JSONB column — they do **not** reference the live rule by foreign key. Therefore, the retired rule's data continues to exist in the snapshot and will be served during evaluation.

However, there is **no notification mechanism**. When a rule is retired via proposal, the system does not check whether any deployed snapshot contains that rule, and does not alert operators.

**Gap**: Partial. The immutability guarantee works correctly by accident (JSONB copy is independent of live rule state). But operators have no visibility into stale snapshots containing retired rules. Over time, deployed snapshots can diverge significantly from the live corpus with no warning.

**Remediation**:
- After proposal enactment retires a rule, query `RuleSetDeploymentModel` for active deployments.
- For each active deployment, check if the snapshot's `rule_snapshot` contains the retired rule ID.
- If found, create an alert (via the existing alerts system) notifying the operator that environment X's snapshot contains retired rule Y.
- The alert should suggest creating a new snapshot or rolling back.

**Priority**: Tier 2.

---

## Summary Table

| # | Pair | Status | Gap Severity | Priority |
|---|------|--------|-------------|----------|
| 1 | Federation x Snapshot | Undefined | Medium | Tier 2 |
| 2 | Snapshot x Marketplace | N/A (removed) | — | Deferred |
| 3 | Proposal x Federation | Undefined | High | Tier 2 |
| 4 | Agent Governance x Federation | Undefined | Medium | Tier 2 |
| 5 | Maturity x Snapshot | **Fixed** (Tier 1.0) | Resolved | Done |
| 6 | Marketplace x Maturity | N/A (removed) | — | Deferred |
| 7 | Proposal x Snapshot | Partial | Low | Tier 2 |

---

## Decisions Log

| Date | Pair | Decision | Rationale |
|------|------|----------|-----------|
| 2026-05-06 | #5 Maturity x Snapshot | Fix in Tier 1: serialize maturity_level in snapshots | Data integrity: experimental rules lose shadow protection |
| 2026-05-06 | #2, #6 Marketplace | Defer: marketplace removed | No code exists; document requirements for re-introduction |
| 2026-05-06 | #7 Proposal x Snapshot | Snapshots are immutable; add retirement alerts | Immutability is correct; visibility gap needs alerts |
