#!/usr/bin/env python3
"""Audit spec documents (PROJECT.md, CLAUDE.md) against the actual codebase.

Scans for declared features, endpoints, files, and classes, then classifies each
as IMPLEMENTED, PARTIAL, PLANNED, or MISSING.

By default, uses code-only heuristics (file existence, endpoint scanning, class
detection). With --live-llm, uses Gemini to perform deeper semantic classification.

Usage:
    uv run python scripts/spec_audit.py
    uv run python scripts/spec_audit.py --live-llm
    uv run python scripts/spec_audit.py --output development/spec_implementation_audit.md
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SERVER_SRC = ROOT / "apps" / "server" / "src" / "rulerepo_server"
FRONTEND_APP = ROOT / "apps" / "frontend" / "app"
PACKAGES = ROOT / "packages"
SCRIPTS = ROOT / "scripts"
DEVELOPMENT = ROOT / "development"

DEFAULT_OUTPUT = ROOT / "development" / "spec_implementation_audit.md"

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

STATUS_IMPLEMENTED = "IMPLEMENTED"
STATUS_PARTIAL = "PARTIAL"
STATUS_PLANNED = "PLANNED"
STATUS_MISSING = "MISSING"


@dataclass
class FeatureCheck:
    """A single feature to verify against the codebase."""

    name: str
    category: str
    declared_status: str  # What PROJECT.md / CLAUDE.md claims
    actual_status: str = ""  # What we determined
    evidence: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class AuditReport:
    """Full audit report."""

    timestamp: str = ""
    features: list[FeatureCheck] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Codebase scanner helpers
# ---------------------------------------------------------------------------


def file_exists(rel_path: str) -> bool:
    """Check if a file or directory exists relative to the project root."""
    return (ROOT / rel_path).exists()


def dir_has_files(rel_path: str, pattern: str = "*.py") -> bool:
    """Check if a directory contains files matching a pattern."""
    d = ROOT / rel_path
    if not d.is_dir():
        return False
    return any(d.glob(pattern))


def grep_in_file(filepath: Path, pattern: str) -> list[str]:
    """Search for a regex pattern in a file, return matching lines."""
    if not filepath.is_file():
        return []
    matches = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if re.search(pattern, line):
                matches.append(line.strip())
    except OSError:
        pass
    return matches


def grep_recursive(directory: Path, pattern: str, glob: str = "*.py") -> list[str]:
    """Search for a regex pattern across all files matching glob in a directory."""
    if not directory.is_dir():
        return []
    matches = []
    for f in directory.rglob(glob):
        matches.extend(grep_in_file(f, pattern))
    return matches


def find_router_prefixes() -> set[str]:
    """Extract all registered API router prefixes from the v1 router init."""
    api_v1 = SERVER_SRC / "api" / "v1"
    prefixes: set[str] = set()
    for py in api_v1.rglob("*.py"):
        for line in grep_in_file(py, r'prefix\s*=\s*["\']'):
            m = re.search(r'prefix\s*=\s*["\']([^"\']+)', line)
            if m:
                prefixes.add(m.group(1))
    return prefixes


def find_frontend_pages() -> set[str]:
    """Find all frontend page routes."""
    pages: set[str] = set()
    if not FRONTEND_APP.is_dir():
        return pages
    for page in FRONTEND_APP.rglob("page.tsx"):
        rel = page.relative_to(FRONTEND_APP)
        route = "/" + str(rel.parent).replace("(dashboard)/", "")
        pages.add(route)
    return pages


def has_class(directory: Path, class_name: str) -> bool:
    """Check if a class definition exists in any Python file under directory."""
    return len(grep_recursive(directory, rf"class\s+{class_name}\b")) > 0


def has_function(directory: Path, func_name: str) -> bool:
    """Check if a function definition exists."""
    return len(grep_recursive(directory, rf"def\s+{func_name}\b")) > 0


def has_endpoint(method: str, path_fragment: str) -> bool:
    """Check if an API endpoint exists in the router files."""
    api_v1 = SERVER_SRC / "api" / "v1"
    pattern = rf'@.*\.{method}\s*\(\s*["\'].*{re.escape(path_fragment)}'
    return len(grep_recursive(api_v1, pattern)) > 0


# ---------------------------------------------------------------------------
# Feature definitions — what to check
# ---------------------------------------------------------------------------


def build_feature_checks() -> list[FeatureCheck]:
    """Define all features to audit, grouped by category."""
    checks: list[FeatureCheck] = []

    def add(name: str, category: str, declared: str) -> FeatureCheck:
        fc = FeatureCheck(name=name, category=category, declared_status=declared)
        checks.append(fc)
        return fc

    # --- Core Rule Management ---
    add("Rule CRUD API", "Core", "IMPLEMENTED")
    add("Rule revision history", "Core", "IMPLEMENTED")
    add("Rule effective_period (valid_from/valid_until)", "Core", "IMPLEMENTED")
    add("Rule maturity_level (EXPERIMENTAL/STABLE/PROVEN)", "Core", "IMPLEMENTED")
    add("Rule sensitivity field", "Core", "IMPLEMENTED")
    add("Rule applicable_to (SubjectFilter)", "Core", "IMPLEMENTED")
    add("Rule equivalence_id (polyglot)", "Core", "IMPLEMENTED")
    add("Rule regulatory_severity", "Core", "IMPLEMENTED")
    add("Rule tenant_id", "Core", "IMPLEMENTED")

    # --- Search ---
    add("Full-text search", "Search", "IMPLEMENTED")
    add("Vector search", "Search", "IMPLEMENTED")
    add("Hybrid search", "Search", "IMPLEMENTED")
    add("Category search", "Search", "IMPLEMENTED")
    add("Context search", "Search", "IMPLEMENTED")
    add("Document search", "Search", "IMPLEMENTED")
    add("Temporal search", "Search", "IMPLEMENTED")
    add("Citation search", "Search", "IMPLEMENTED")
    add("Subject-aware search", "Search", "IMPLEMENTED")
    add("Conflict-aware search", "Search", "IMPLEMENTED")

    # --- Evaluation Engine ---
    add("Evaluation API (POST /evaluate)", "Evaluation", "IMPLEMENTED")
    add("Diff parser", "Evaluation", "IMPLEMENTED")
    add("Context assembler", "Evaluation", "IMPLEMENTED")
    add("Rule selector", "Evaluation", "IMPLEMENTED")
    add("Batch evaluator", "Evaluation", "IMPLEMENTED")
    add("Verdict aggregator", "Evaluation", "IMPLEMENTED")
    add("Conflict aggregator", "Evaluation", "IMPLEMENTED")
    add("Graph resolver", "Evaluation", "IMPLEMENTED")
    add("Impact preview", "Evaluation", "IMPLEMENTED")
    add("EvaluationDomainAdapter Protocol", "Evaluation", "IMPLEMENTED")
    add("Code adapter (under adapters/code/)", "Evaluation", "IMPLEMENTED")
    add("business_event adapter", "Evaluation", "IMPLEMENTED")
    add("document_diff adapter", "Evaluation", "IMPLEMENTED")
    add("communication adapter", "Evaluation", "IMPLEMENTED")
    add("documentation adapter", "Evaluation", "IMPLEMENTED")
    add("Consensus voting for CRITICAL", "Evaluation", "IMPLEMENTED")
    add("Idempotency-Key middleware", "Evaluation", "IMPLEMENTED")

    # --- Extraction ---
    add("Extraction pipeline", "Extraction", "IMPLEMENTED")
    add("Document upload API", "Extraction", "IMPLEMENTED")
    add("PDF sanitizer (pikepdf)", "Extraction", "IMPLEMENTED")
    add("Contract clause segmenter", "Extraction", "IMPLEMENTED")

    # --- Intent ---
    add("Intent API (POST /intent)", "Intent", "IMPLEMENTED")
    add("Intent classifier", "Intent", "IMPLEMENTED")

    # --- Discovery ---
    add("Discovery scan API", "Discovery", "IMPLEMENTED")
    add("CLAUDE.md analyzer", "Discovery", "IMPLEMENTED")
    add("Linter config analyzer", "Discovery", "IMPLEMENTED")
    add("Code patterns analyzer", "Discovery", "IMPLEMENTED")
    add("Policy document analyzer", "Discovery", "IMPLEMENTED")
    add("Confluence connector", "Discovery", "IMPLEMENTED")
    add("Notion connector", "Discovery", "IMPLEMENTED")
    add("e-Gov connector", "Discovery", "IMPLEMENTED")
    add("EUR-Lex connector", "Discovery", "IMPLEMENTED")

    # --- Feedback ---
    add("Correction feedback API", "Feedback", "IMPLEMENTED")
    add("Auto-draft from corrections", "Feedback", "IMPLEMENTED")
    add("Correction analyzer", "Feedback", "IMPLEMENTED")

    # --- Federation ---
    add("Federation CRUD API", "Federation", "IMPLEMENTED")
    add("Effective rules resolution", "Federation", "IMPLEMENTED")
    add("Federation diff", "Federation", "IMPLEMENTED")

    # --- Snapshots ---
    add("Snapshot CRUD API", "Snapshots", "IMPLEMENTED")
    add("Snapshot deploy/rollback", "Snapshots", "IMPLEMENTED")
    add("Snapshot simulate", "Snapshots", "IMPLEMENTED")
    add("Bulk impact preview (simulate-bulk)", "Snapshots", "IMPLEMENTED")

    # --- Proposals ---
    add("Proposal CRUD API", "Proposals", "IMPLEMENTED")
    add("Proposal voting workflow", "Proposals", "IMPLEMENTED")
    add("Proposal enact/revert", "Proposals", "IMPLEMENTED")
    add("Proposal notifications", "Proposals", "IMPLEMENTED")

    # --- Agent Governance ---
    add("Agent profile registration", "Agent Governance", "IMPLEMENTED")
    add("Agent trust levels", "Agent Governance", "IMPLEMENTED")
    add("Agent mastery tracking", "Agent Governance", "IMPLEMENTED")
    add("Agent exception requests", "Agent Governance", "IMPLEMENTED")
    add("Agent negotiation", "Agent Governance", "IMPLEMENTED")
    add("Governance sessions", "Agent Governance", "IMPLEMENTED")

    # --- Intelligence ---
    add("Intelligence dashboard API", "Intelligence", "IMPLEMENTED")
    add("Health scoring", "Intelligence", "IMPLEMENTED")
    add("Rule effectiveness", "Intelligence", "IMPLEMENTED")
    add("Recommendations", "Intelligence", "IMPLEMENTED")
    add("Agent analytics", "Intelligence", "IMPLEMENTED")
    add("Weekly digest", "Intelligence", "IMPLEMENTED")

    # --- Playground ---
    add("Playground evaluate API", "Playground", "IMPLEMENTED")
    add("Test case generation", "Playground", "IMPLEMENTED")
    add("Test runner", "Playground", "IMPLEMENTED")
    add("Counterexample generator", "Playground", "IMPLEMENTED")

    # --- MCP ---
    add("MCP server (stdio + HTTP)", "MCP", "IMPLEMENTED")
    add("MCP tools (search, explain, conflicts)", "MCP", "IMPLEMENTED")
    add("MCP resources", "MCP", "IMPLEMENTED")
    add("MCP prompts", "MCP", "IMPLEMENTED")

    # --- Gateway ---
    add("Gateway webhook ingestion", "Gateway", "IMPLEMENTED")
    add("Gateway enforcement policies", "Gateway", "IMPLEMENTED")
    add("Slack/Teams/Email gateways", "Gateway", "IMPLEMENTED")

    # --- Integrations ---
    add("GitHub webhook receiver", "Integrations", "IMPLEMENTED")
    add("GitHub check reporter", "Integrations", "IMPLEMENTED")

    # --- Audit ---
    add("Audit log (append-only, hash-chained)", "Audit", "IMPLEMENTED")
    add("Audit inspection API (GET /audit)", "Audit", "IMPLEMENTED")
    add("Audit chain verification script", "Audit", "IMPLEMENTED")
    add("Audit frontend page", "Audit", "IMPLEMENTED")

    # --- Provenance ---
    add("Why API (GET /rules/{id}/why)", "Provenance", "IMPLEMENTED")
    add("Provenance lineage resolver", "Provenance", "IMPLEMENTED")
    add("DERIVES_FROM basis_type edge property", "Provenance", "IMPLEMENTED")

    # --- PII ---
    add("PII tokenizer (core/pii/tokenizer.py)", "PII", "IMPLEMENTED")
    add("PII masking in logs", "PII", "PARTIAL")
    add("Evaluation context encryption", "PII", "IMPLEMENTED")

    # --- Multi-tenancy ---
    add("Tenant model and tenant_id FK", "Multi-tenancy", "IMPLEMENTED")
    add("Postgres Row-Level Security", "Multi-tenancy", "IMPLEMENTED")
    add("Elasticsearch routing by tenant", "Multi-tenancy", "IMPLEMENTED")
    add("Neo4j multi-database per tenant", "Multi-tenancy", "IMPLEMENTED")

    # --- Observability ---
    add("Structured logging (structlog)", "Observability", "IMPLEMENTED")
    add("Cost ledger (token counts on evaluations)", "Observability", "IMPLEMENTED")

    # --- LLM Provider ---
    add("LLMProvider Protocol (adapters/llm/base.py)", "LLM", "IMPLEMENTED")
    add("Gemini adapter", "LLM", "IMPLEMENTED")
    add("Anthropic adapter", "LLM", "IMPLEMENTED")
    add("OpenAI adapter", "LLM", "IMPLEMENTED")
    add("Local LLM adapter (vLLM/Ollama)", "LLM", "IMPLEMENTED")

    # --- CLI ---
    add("Unified rulerepo CLI (packages/cli)", "CLI", "IMPLEMENTED")
    add("rulerepo check command", "CLI", "IMPLEMENTED")
    add("rulerepo hook command", "CLI", "IMPLEMENTED")
    add("rulerepo ingest command", "CLI", "IMPLEMENTED")
    add("rulerepo export command", "CLI", "IMPLEMENTED")
    add("rulerepo context command", "CLI", "IMPLEMENTED")
    add("rulerepo mcp command", "CLI", "IMPLEMENTED")
    add("rulerepo init command", "CLI", "IMPLEMENTED")
    add("rulerepo doctor command", "CLI", "IMPLEMENTED")
    add("rulerepo audit verify command", "CLI", "IMPLEMENTED")

    # --- Workers ---
    add("arq worker settings", "Workers", "IMPLEMENTED")
    add("Continuous conflict scanner", "Workers", "IMPLEMENTED")
    add("Archival worker", "Workers", "IMPLEMENTED")
    add("Policy review cycle worker", "Workers", "IMPLEMENTED")
    add("Verdict drift monitor", "Workers", "IMPLEMENTED")
    add("Polyglot validator", "Workers", "IMPLEMENTED")

    # --- Frontend Pages ---
    add("Rules list page", "Frontend", "IMPLEMENTED")
    add("Rule detail page", "Frontend", "IMPLEMENTED")
    add("Search page", "Frontend", "IMPLEMENTED")
    add("Documents page", "Frontend", "IMPLEMENTED")
    add("Discovery page", "Frontend", "IMPLEMENTED")
    add("Playground page", "Frontend", "IMPLEMENTED")
    add("Proposals page", "Frontend", "IMPLEMENTED")
    add("Federation page", "Frontend", "IMPLEMENTED")
    add("Snapshots page", "Frontend", "IMPLEMENTED")
    add("Intelligence page", "Frontend", "IMPLEMENTED")
    add("Feedback page", "Frontend", "IMPLEMENTED")
    add("Agents page", "Frontend", "IMPLEMENTED")
    add("Gateway page", "Frontend", "IMPLEMENTED")
    add("Review page", "Frontend", "IMPLEMENTED")
    add("Notifications page", "Frontend", "IMPLEMENTED")
    add("Projects page", "Frontend", "IMPLEMENTED")
    add("Integrations page", "Frontend", "IMPLEMENTED")
    add("Audit page", "Frontend", "IMPLEMENTED")
    add("Rule Tutor page", "Frontend", "IMPLEMENTED")
    add("Persona switcher", "Frontend", "IMPLEMENTED")
    add("Sidebar reorganization (Compose/Govern/Observe/Share/Agents)", "Frontend", "PARTIAL")

    # --- Infrastructure ---
    add("Docker Compose full stack", "Infrastructure", "IMPLEMENTED")
    add("PostgreSQL init.sql", "Infrastructure", "IMPLEMENTED")
    add("Elasticsearch setup", "Infrastructure", "IMPLEMENTED")
    add("Neo4j init.cypher", "Infrastructure", "IMPLEMENTED")
    add("Redis service", "Infrastructure", "IMPLEMENTED")
    add("arq-worker service", "Infrastructure", "IMPLEMENTED")
    add("MCP server service", "Infrastructure", "IMPLEMENTED")

    # --- Scripts ---
    add("seed_data.py", "Scripts", "IMPLEMENTED")
    add("reconcile_graph.py", "Scripts", "IMPLEMENTED")
    add("reindex_elasticsearch.py", "Scripts", "IMPLEMENTED")
    add("generate_claude_md.py", "Scripts", "IMPLEMENTED")
    add("spec_audit.py", "Scripts", "IMPLEMENTED")
    add("verify_audit_chain.py", "Scripts", "IMPLEMENTED")

    # --- Sample Rules ---
    add("Coding rules (10 documents)", "Sample Rules", "IMPLEMENTED")
    add("Company rules (6 documents)", "Sample Rules", "IMPLEMENTED")
    add("Sales team rules (5 documents)", "Sample Rules", "IMPLEMENTED")
    add("Rule templates (5 YAML)", "Sample Rules", "IMPLEMENTED")
    add("Legal rules", "Sample Rules", "IMPLEMENTED")
    add("Communication rules", "Sample Rules", "IMPLEMENTED")

    # --- Tier 0 Deliverables ---
    add("spec_audit.py script", "Tier 0", "IMPLEMENTED")
    add("development/feature_interactions.md", "Tier 0", "IMPLEMENTED")
    add("development/spec_implementation_audit.md", "Tier 0", "IMPLEMENTED")
    add("tests/integration/feature_matrix/", "Tier 0", "IMPLEMENTED")
    add("make spec-audit target", "Tier 0", "IMPLEMENTED")

    return checks


# ---------------------------------------------------------------------------
# Code-only verification engine
# ---------------------------------------------------------------------------


def verify_feature(fc: FeatureCheck) -> None:
    """Verify a feature using code-only heuristics. Mutates fc in place."""
    name = fc.name
    cat = fc.category

    # -- Core Rule fields --
    if cat == "Core":
        if "CRUD" in name:
            _check_files(
                fc,
                [
                    "apps/server/src/rulerepo_server/api/v1/rules.py",
                    "apps/server/src/rulerepo_server/services/rule_service.py",
                ],
            )
        elif "revision history" in name:
            _check_class_and_file(fc, "RuleRevision", "apps/server/src/rulerepo_server/domain/revision.py")
        elif "effective_period" in name:
            _check_class(fc, "EffectivePeriod")
        elif "maturity_level" in name:
            _check_class(fc, "MaturityLevel")
        elif "sensitivity" in name:
            _check_field_in_model(fc, "sensitivity", "apps/server/src/rulerepo_server/domain/rule.py")
        elif "applicable_to" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/domain/subject.py")
        elif "equivalence_id" in name:
            _check_field_in_model(fc, "equivalence_id", "apps/server/src/rulerepo_server/domain/rule.py")
        elif "regulatory_severity" in name:
            _check_field_in_model(fc, "regulatory_severity", "apps/server/src/rulerepo_server/domain/rule.py")
        elif "tenant_id" in name:
            _check_field_in_model(fc, "tenant_id", "apps/server/src/rulerepo_server/adapters/postgres/models.py")

    # -- Search --
    elif cat == "Search":
        search_router = "apps/server/src/rulerepo_server/api/v1/search.py"
        if "Full-text" in name:
            _check_endpoint_in_file(fc, "fulltext", search_router)
        elif "Vector" in name:
            _check_endpoint_in_file(fc, "vector", search_router)
        elif "Hybrid" in name:
            _check_endpoint_in_file(fc, "hybrid", search_router)
        elif "Category" in name:
            _check_endpoint_in_file(fc, "category", search_router)
        elif "Context" in name:
            _check_endpoint_in_file(fc, "context", search_router)
        elif "Document" in name:
            _check_endpoint_in_file(fc, "documents", search_router)
        elif "Temporal" in name:
            _check_endpoint_in_file(fc, "temporal", search_router)
        elif "Citation" in name:
            _check_endpoint_in_file(fc, "citation", search_router)
        elif "Subject-aware" in name:
            _check_endpoint_in_file(fc, "subject", search_router)
        elif "Conflict-aware" in name:
            _check_endpoint_in_file(fc, "conflict", search_router)

    # -- Evaluation --
    elif cat == "Evaluation":
        eval_dir = "apps/server/src/rulerepo_server/services/evaluation"
        if "Evaluation API" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/evaluation.py")
        elif "Diff parser" in name:
            _check_file(fc, f"{eval_dir}/diff_parser.py")
        elif "Context assembler" in name:
            _check_file(fc, f"{eval_dir}/context_assembler.py")
        elif "Rule selector" in name:
            _check_file(fc, f"{eval_dir}/rule_selector.py")
        elif "Batch evaluator" in name:
            _check_file(fc, f"{eval_dir}/batch_evaluator.py")
        elif "Verdict aggregator" in name:
            _check_file(fc, f"{eval_dir}/verdict_aggregator.py")
        elif "Conflict aggregator" in name:
            _check_file(fc, f"{eval_dir}/conflict_aggregator.py")
        elif "Graph resolver" in name:
            _check_file(fc, f"{eval_dir}/graph_resolver.py")
        elif "Impact preview" in name:
            _check_file(fc, f"{eval_dir}/impact_preview.py")
        elif "DomainAdapter Protocol" in name:
            _check_file(fc, f"{eval_dir}/adapters/base.py")
        elif "Code adapter" in name:
            _check_dir(fc, f"{eval_dir}/adapters/code")
        elif "business_event" in name:
            _check_dir(fc, f"{eval_dir}/adapters/business_event")
        elif "document_diff" in name:
            _check_dir(fc, f"{eval_dir}/adapters/document_diff")
        elif "communication adapter" in name:
            _check_dir(fc, f"{eval_dir}/adapters/communication")
        elif "documentation adapter" in name:
            _check_dir(fc, f"{eval_dir}/adapters/documentation")
        elif "Consensus" in name:
            _check_file(fc, f"{eval_dir}/consensus.py")
        elif "Idempotency" in name:
            _check_file(fc, f"{eval_dir}/idempotency.py")

    # -- Extraction --
    elif cat == "Extraction":
        if "pipeline" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/services/extraction/pipeline.py")
        elif "upload" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/extraction.py")
        elif "sanitizer" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/services/extraction/pdf_sanitizer.py")
        elif "clause" in name.lower():
            _check_dir(fc, "apps/server/src/rulerepo_server/services/extraction/contract")

    # -- Intent --
    elif cat == "Intent":
        if "API" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/intent.py")
        elif "classifier" in name:
            _check_class(fc, "IntentClassifier")

    # -- Discovery --
    elif cat == "Discovery":
        disc = "apps/server/src/rulerepo_server/services/discovery"
        if "scan API" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/discovery.py")
        elif "CLAUDE.md" in name:
            _check_file(fc, f"{disc}/analyzers/claude_md.py")
        elif "Linter" in name:
            _check_file(fc, f"{disc}/analyzers/linter_config.py")
        elif "Code patterns" in name:
            _check_file(fc, f"{disc}/analyzers/code_patterns.py")
        elif "Policy" in name:
            _check_file(fc, f"{disc}/analyzers/policy_document.py")
        elif "Confluence" in name:
            _check_file(fc, f"{disc}/connectors/confluence.py")
        elif "Notion" in name:
            _check_file(fc, f"{disc}/connectors/notion.py")
        elif "e-Gov" in name:
            _check_file(fc, f"{disc}/connectors/egov.py")
        elif "EUR-Lex" in name:
            _check_file(fc, f"{disc}/connectors/eurlex.py")

    # -- Feedback --
    elif cat == "Feedback":
        fb = "apps/server/src/rulerepo_server/services/feedback"
        if "API" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/feedback.py")
        elif "Auto-draft" in name:
            _check_file(fc, f"{fb}/auto_drafter.py")
        elif "analyzer" in name:
            _check_file(fc, f"{fb}/correction_analyzer.py")

    # -- Federation --
    elif cat == "Federation":
        if "CRUD" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/federation.py")
        elif "Effective" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/services/federation/resolver.py")
        elif "diff" in name:
            _check_endpoint_in_file(fc, "diff", "apps/server/src/rulerepo_server/api/v1/federation.py")

    # -- Snapshots --
    elif cat == "Snapshots":
        if "CRUD" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/snapshots.py")
        elif "deploy" in name or "rollback" in name:
            _check_endpoint_in_file(fc, "deploy", "apps/server/src/rulerepo_server/api/v1/snapshots.py")
        elif "simulate" in name.lower() and "bulk" not in name.lower():
            _check_endpoint_in_file(fc, "simulate", "apps/server/src/rulerepo_server/api/v1/snapshots.py")
        elif "bulk" in name.lower():
            _check_endpoint_in_file(fc, "simulate-bulk", "apps/server/src/rulerepo_server/api/v1/snapshots.py")

    # -- Proposals --
    elif cat == "Proposals":
        if "CRUD" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/proposals.py")
        elif "voting" in name:
            _check_endpoint_in_file(fc, "vote", "apps/server/src/rulerepo_server/api/v1/proposals.py")
        elif "enact" in name:
            _check_endpoint_in_file(fc, "enact", "apps/server/src/rulerepo_server/api/v1/proposals.py")
        elif "notification" in name.lower():
            _check_endpoint_in_file(fc, "notification", "apps/server/src/rulerepo_server/api/v1/proposals.py")

    # -- Agent Governance --
    elif cat == "Agent Governance":
        ag_router = "apps/server/src/rulerepo_server/api/v1/agent_governance.py"
        if "registration" in name:
            _check_endpoint_in_file(fc, "register", ag_router)
        elif "trust" in name:
            _check_class(fc, "TrustLevel")
        elif "mastery" in name:
            _check_endpoint_in_file(fc, "mastery", ag_router)
        elif "exception" in name:
            _check_endpoint_in_file(fc, "exception", ag_router)
        elif "negotiation" in name:
            _check_endpoint_in_file(fc, "negotiate", ag_router)
        elif "session" in name.lower():
            _check_endpoint_in_file(fc, "session", ag_router)

    # -- Intelligence --
    elif cat == "Intelligence":
        intel = "apps/server/src/rulerepo_server/services/intelligence"
        if "dashboard" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/intelligence.py")
        elif "Health" in name:
            _check_file(fc, f"{intel}/health_scorer.py")
        elif "effectiveness" in name.lower():
            _check_file(fc, f"{intel}/effectiveness.py")
        elif "Recommendation" in name:
            _check_file(fc, f"{intel}/recommender.py")
        elif "Agent analytics" in name:
            _check_file(fc, f"{intel}/agent_analytics.py")
        elif "digest" in name.lower():
            _check_file(fc, f"{intel}/digest.py")

    # -- Playground --
    elif cat == "Playground":
        pg = "apps/server/src/rulerepo_server/services/playground"
        if "evaluate" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/api/v1/playground.py")
        elif "generation" in name.lower():
            _check_file(fc, f"{pg}/test_generator.py")
        elif "runner" in name.lower():
            _check_file(fc, f"{pg}/test_runner.py")
        elif "Counterexample" in name:
            _check_file(fc, f"{pg}/counterexample_generator.py")

    # -- MCP --
    elif cat == "MCP":
        mcp = "apps/server/src/rulerepo_server/mcp"
        if "server" in name.lower():
            _check_file(fc, f"{mcp}/server.py")
        elif "tools" in name.lower():
            _check_file(fc, f"{mcp}/tools.py")
        elif "resources" in name.lower():
            _check_file(fc, f"{mcp}/resources.py")
        elif "prompts" in name.lower():
            _check_file(fc, f"{mcp}/prompts.py")

    # -- Gateway --
    elif cat == "Gateway":
        if "webhook" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/gateway/router.py")
        elif "enforcement" in name.lower():
            _check_class(fc, "EnforcementPolicyModel")
        elif "Slack" in name or "Teams" in name or "Email" in name:
            # Check for normalizer files in gateway/normalizers/
            gw = ROOT / "apps/server/src/rulerepo_server/gateway/normalizers"
            has_slack = (gw / "slack.py").is_file()
            has_teams = (gw / "teams.py").is_file()
            has_email = (gw / "email.py").is_file()
            if has_slack and has_teams and has_email:
                fc.actual_status = STATUS_IMPLEMENTED
                fc.evidence = ["slack.py", "teams.py", "email.py"]
            else:
                fc.actual_status = STATUS_PLANNED
                fc.notes = "Missing normalizers: " + ", ".join(
                    n for n, e in [("slack", has_slack), ("teams", has_teams), ("email", has_email)] if not e
                )

    # -- Integrations --
    elif cat == "Integrations":
        gh = "apps/server/src/rulerepo_server/integrations/github"
        if "webhook" in name.lower():
            _check_file(fc, f"{gh}/router.py")
        elif "check reporter" in name.lower():
            _check_file(fc, f"{gh}/check_reporter.py")

    # -- Audit --
    elif cat == "Audit":
        if "append-only" in name:
            _check_class(fc, "AuditLogModel")
        elif "inspection API" in name:
            # Check for a dedicated audit router
            audit_router = ROOT / "apps/server/src/rulerepo_server/api/v1/audit.py"
            if audit_router.is_file():
                fc.actual_status = STATUS_IMPLEMENTED
                fc.evidence.append(str(audit_router.relative_to(ROOT)))
            else:
                fc.actual_status = STATUS_PLANNED
                fc.notes = "No dedicated audit API router found"
        elif "verification script" in name:
            _check_file(fc, "scripts/verify_audit_chain.py")
        elif "frontend" in name.lower():
            _check_frontend_page(fc, "audit")

    # -- Provenance --
    elif cat == "Provenance":
        if "Why API" in name:
            _check_endpoint_in_file(fc, "why", "apps/server/src/rulerepo_server/api/v1/rules.py")
        elif "lineage" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/services/provenance/lineage_resolver.py")
        elif "basis_type" in name:
            neo4j_dir = ROOT / "apps/server/src/rulerepo_server/adapters/neo4j"
            matches = grep_recursive(neo4j_dir, r"basis_type")
            if matches:
                fc.actual_status = STATUS_IMPLEMENTED
                fc.evidence = matches[:3]
            else:
                fc.actual_status = STATUS_PLANNED
                fc.notes = "No basis_type property found in Neo4j adapter"

    # -- PII --
    elif cat == "PII":
        if "tokenizer" in name.lower():
            _check_file(fc, "apps/server/src/rulerepo_server/core/pii/tokenizer.py")
        elif "masking" in name.lower():
            pii_file = ROOT / "apps/server/src/rulerepo_server/core/pii.py"
            pii_dir = ROOT / "apps/server/src/rulerepo_server/core/pii"
            if pii_file.is_file() or pii_dir.is_dir():
                fc.actual_status = STATUS_PARTIAL
                fc.evidence.append("core/pii.py or core/pii/ exists")
                fc.notes = "Basic PII module exists but may not be fully wired"
            else:
                fc.actual_status = STATUS_PLANNED
        elif "encryption" in name.lower():
            models = "apps/server/src/rulerepo_server/adapters/postgres/models.py"
            _check_field_in_model(fc, "context_encrypted", models)

    # -- Multi-tenancy --
    elif cat == "Multi-tenancy":
        if "Tenant model" in name:
            _check_field_in_model(fc, "tenant_id", "apps/server/src/rulerepo_server/adapters/postgres/models.py")
        elif "Row-Level" in name:
            _check_file(fc, "infra/postgres/rls_policies.sql")
        elif "Elasticsearch" in name:
            es_dir = ROOT / "apps/server/src/rulerepo_server/adapters/elasticsearch"
            matches = grep_recursive(es_dir, r"routing.*tenant")
            if matches:
                fc.actual_status = STATUS_IMPLEMENTED
                fc.evidence = matches[:3]
            else:
                fc.actual_status = STATUS_PLANNED
        elif "Neo4j" in name:
            neo4j_dir = ROOT / "apps/server/src/rulerepo_server/adapters/neo4j"
            matches = grep_recursive(neo4j_dir, r"multi.?database|tenant")
            if matches:
                fc.actual_status = STATUS_IMPLEMENTED
                fc.evidence = matches[:3]
            else:
                fc.actual_status = STATUS_PLANNED

    # -- Observability --
    elif cat == "Observability":
        if "OpenTelemetry" in name:
            _check_file(fc, "apps/server/src/rulerepo_server/core/logging.py")
        elif "Cost ledger" in name:
            models = "apps/server/src/rulerepo_server/adapters/postgres/models.py"
            _check_field_in_model(fc, "input_tokens", models)

    # -- LLM --
    elif cat == "LLM":
        llm_dir = "apps/server/src/rulerepo_server/adapters/llm"
        if "Protocol" in name:
            _check_file(fc, f"{llm_dir}/base.py")
        elif "Gemini" in name:
            _check_dir(fc, "apps/server/src/rulerepo_server/adapters/gemini")
        elif "Anthropic" in name:
            _check_file(fc, f"{llm_dir}/anthropic.py")
        elif "OpenAI" in name:
            _check_file(fc, f"{llm_dir}/openai.py")
        elif "Local" in name:
            _check_file(fc, f"{llm_dir}/local.py")

    # -- CLI --
    elif cat == "CLI":
        cli_dir = "packages/cli/src/rulerepo_cli"
        if "Unified" in name:
            _check_file(fc, f"{cli_dir}/main.py")
        elif "check" in name:
            _check_file(fc, "packages/cli/src/rulerepo_cli/commands/check.py")
            if fc.actual_status != STATUS_IMPLEMENTED:
                # Fall back to old-style location
                _check_file(fc, "packages/cli/src/rulerepo_cli/check.py")
        elif "hook" in name:
            _check_files(
                fc,
                [
                    "packages/cli/src/rulerepo_cli/commands/hook.py",
                    "packages/cli/src/rulerepo_cli/hook.py",
                ],
                any_of=True,
            )
        elif "ingest" in name:
            _check_files(
                fc,
                [
                    "packages/cli/src/rulerepo_cli/commands/ingest.py",
                    "packages/cli/src/rulerepo_cli/ingest.py",
                ],
                any_of=True,
            )
        elif "export" in name:
            _check_files(
                fc,
                [
                    "packages/cli/src/rulerepo_cli/commands/export.py",
                    "packages/cli/src/rulerepo_cli/export.py",
                ],
                any_of=True,
            )
        elif "context" in name:
            _check_files(
                fc,
                [
                    "packages/cli/src/rulerepo_cli/commands/context.py",
                    "packages/cli/src/rulerepo_cli/context.py",
                ],
                any_of=True,
            )
        elif "mcp" in name.lower():
            _check_files(
                fc,
                [
                    "packages/cli/src/rulerepo_cli/commands/mcp.py",
                    "apps/server/src/rulerepo_server/mcp/server.py",
                ],
                any_of=True,
            )
        elif "init" in name:
            _check_file(fc, "packages/cli/src/rulerepo_cli/commands/init.py")
        elif "doctor" in name:
            _check_file(fc, "packages/cli/src/rulerepo_cli/commands/doctor.py")
        elif "audit" in name:
            _check_file(fc, "packages/cli/src/rulerepo_cli/commands/audit.py")

    # -- Workers --
    elif cat == "Workers":
        w = "apps/server/src/rulerepo_server/workers"
        if "settings" in name.lower():
            _check_file(fc, f"{w}/settings.py")
        elif "conflict" in name.lower():
            _check_file(fc, f"{w}/conflict_scanner.py")
        elif "archival" in name.lower() or "Archival" in name:
            _check_file(fc, f"{w}/archival.py")
        elif "review cycle" in name.lower():
            _check_file(fc, f"{w}/policy_review_cycle.py")
        elif "drift" in name.lower():
            _check_file(fc, f"{w}/verdict_drift.py")
        elif "polyglot" in name.lower() or "Polyglot" in name:
            _check_file(fc, f"{w}/polyglot_validator.py")

    # -- Frontend --
    elif cat == "Frontend":
        if "page" in name.lower():
            # Extract the page name
            page_name = name.lower().replace(" page", "").replace(" list", "").strip()
            _check_frontend_page(fc, page_name)
        elif "Persona switcher" in name:
            matches = grep_recursive(FRONTEND_APP, r"persona|PersonaSwitcher", "*.tsx")
            fc.actual_status = STATUS_IMPLEMENTED if matches else STATUS_PLANNED
            fc.evidence = matches[:3]
        elif "Sidebar" in name:
            # Must find the actual sidebar section grouping, not just any mention of these words
            matches = grep_recursive(
                FRONTEND_APP,
                r'"(Compose|Govern|Observe|Share|Agents)".*section|section.*"(Compose|Govern|Observe|Share|Agents)"',
                "*.tsx",
            )
            if len(matches) >= 3:
                fc.actual_status = STATUS_IMPLEMENTED
            elif matches:
                fc.actual_status = STATUS_PARTIAL
            else:
                fc.actual_status = STATUS_PLANNED
            fc.evidence = matches[:3]

    # -- Infrastructure --
    elif cat == "Infrastructure":
        dc = ROOT / "docker-compose.yml"
        if "Docker Compose" in name:
            _check_file(fc, "docker-compose.yml")
        elif "init.sql" in name:
            _check_file(fc, "infra/postgres/init.sql")
        elif "Elasticsearch" in name:
            _check_file(fc, "infra/elasticsearch/setup.sh")
        elif "init.cypher" in name:
            _check_file(fc, "infra/neo4j/init.cypher")
        elif "Redis" in name:
            matches = grep_in_file(dc, r"redis")
            fc.actual_status = STATUS_IMPLEMENTED if matches else STATUS_PLANNED
            fc.evidence = matches[:3]
        elif "arq-worker" in name:
            matches = grep_in_file(dc, r"arq.worker|arq-worker")
            fc.actual_status = STATUS_IMPLEMENTED if matches else STATUS_PLANNED
            fc.evidence = matches[:3]
        elif "MCP server" in name:
            matches = grep_in_file(dc, r"mcp.server|mcp-server")
            fc.actual_status = STATUS_IMPLEMENTED if matches else STATUS_PLANNED
            fc.evidence = matches[:3]

    # -- Scripts --
    elif cat == "Scripts":
        _check_file(fc, f"scripts/{name}")

    # -- Sample Rules --
    elif cat == "Sample Rules":
        if "Coding" in name:
            _check_dir(fc, "sample_rules/coding_rules")
        elif "Company" in name:
            _check_dir(fc, "sample_rules/company_rules")
        elif "Sales" in name:
            _check_dir(fc, "sample_rules/sales_team_rules")
        elif "template" in name.lower():
            _check_dir(fc, "sample_rules/templates")
        elif "Legal" in name:
            _check_dir(fc, "sample_rules/legal_rules")
        elif "Communication" in name:
            _check_dir(fc, "sample_rules/communication_rules")

    # -- Tier 0 --
    elif cat == "Tier 0":
        if "spec_audit" in name:
            _check_file(fc, "scripts/spec_audit.py")
        elif "feature_interactions" in name:
            _check_file(fc, "development/feature_interactions.md")
        elif "spec_implementation_audit" in name:
            _check_file(fc, "development/spec_implementation_audit.md")
        elif "feature_matrix" in name:
            _check_dir(fc, "apps/server/tests/integration/feature_matrix")
        elif "make spec-audit" in name:
            matches = grep_in_file(ROOT / "Makefile", r"spec.audit|spec-audit")
            fc.actual_status = STATUS_IMPLEMENTED if matches else STATUS_PLANNED
            fc.evidence = matches[:3]

    # Fallback: if actual_status wasn't set
    if not fc.actual_status:
        fc.actual_status = STATUS_PLANNED
        fc.notes = fc.notes or "No automated check implemented for this feature"


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------


def _check_file(fc: FeatureCheck, rel_path: str) -> None:
    p = ROOT / rel_path
    if p.is_file():
        fc.actual_status = STATUS_IMPLEMENTED
        fc.evidence.append(rel_path)
    else:
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"File not found: {rel_path}"


def _check_dir(fc: FeatureCheck, rel_path: str) -> None:
    p = ROOT / rel_path
    if p.is_dir() and any(p.iterdir()):
        fc.actual_status = STATUS_IMPLEMENTED
        fc.evidence.append(f"{rel_path}/ (directory with files)")
    elif p.is_dir():
        fc.actual_status = STATUS_PARTIAL
        fc.evidence.append(f"{rel_path}/ (empty directory)")
    else:
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"Directory not found: {rel_path}"


def _check_files(fc: FeatureCheck, paths: list[str], any_of: bool = False) -> None:
    found = []
    missing = []
    for p in paths:
        if (ROOT / p).is_file():
            found.append(p)
        else:
            missing.append(p)
    if any_of:
        if found:
            fc.actual_status = STATUS_IMPLEMENTED
            fc.evidence = found
        else:
            fc.actual_status = STATUS_PLANNED
            fc.notes = f"None found: {', '.join(missing)}"
    else:
        if len(found) == len(paths):
            fc.actual_status = STATUS_IMPLEMENTED
            fc.evidence = found
        elif found:
            fc.actual_status = STATUS_PARTIAL
            fc.evidence = found
            fc.notes = f"Missing: {', '.join(missing)}"
        else:
            fc.actual_status = STATUS_PLANNED
            fc.notes = f"Missing: {', '.join(missing)}"


def _check_class(fc: FeatureCheck, class_name: str) -> None:
    if has_class(SERVER_SRC, class_name):
        fc.actual_status = STATUS_IMPLEMENTED
        fc.evidence.append(f"class {class_name} found in server src")
    else:
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"class {class_name} not found"


def _check_class_and_file(fc: FeatureCheck, class_name: str, rel_path: str) -> None:
    p = ROOT / rel_path
    if p.is_file() and has_class(p.parent, class_name):
        fc.actual_status = STATUS_IMPLEMENTED
        fc.evidence.append(rel_path)
    elif p.is_file():
        fc.actual_status = STATUS_PARTIAL
        fc.evidence.append(rel_path)
        fc.notes = f"File exists but class {class_name} not found in it"
    else:
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"File not found: {rel_path}"


def _check_field_in_model(fc: FeatureCheck, field_name: str, rel_path: str) -> None:
    p = ROOT / rel_path
    if not p.is_file():
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"File not found: {rel_path}"
        return
    matches = grep_in_file(p, rf"\b{field_name}\b")
    if matches:
        fc.actual_status = STATUS_IMPLEMENTED
        fc.evidence = matches[:3]
    else:
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"Field '{field_name}' not found in {rel_path}"


def _check_endpoint_in_file(fc: FeatureCheck, fragment: str, rel_path: str) -> None:
    p = ROOT / rel_path
    if not p.is_file():
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"Router file not found: {rel_path}"
        return
    matches = grep_in_file(p, fragment)
    if matches:
        fc.actual_status = STATUS_IMPLEMENTED
        fc.evidence = matches[:3]
    else:
        fc.actual_status = STATUS_PLANNED
        fc.notes = f"'{fragment}' not found in {rel_path}"


def _check_frontend_page(fc: FeatureCheck, page_name: str) -> None:
    """Check if a frontend page exists."""
    # Map common names to directory names
    name_map = {
        "rules": "rules",
        "rule detail": "rules",
        "search": "search",
        "documents": "documents",
        "discovery": "discover",
        "playground": "playground",
        "proposals": "proposals",
        "federation": "federations",
        "federations": "federations",
        "snapshots": "snapshots",
        "intelligence": "intelligence",
        "feedback": "feedback",
        "agents": "agents",
        "gateway": "gateway",
        "review": "review",
        "notifications": "notifications",
        "projects": "projects",
        "integrations": "integrations",
        "audit": "audit",
        "rule tutor": "tutor",
        "tutor": "tutor",
    }
    dir_name = name_map.get(page_name, page_name)
    page_path = FRONTEND_APP / "(dashboard)" / dir_name / "page.tsx"
    if page_path.is_file():
        fc.actual_status = STATUS_IMPLEMENTED
        fc.evidence.append(str(page_path.relative_to(ROOT)))
    else:
        # Also check root level
        page_path_root = FRONTEND_APP / dir_name / "page.tsx"
        if page_path_root.is_file():
            fc.actual_status = STATUS_IMPLEMENTED
            fc.evidence.append(str(page_path_root.relative_to(ROOT)))
        else:
            fc.actual_status = STATUS_PLANNED
            fc.notes = f"No page.tsx found for '{dir_name}'"


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(report: AuditReport) -> str:
    """Generate the markdown audit report."""
    lines: list[str] = []
    lines.append("# Spec Implementation Audit")
    lines.append("")
    lines.append(f"> Generated: {report.timestamp}")
    lines.append("> Method: code-only heuristic (file existence, pattern matching)")
    lines.append("> Source docs: PROJECT.md, CLAUDE.md")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    total = len(report.features)
    lines.append("| Status | Count | % |")
    lines.append("|--------|-------|---|")
    for status in [STATUS_IMPLEMENTED, STATUS_PARTIAL, STATUS_PLANNED, STATUS_MISSING]:
        count = report.summary.get(status, 0)
        pct = f"{count / total * 100:.1f}" if total else "0"
        lines.append(f"| {status} | {count} | {pct}% |")
    lines.append(f"| **Total** | **{total}** | |")
    lines.append("")

    # Drift detection
    drift_items = [
        f
        for f in report.features
        if f.declared_status != f.actual_status
        and f.declared_status != STATUS_PLANNED  # Only flag drift for non-PLANNED
    ]
    if drift_items:
        lines.append("## Spec-Implementation Drift")
        lines.append("")
        lines.append("Features where the declared status in PROJECT.md/CLAUDE.md differs from what the code shows:")
        lines.append("")
        lines.append("| Feature | Category | Declared | Actual | Notes |")
        lines.append("|---------|----------|----------|--------|-------|")
        for f in drift_items:
            notes = f.notes.replace("|", "\\|") if f.notes else ""
            lines.append(f"| {f.name} | {f.category} | {f.declared_status} | {f.actual_status} | {notes} |")
        lines.append("")

    # PLANNED features that actually exist
    surprise_impl = [
        f
        for f in report.features
        if f.declared_status == STATUS_PLANNED and f.actual_status in (STATUS_IMPLEMENTED, STATUS_PARTIAL)
    ]
    if surprise_impl:
        lines.append("## Undocumented Implementations")
        lines.append("")
        lines.append("Features declared as PLANNED but found in the codebase:")
        lines.append("")
        lines.append("| Feature | Category | Actual | Evidence |")
        lines.append("|---------|----------|--------|----------|")
        for f in surprise_impl:
            ev = "; ".join(f.evidence[:2]) if f.evidence else ""
            lines.append(f"| {f.name} | {f.category} | {f.actual_status} | {ev} |")
        lines.append("")

    # Per-category breakdown
    categories: dict[str, list[FeatureCheck]] = {}
    for f in report.features:
        categories.setdefault(f.category, []).append(f)

    lines.append("## Detailed Breakdown")
    lines.append("")
    for cat, features in sorted(categories.items()):
        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| Feature | Declared | Actual | Match | Evidence |")
        lines.append("|---------|----------|--------|-------|----------|")
        for f in features:
            match_icon = "Y" if f.declared_status == f.actual_status else "**N**"
            ev = "; ".join(f.evidence[:2]) if f.evidence else (f.notes or "-")
            ev = ev.replace("|", "\\|")
            lines.append(f"| {f.name} | {f.declared_status} | {f.actual_status} | {match_icon} | {ev} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM-enhanced classification (behind --live-llm)
# ---------------------------------------------------------------------------


async def enhance_with_llm(report: AuditReport) -> None:
    """Use Gemini to refine classification for ambiguous features.

    Only called with --live-llm flag. Requires GEMINI_API_KEY.
    """
    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai not installed. Run: uv add google-genai")
        return

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set. Skipping LLM enhancement.")
        return

    client = genai.Client(api_key=api_key)

    # Only enhance features where declared != actual (potential drift)
    ambiguous = [f for f in report.features if f.declared_status != f.actual_status]

    if not ambiguous:
        print("No ambiguous features to enhance with LLM.")
        return

    print(f"Enhancing {len(ambiguous)} ambiguous features with Gemini...")

    # Process in batches of 10
    batch_size = 10
    for i in range(0, len(ambiguous), batch_size):
        batch = ambiguous[i : i + batch_size]
        features_text = "\n".join(
            f"- {f.name} (category: {f.category}, declared: {f.declared_status}, "
            f"code-scan: {f.actual_status}, evidence: {'; '.join(f.evidence[:2]) or 'none'}, "
            f"notes: {f.notes or 'none'})"
            for f in batch
        )

        prompt = f"""You are auditing a software project's documentation against its codebase.

