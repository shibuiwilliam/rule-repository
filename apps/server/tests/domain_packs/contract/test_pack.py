"""Contract domain pack smoke test.

Loads the Contract Pack, validates its structure, verifies rules parse
correctly, and runs a sample evaluation through the Contract Surface adapter.

See CLAUDE.md §11 and §14.3.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.surfaces.contract import (
    ContractSurfaceAdapter,
)

PACK_DIR = Path(__file__).resolve().parents[3] / "src" / "rulerepo_server" / "domain_packs" / "contract"


class TestContractPackStructure:
    """Verify the Contract Pack has the required structure."""

    def test_pack_yaml_exists(self) -> None:
        assert (PACK_DIR / "pack.yaml").is_file()

    def test_pack_yaml_valid(self) -> None:
        pack = yaml.safe_load((PACK_DIR / "pack.yaml").read_text())
        assert pack["name"] == "contract"
        assert "contract" in pack["surfaces"]
        assert pack["persona"] == "legal"
        assert "default_scopes" in pack

    def test_rules_directory_exists(self) -> None:
        rules_dir = PACK_DIR / "rules"
        assert rules_dir.is_dir()
        yaml_files = list(rules_dir.glob("*.yaml"))
        assert len(yaml_files) >= 1, "Pack must contain at least one rules file"

    def test_minimum_rule_count(self) -> None:
        """Contract pack must have at least 30 rules (NDA + MSA + SOW)."""
        rules_dir = PACK_DIR / "rules"
        total_rules = 0
        for f in rules_dir.glob("*.yaml"):
            data = yaml.safe_load(f.read_text())
            if data and "rules" in data:
                total_rules += len(data["rules"])
        assert total_rules >= 30, f"Expected >=30 rules, found {total_rules}"

    def test_samples_directory_exists(self) -> None:
        samples_dir = PACK_DIR / "samples"
        assert samples_dir.is_dir()
        sample_files = list(samples_dir.iterdir())
        assert len(sample_files) >= 1, "Pack must contain at least one sample"

    def test_all_rules_have_required_fields(self) -> None:
        """Every rule must have statement, modality, severity, scope."""
        rules_dir = PACK_DIR / "rules"
        required = {"statement", "modality", "severity", "scope"}
        for f in rules_dir.glob("*.yaml"):
            data = yaml.safe_load(f.read_text())
            if not data or "rules" not in data:
                continue
            for i, rule in enumerate(data["rules"]):
                missing = required - set(rule.keys())
                assert not missing, f"{f.name} rule #{i}: missing fields {missing}"


class TestContractSurfaceAdapter:
    """Verify the Contract Surface adapter works with pack data."""

    @pytest.mark.asyncio
    async def test_evaluate_nda_clause(self) -> None:
        """Parse an NDA clause through the contract adapter."""
        adapter = ContractSurfaceAdapter()
        subject = await adapter.parse(
            {
                "clause_text": (
                    "The Receiving Party agrees to hold all Confidential "
                    "Information in strict confidence and not to disclose "
                    "it to any third party without prior written consent."
                ),
                "clause_type": "confidentiality",
                "parties": ["Acme Corp", "Beta Inc"],
                "contract_id": "TEST-NDA-001",
                "position": 1,
                "locale": "en",
            }
        )
        assert subject.surface == Surface.CONTRACT
        assert "confidentiality" in subject.description
        assert subject.locale == "en"

    @pytest.mark.asyncio
    async def test_evaluate_jp_clause(self) -> None:
        """Parse a Japanese contract clause."""
        adapter = ContractSurfaceAdapter()
        subject = await adapter.parse(
            {
                "clause_text": (
                    "受領者は、秘密情報を厳重に管理し、開示者の事前の書面による同意なく第三者に開示してはならない。"
                ),
                "clause_type": "confidentiality",
                "parties": ["株式会社テスト", "合同会社サンプル"],
                "contract_id": "TEST-NDA-JP-001",
                "position": 1,
                "locale": "ja",
            }
        )
        assert subject.surface == Surface.CONTRACT
        assert subject.locale == "ja"

    def test_resolve_scopes_nda(self) -> None:
        adapter = ContractSurfaceAdapter()
        scopes = adapter.resolve_scopes({"clause_type": "confidentiality"})
        assert "legal/contract" in scopes
        assert "legal/contract/confidentiality" in scopes

    def test_pii_redaction(self) -> None:
        adapter = ContractSurfaceAdapter()
        assert "parties" in adapter.pii_fields({})

    def test_retention_is_10_years(self) -> None:
        assert ContractSurfaceAdapter().default_audit_retention_days == 3650

    def test_prompt_hints_not_empty(self) -> None:
        adapter = ContractSurfaceAdapter()
        hints = adapter.get_prompt_hints()
        assert len(hints) > 0
        assert "contract" in hints.lower() or "clause" in hints.lower()
