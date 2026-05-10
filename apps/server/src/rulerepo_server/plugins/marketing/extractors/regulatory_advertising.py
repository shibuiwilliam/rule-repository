"""Regulatory advertising extractor for marketing plugin.

Extracts rules from Japanese advertising regulations including:
- 薬機法 (Pharmaceutical and Medical Device Act)
- 景品表示法 (Act against Unjustifiable Premiums and Misleading Representations)
- 特定商取引法 (Specified Commercial Transactions Act)
- JARO guidelines

See: CLAUDE.md SS14.11
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# --- Yakukiho (薬機法) patterns ---
# Prohibited health/beauty claim expressions
_YAKUKIHO_PROHIBITED_EXPRESSIONS: list[str] = [
    "治る",
    "治療",
    "完治",
    "万能",
    "特効薬",
    "医学的効果",
    "必ず効く",
    "確実に痩せる",
    "シミが消える",
    "シワがなくなる",
    "若返る",
    "アンチエイジング効果",
    "癌に効く",
    "血圧が下がる",
    "糖尿病が治る",
    "アレルギーが治る",
    "即効性",
    "奇跡の",
]

# Required qualifiers for health-related content
_YAKUKIHO_REQUIRED_QUALIFIERS: list[str] = [
    "個人の感想です",
    "効果には個人差があります",
    "※個人の感想であり、効果・効能を保証するものではありません",
    "医薬品ではありません",
]

# --- Keihin Hyoji Ho (景品表示法) patterns ---
# Superlative / superiority expressions requiring evidence
_KEIHYOHO_SUPERLATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(最高|最大|最強|最安|最速|最先端)"),
    re.compile(r"(No\.?\s*1|ナンバーワン|ナンバー1)"),
    re.compile(r"(業界初|世界初|日本初|国内初)"),
    re.compile(r"(世界一|日本一|業界一)"),
    re.compile(r"(唯一|オンリーワン)"),
    re.compile(r"(満足度\s*\d+%|顧客満足度)"),
    re.compile(r"(売上No|シェアNo|実績No)"),
    re.compile(r"(圧倒的|ダントツ|群を抜く)"),
]

# Prize/premium limitations
_KEIHYOHO_PRIZE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(全員にプレゼント|もれなく|必ずもらえる)"),
    re.compile(r"(抽選で|当選|懸賞)"),
]

# Misleading price patterns
_KEIHYOHO_PRICE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(\d+%\s*OFF|割引|値引き)"),
    re.compile(r"(通常価格|定価|メーカー希望小売価格).*?(→|⇒|から)\s*\d+"),
    re.compile(r"(今だけ|期間限定|本日限り)"),
    re.compile(r"(無料|0円|タダ)"),
]

# --- Tokusho Ho (特定商取引法) patterns ---
# Required disclosures for online sales
_TOKUSHOHO_REQUIRED_DISCLOSURES: list[str] = [
    "販売業者名",
    "代表者名",
    "所在地",
    "電話番号",
    "商品の価格",
    "送料",
    "支払方法",
    "引渡時期",
    "返品・交換について",
    "申込みの撤回・契約の解除",
]


def _find_yakukiho_violations(content: str) -> list[dict[str, Any]]:
    """Detect pharmaceutical/cosmetic claim violations.

    Args:
        content: Document text to analyze.

    Returns:
        List of candidate rule dicts for detected violations.
    """
    rules: list[dict[str, Any]] = []
    found_expressions: list[str] = []

    for expr in _YAKUKIHO_PROHIBITED_EXPRESSIONS:
        if expr in content:
            found_expressions.append(expr)

    if found_expressions:
        for expr in found_expressions:
            rules.append(
                {
                    "statement": (
                        f"広告コンテンツにおいて薬機法で禁止されている表現 "
                        f"'{expr}' を使用してはならない (MUST NOT use prohibited "
                        f"pharmaceutical expression: '{expr}')"
                    ),
                    "modality": "MUST_NOT",
                    "severity": "CRITICAL",
                    "scope": ["compliance/advertising", "marketing/external"],
                    "applicable_subject_types": ["creative", "document"],
                    "tags": ["yakukiho", "pharmaceutical-compliance", "regulatory"],
                    "source_section": "yakukiho_prohibited",
                    "regulation_reference": "薬機法 第66条・第68条",
                }
            )

    # Required qualifier rules
    rules.append(
        {
            "statement": (
                "健康・美容に関する広告には「効果には個人差があります」等の "
                "注意書きを含めなければならない (Health/beauty ads MUST include "
                "individual variation disclaimer)"
            ),
            "modality": "MUST",
            "severity": "CRITICAL",
            "scope": ["compliance/advertising", "marketing/external"],
            "applicable_subject_types": ["creative", "document"],
            "tags": ["yakukiho", "required-disclaimer", "regulatory"],
            "source_section": "yakukiho_qualifiers",
            "regulation_reference": "薬機法 第66条",
        }
    )

    return rules


def _find_keihyoho_violations(content: str) -> list[dict[str, Any]]:
    """Detect misleading representation violations.

    Args:
        content: Document text to analyze.

    Returns:
        List of candidate rule dicts.
    """
    rules: list[dict[str, Any]] = []

    # Superlative claims
    for pattern in _KEIHYOHO_SUPERLATIVE_PATTERNS:
        matches = pattern.findall(content)
        for match_text in matches:
            rules.append(
                {
                    "statement": (
                        f"優良誤認を避けるため、'{match_text}' 等の最上級表現には "
                        f"客観的根拠の明示が必要 (Superlative claim '{match_text}' "
                        f"MUST be accompanied by objective evidence citation)"
                    ),
                    "modality": "MUST",
                    "severity": "CRITICAL",
                    "scope": ["compliance/advertising", "marketing/external"],
                    "applicable_subject_types": ["creative", "document"],
                    "tags": ["keihyoho", "superlative-claim", "regulatory"],
                    "source_section": "keihyoho_superlatives",
                    "regulation_reference": "景品表示法 第5条第1号(優良誤認)",
                }
            )

    # Price/discount claims
    for pattern in _KEIHYOHO_PRICE_PATTERNS:
        matches = pattern.findall(content)
        for match_text in matches:
            rules.append(
                {
                    "statement": (
                        f"価格表示 '{match_text}' には条件・期間を明記しなければ"
                        f"ならない (Price/discount mention '{match_text}' MUST "
                        f"include conditions and validity period)"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "scope": ["compliance/advertising", "marketing/external"],
                    "applicable_subject_types": ["creative", "document"],
                    "tags": ["keihyoho", "price-representation", "regulatory"],
                    "source_section": "keihyoho_price",
                    "regulation_reference": "景品表示法 第5条第2号(有利誤認)",
                }
            )

    # Prize/premium rules
    for pattern in _KEIHYOHO_PRIZE_PATTERNS:
        matches = pattern.findall(content)
        for match_text in matches:
            rules.append(
                {
                    "statement": (
                        f"景品提供 '{match_text}' は景品類の上限規制に従わなければ"
                        f"ならない (Premium offer '{match_text}' MUST comply with "
                        f"prize value limits)"
                    ),
                    "modality": "MUST",
                    "severity": "HIGH",
                    "scope": ["compliance/advertising", "marketing/external"],
                    "applicable_subject_types": ["creative", "document"],
                    "tags": ["keihyoho", "prize-regulation", "regulatory"],
                    "source_section": "keihyoho_prizes",
                    "regulation_reference": "景品表示法 景品類の制限",
                }
            )

    return rules


def _find_tokushoho_requirements(content: str) -> list[dict[str, Any]]:
    """Generate rules for required disclosures in online sales.

    Args:
        content: Document text to analyze.

    Returns:
        List of candidate rule dicts for required disclosures.
    """
    rules: list[dict[str, Any]] = []

    for disclosure in _TOKUSHOHO_REQUIRED_DISCLOSURES:
        rules.append(
            {
                "statement": (
                    f"通信販売の広告には '{disclosure}' を表示しなければならない "
                    f"(Online sales advertisements MUST display: '{disclosure}')"
                ),
                "modality": "MUST",
                "severity": "CRITICAL",
                "scope": ["compliance/advertising", "marketing/external"],
                "applicable_subject_types": ["creative", "document"],
                "tags": ["tokushoho", "required-disclosure", "regulatory"],
                "source_section": "tokushoho_disclosures",
                "regulation_reference": "特定商取引法 第11条",
            }
        )

    return rules


def _deduplicate_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate rules based on statement text.

    Args:
        rules: List of candidate rule dicts.

    Returns:
        Deduplicated list.
    """
    seen_statements: set[str] = set()
    unique: list[dict[str, Any]] = []
    for rule in rules:
        stmt = rule["statement"]
        if stmt not in seen_statements:
            seen_statements.add(stmt)
            unique.append(rule)
    return unique