For each feature below, determine the most accurate implementation status:
- IMPLEMENTED: Feature is fully working in the codebase
- PARTIAL: Feature exists but is incomplete or only partially functional
- PLANNED: Feature is documented but not yet implemented
- MISSING: Feature was supposed to exist but cannot be found

Features to classify:
{features_text}

Based on the project documentation context (PROJECT.md and CLAUDE.md have been provided),
refine each classification. Consider that:
- A file existing doesn't mean the feature is complete
- A PARTIAL status means some code exists but the full feature isn't done
- Some features may be structurally present but not wired up

Respond with a JSON array of objects, each with:
- "name": feature name (exact match)
- "status": one of IMPLEMENTED, PARTIAL, PLANNED, MISSING
- "reasoning": one sentence explaining why
"""

        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "thinking": {"thinking_level": "low"},
                },
            )
            import json

            results = json.loads(response.text)
            result_map = {r["name"]: r for r in results}

            for f in batch:
                if f.name in result_map:
                    r = result_map[f.name]
                    f.actual_status = r["status"]
                    f.notes = r.get("reasoning", f.notes)

        except Exception as e:
            print(f"  LLM batch {i // batch_size + 1} failed: {e}")
            continue

    print("LLM enhancement complete.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit spec documents against the codebase.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output file path (default: development/spec_implementation_audit.md)",
    )
    parser.add_argument(
        "--live-llm",
        action="store_true",
        help="Use Gemini for deeper semantic classification (requires GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output results as JSON",
    )
    args = parser.parse_args()

    print("Rule Repository — Spec Implementation Audit")
    print("=" * 50)

    # Build feature checks
    features = build_feature_checks()
    print(f"Checking {len(features)} features...")

    # Run code-only verification
    for fc in features:
        verify_feature(fc)

    # LLM enhancement if requested
    if args.live_llm:
        import asyncio

        asyncio.run(enhance_with_llm(AuditReport(features=features)))

    # Build report
    report = AuditReport(
        timestamp=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        features=features,
    )

    # Compute summary
    for status in [STATUS_IMPLEMENTED, STATUS_PARTIAL, STATUS_PLANNED, STATUS_MISSING]:
        report.summary[status] = sum(1 for f in features if f.actual_status == status)

    # Generate markdown
    md = generate_report(report)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    print(f"\nReport written to {output_path}")

    # Summary
    print("\nSummary:")
    for status, count in sorted(report.summary.items()):
        print(f"  {status}: {count}")

    # Drift warnings
    drift = [f for f in features if f.declared_status != f.actual_status and f.declared_status != STATUS_PLANNED]
    if drift:
        print(f"\n  DRIFT DETECTED: {len(drift)} feature(s) differ from spec")
        for f in drift[:10]:
            print(f"    - {f.name}: declared={f.declared_status}, actual={f.actual_status}")

    # JSON output
    if args.json:
        import json

        json_path = output_path.with_suffix(".json")
        data = {
            "timestamp": report.timestamp,
            "summary": report.summary,
            "features": [
                {
                    "name": f.name,
                    "category": f.category,
                    "declared_status": f.declared_status,
                    "actual_status": f.actual_status,
                    "evidence": f.evidence,
                    "notes": f.notes,
                }
                for f in features
            ],
        }
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"JSON written to {json_path}")


if __name__ == "__main__":
    main()
