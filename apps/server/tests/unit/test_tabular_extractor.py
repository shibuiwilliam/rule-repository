"""Tests for the tabular extractor — financial metadata tagging."""

from __future__ import annotations

from pathlib import Path

import pytest

from rulerepo_server.services.extraction.extractors import SourceFile
from rulerepo_server.services.extraction.extractors.tabular import (
    TabularExtractor,
    _detect_financial_columns,
    _extract_financial_metadata,
)

# ---------------------------------------------------------------------------
# Financial Column Detection
# ---------------------------------------------------------------------------


class TestDetectFinancialColumns:
    def test_account_code_jp(self) -> None:
        result = _detect_financial_columns({"勘定科目", "内容", "上限金額"})
        assert result["勘定科目"] == "account_code"

    def test_account_code_en(self) -> None:
        result = _detect_financial_columns({"account_code", "description", "amount"})
        assert result["account_code"] == "account_code"

    def test_tax_category_jp(self) -> None:
        result = _detect_financial_columns({"税区分", "備考"})
        assert result["税区分"] == "tax_category"

    def test_tax_category_en(self) -> None:
        result = _detect_financial_columns({"tax_category", "notes"})
        assert result["tax_category"] == "tax_category"

    def test_cost_center(self) -> None:
        result = _detect_financial_columns({"コストセンター", "項目"})
        assert result["コストセンター"] == "cost_center"

    def test_amount_limit(self) -> None:
        result = _detect_financial_columns({"上限", "description"})
        assert result["上限"] == "amount_limit"

    def test_gl_code(self) -> None:
        result = _detect_financial_columns({"GL Code", "description"})
        assert result["GL Code"] == "account_code"

    def test_no_financial_columns(self) -> None:
        result = _detect_financial_columns({"name", "description", "priority"})
        assert result == {}

    def test_multiple_financial_columns(self) -> None:
        headers = {"勘定科目", "税区分", "コストセンター", "上限", "内容"}
        result = _detect_financial_columns(headers)
        assert len(result) == 4


# ---------------------------------------------------------------------------
# Financial Metadata Extraction
# ---------------------------------------------------------------------------


class TestExtractFinancialMetadata:
    def test_extract_values(self) -> None:
        row = {"勘定科目": "4110", "税区分": "課税", "内容": "交通費"}
        fin_columns = {"勘定科目": "account_code", "税区分": "tax_category"}
        meta = _extract_financial_metadata(row, fin_columns)
        assert meta["account_code"] == "4110"
        assert meta["tax_category"] == "課税"

    def test_skip_empty_values(self) -> None:
        row = {"勘定科目": "4110", "税区分": None}
        fin_columns = {"勘定科目": "account_code", "税区分": "tax_category"}
        meta = _extract_financial_metadata(row, fin_columns)
        assert "account_code" in meta
        assert "tax_category" not in meta

    def test_empty_when_no_fin_columns(self) -> None:
        row = {"name": "test"}
        meta = _extract_financial_metadata(row, {})
        assert meta == {}


# ---------------------------------------------------------------------------
# Full Extractor Integration (CSV)
# ---------------------------------------------------------------------------

FINANCIAL_CSV = """\
勘定科目,税区分,statement,modality,severity
4110,課税,交通費は月額5万円を上限とする,MUST,MEDIUM
4120,非課税,通勤手当は実費支給とする,SHOULD,LOW
4210,課税,接待交際費は事前承認を得なければならない,MUST,HIGH
"""

PLAIN_CSV = """\
rule_name,statement,modality,severity
naming,Variables must use camelCase,MUST,MEDIUM
logging,All errors shall be logged,MUST,HIGH
"""


class TestTabularExtractorFinancial:
    @pytest.mark.asyncio
    async def test_financial_csv(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_financial.csv"),
            source_type="csv",
            content=FINANCIAL_CSV,
            metadata={"department": "finance"},
        )
        extractor = TabularExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) == 3

        # All candidates should have financial metadata
        for c in candidates:
            assert "financial" in c.tags
            fin_meta = c.source_refs.get("financial_metadata")
            assert fin_meta is not None
            assert "account_code" in fin_meta
            assert "tax_category" in fin_meta

        # Check specific values
        assert candidates[0].source_refs["financial_metadata"]["account_code"] == "4110"
        assert candidates[0].source_refs["financial_metadata"]["tax_category"] == "課税"

    @pytest.mark.asyncio
    async def test_non_financial_csv(self) -> None:
        source = SourceFile(
            path=Path("/tmp/test_plain.csv"),
            source_type="csv",
            content=PLAIN_CSV,
            metadata={"department": "engineering"},
        )
        extractor = TabularExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) == 2

        # No financial tags or metadata
        for c in candidates:
            assert "financial" not in c.tags
            assert "financial_metadata" not in c.source_refs

    @pytest.mark.asyncio
    async def test_withholding_tax_column(self) -> None:
        csv_content = "源泉徴収,statement\n対象,報酬は源泉徴収の対象とする\n"
        source = SourceFile(
            path=Path("/tmp/test_wh.csv"),
            source_type="csv",
            content=csv_content,
            metadata={},
        )
        extractor = TabularExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) == 1
        assert "financial" in candidates[0].tags
        fin_meta = candidates[0].source_refs.get("financial_metadata", {})
        assert "tax_category" in fin_meta