class RegulatoryAdvertisingExtractor:
    """Extractor for Japanese advertising regulation documents.

    Supports extraction from documents related to:
    - 薬機法 (yakukiho): Pharmaceutical and Medical Device Act
    - 景品表示法 (keihin_hyoji): Act against Unjustifiable Premiums
    - 特定商取引法 (tokushoho): Specified Commercial Transactions Act
    - JARO guidelines
    """

    @property
    def name(self) -> str:
        return "regulatory_advertising_extractor"

    @property
    def domain(self) -> str:
        return "marketing"

    @property
    def supported_source_types(self) -> list[str]:
        return [
            "advertising_regulation",
            "yakukiho",
            "keihin_hyoji",
            "jaro_guidelines",
        ]

    async def extract(
        self,
        content: bytes,
        source_type: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract regulatory advertising rules from document content.

        Args:
            content: The regulation document as bytes.
            source_type: One of the supported source types.
            metadata: Optional metadata (e.g., regulation version, date).

        Returns:
            List of candidate rule dicts with severity=CRITICAL for
            regulatory violations.
        """
        text = content.decode("utf-8", errors="replace")

        logger.info(
            "regulatory_advertising_extraction_started",
            source_type=source_type,
            content_length=len(text),
        )

        candidates: list[dict[str, Any]] = []

        if source_type in ("advertising_regulation", "yakukiho"):
            candidates.extend(_find_yakukiho_violations(text))

        if source_type in ("advertising_regulation", "keihin_hyoji"):
            candidates.extend(_find_keihyoho_violations(text))

        if source_type in ("advertising_regulation", "jaro_guidelines"):
            # JARO guidelines overlap with both keihyoho and tokushoho
            candidates.extend(_find_keihyoho_violations(text))
            candidates.extend(_find_tokushoho_requirements(text))

        # For generic advertising_regulation, include all
        if source_type == "advertising_regulation":
            candidates.extend(_find_tokushoho_requirements(text))

        # Deduplicate
        candidates = _deduplicate_rules(candidates)

        # Enrich with metadata
        for candidate in candidates:
            candidate["extraction_source"] = source_type
            candidate["extraction_metadata"] = metadata

        logger.info(
            "regulatory_advertising_extraction_complete",
            total_candidates=len(candidates),
            source_type=source_type,
        )

        return candidates