# ---------------------------------------------------------------------------
# Contract Extractor — effective dates and parties
# ---------------------------------------------------------------------------


class TestContractExtractorEnhancements:
    """Test the contract extractor's new cross-reference and metadata features."""

    @pytest.mark.asyncio
    async def test_effective_date_extraction(self) -> None:
        from rulerepo_server.services.extraction.contract.clause_segmenter import (
            segment_contract,
        )
        from rulerepo_server.services.extraction.extractors.contract import (
            _extract_contract_metadata,
        )

        text = (
            "This Agreement is effective as of 2025-03-15.\n\n"
            "Article 1. Obligations\n"
            "The Buyer shall pay within 30 days.\n"
        )
        doc = segment_contract(text)
        meta = _extract_contract_metadata(text, doc)
        assert "2025-03-15" in meta.effective_dates

    @pytest.mark.asyncio
    async def test_jp_effective_date(self) -> None:
        from rulerepo_server.services.extraction.contract.clause_segmenter import (
            segment_contract,
        )
        from rulerepo_server.services.extraction.extractors.contract import (
            _extract_contract_metadata,
        )

        text = "契約日：2024年10月1日\n\n第1条 甲は乙に対して支払うものとする。\n"
        doc = segment_contract(text)
        meta = _extract_contract_metadata(text, doc)
        assert "2024年10月1日" in meta.effective_dates

    @pytest.mark.asyncio
    async def test_party_extraction_english(self) -> None:
        from rulerepo_server.services.extraction.contract.clause_segmenter import (
            segment_contract,
        )
        from rulerepo_server.services.extraction.extractors.contract import (
            _extract_contract_metadata,
        )

        text = (
            '"ACME Corporation" (hereinafter the "Seller") and '
            '"Beta Inc." (hereinafter the "Buyer") agree as follows:\n\n'
            "Article 1. The Seller shall deliver goods.\n"
        )
        doc = segment_contract(text)
        meta = _extract_contract_metadata(text, doc)
        assert len(meta.parties) == 2
        names = {p["name"] for p in meta.parties}
        assert "ACME Corporation" in names
        assert "Beta Inc." in names

    @pytest.mark.asyncio
    async def test_party_extraction_japanese(self) -> None:
        from rulerepo_server.services.extraction.contract.clause_segmenter import (
            segment_contract,
        )
        from rulerepo_server.services.extraction.extractors.contract import (
            _extract_contract_metadata,
        )

        text = "甲：株式会社テスト\n乙：合同会社サンプル\n\n第1条 甲は乙に支払うものとする。\n"
        doc = segment_contract(text)
        meta = _extract_contract_metadata(text, doc)
        assert len(meta.parties) >= 2
        names = {p["name"] for p in meta.parties}
        assert "株式会社テスト" in names
        assert "合同会社サンプル" in names

    @pytest.mark.asyncio
    async def test_references_attached_to_candidates(self) -> None:
        from rulerepo_server.services.extraction.extractors.contract import (
            ContractExtractor,
        )

        text = (
            "Article 1. Definitions\n"
            "Confidential Information means all non-public data.\n\n"
            "Article 2. Obligations\n"
            "As defined in Article 1, the Receiving Party shall protect all information.\n"
        )
        source = SourceFile(
            path=Path("/tmp/test_contract.txt"),
            source_type="contract",
            content=text,
            metadata={},
        )
        extractor = ContractExtractor()
        candidates = await extractor.extract(source)

        assert len(candidates) == 2
        # Article 2 should have a reference to Article 1
        art2 = candidates[1]
        refs = art2.source_refs.get("references", [])
        assert len(refs) >= 1
        assert any(r["target"] == "art1" for r in refs)

    @pytest.mark.asyncio
    async def test_term_duration(self) -> None:
        from rulerepo_server.services.extraction.contract.clause_segmenter import (
            segment_contract,
        )
        from rulerepo_server.services.extraction.extractors.contract import (
            _extract_contract_metadata,
        )

        text = "The term of this agreement is 2 years.\n\nArticle 1. Scope\nThis applies to all.\n"
        doc = segment_contract(text)
        meta = _extract_contract_metadata(text, doc)
        assert "2 years" in meta.term_duration
