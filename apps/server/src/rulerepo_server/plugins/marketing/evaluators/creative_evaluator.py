"""Creative compliance evaluator for marketing plugin.

Performs deterministic (non-LLM) checks on marketing creative content
including prohibited phrases, required disclaimers, superlative claims,
competitor mentions, price/discount validation, and contact information
completeness.

See: CLAUDE.md SS14.6
"""

from __future__ import annotations

import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Default prohibited phrases (configurable via constructor)
_DEFAULT_PROHIBITED_PHRASES: list[str] = [
    "絶対",
    "完全",
    "永久",
    "万能",
    "奇跡",
    "魔法",
    "確実に",
    "必ず",
    "100%効果",
    "副作用なし",
    "リスクゼロ",
    "guaranteed",
    "miracle",
    "magic",
]

# Superlative expressions requiring evidence
_SUPERLATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"最高[級品質]?"),
    re.compile(r"No\.?\s*1|ナンバーワン"),
    re.compile(r"業界初|世界初|日本初"),
    re.compile(r"世界一|日本一|業界一"),
    re.compile(r"唯一の|オンリーワン"),
    re.compile(r"最安[値]?"),
    re.compile(r"最速"),
    re.compile(r"最先端"),
    re.compile(r"圧倒的"),
    re.compile(r"ダントツ"),
    re.compile(r"他社を凌駕"),
    re.compile(r"best\s+in\s+class", re.IGNORECASE),
    re.compile(r"#\s*1|number\s*one", re.IGNORECASE),
    re.compile(r"industry[\s-]*first", re.IGNORECASE),
]

# Required disclaimers by content type
_REQUIRED_DISCLAIMERS: dict[str, list[str]] = {
    "health": [
        "効果には個人差があります",
        "個人の感想です",
    ],
    "beauty": [
        "効果には個人差があります",
        "個人の感想です",
    ],
    "financial": [
        "投資にはリスクが伴います",
        "元本保証はありません",
        "過去の実績は将来の成果を保証するものではありません",
    ],
    "supplement": [
        "効果には個人差があります",
        "本品は、特定保健用食品と異なり",
        "食生活は、主食、主菜、副菜を基本に",
    ],
    "insurance": [
        "保険料は年齢・性別等により異なります",
        "詳しくは契約概要をご確認ください",
    ],
    "real_estate": [
        "物件の詳細は現地にてご確認ください",
        "価格は変更になる場合があります",
    ],
}

# Evidence citation patterns (to verify superlative claims have backing)
_EVIDENCE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(出典|出所|調査|データ|エビデンス)[:\uff1a]"),
    re.compile(r"\d{4}年.*?(調査|データ|レポート)"),
    re.compile(r"(※|\uff0a)\s*\d{4}年"),
    re.compile(r"(source|survey|study|data)[:\uff1a]", re.IGNORECASE),
]

# Price/discount patterns that need conditions
_PRICE_DISCOUNT_PATTERN = re.compile(
    r"(\d+%\s*(?:OFF|オフ|割引)|半額|無料|0円|タダ|"
    r"通常価格.*?(?:→|⇒|から)\s*\d+|今だけ|期間限定|本日限り)"
)

# Condition patterns that accompany price claims
_PRICE_CONDITION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(条件|適用条件|対象)[:\uff1a]"),
    re.compile(r"(\d{4}年\d{1,2}月\d{1,2}日|〜|まで|から)"),
    re.compile(r"(※|\uff0a).*(条件|期間|対象)"),
    re.compile(r"(valid\s+until|expires|conditions\s+apply)", re.IGNORECASE),
]

# Contact information fields required for specific ad types
_REQUIRED_CONTACT_FIELDS: list[str] = [
    "電話番号",
    "メールアドレス",
    "所在地",
    "会社名",
    "販売業者",
]

# Ad types requiring contact info
_CONTACT_REQUIRED_AD_TYPES: set[str] = {
    "direct_response",
    "e_commerce",
    "mail_order",
    "通販",
    "EC",
    "ダイレクトレスポンス",
}


def _check_prohibited_phrases(
    text: str,
    prohibited: list[str],
) -> list[dict[str, Any]]:
    """Check for prohibited phrases in content.

    Args:
        text: Content text to check.
        prohibited: List of prohibited phrases/words.

    Returns:
        List of verdict dicts for violations found.
    """
    verdicts: list[dict[str, Any]] = []
    text_lower = text.lower()

    for phrase in prohibited:
        if phrase.lower() in text_lower:
            verdicts.append(
                {
                    "check": "prohibited_phrase",
                    "verdict": "DENY",
                    "confidence": 0.95,
                    "severity": "HIGH",
                    "reasoning": f"禁止表現 '{phrase}' が検出されました",
                    "remediation": {
                        "kind": "text_rewrite",
                        "description": f"'{phrase}' を削除または言い換えてください",
                        "auto_applicable": False,
                        "payload": {"prohibited_phrase": phrase},
                    },
                }
            )

    return verdicts


def _check_required_disclaimers(
    text: str,
    content_type: str,
) -> list[dict[str, Any]]:
    """Check for required disclaimers based on content type.

    Args:
        text: Content text to check.
        content_type: Type of marketing content.

    Returns:
        List of verdict dicts for missing disclaimers.
    """
    verdicts: list[dict[str, Any]] = []
    required = _REQUIRED_DISCLAIMERS.get(content_type, [])

    for disclaimer in required:
        if disclaimer not in text:
            verdicts.append(
                {
                    "check": "missing_disclaimer",
                    "verdict": "DENY",
                    "confidence": 0.9,
                    "severity": "HIGH",
                    "reasoning": (f"コンテンツタイプ '{content_type}' には 免責事項 '{disclaimer}' が必須です"),
                    "remediation": {
                        "kind": "text_rewrite",
                        "description": f"以下の免責事項を追加してください: '{disclaimer}'",
                        "auto_applicable": True,
                        "payload": {
                            "action": "add_disclaimer",
                            "disclaimer_text": disclaimer,
                        },
                    },
                }
            )

    return verdicts


def _check_superlative_claims(text: str) -> list[dict[str, Any]]:
    """Check for superlative claims without evidence citation.

    Args:
        text: Content text to check.

    Returns:
        List of verdict dicts for unsupported superlatives.
    """
    verdicts: list[dict[str, Any]] = []

    has_evidence = any(p.search(text) for p in _EVIDENCE_PATTERNS)

    for pattern in _SUPERLATIVE_PATTERNS:
        matches = pattern.findall(text)
        for match_text in matches:
            if not has_evidence:
                verdicts.append(
                    {
                        "check": "superlative_without_evidence",
                        "verdict": "DENY",
                        "confidence": 0.85,
                        "severity": "CRITICAL",
                        "reasoning": (
                            f"最上級表現 '{match_text}' に客観的根拠の引用がありません(景品表示法 優良誤認のおそれ)"
                        ),
                        "remediation": {
                            "kind": "text_rewrite",
                            "description": (f"'{match_text}' に根拠データの出典を追加するか、表現を修正してください"),
                            "auto_applicable": False,
                            "payload": {
                                "action": "add_evidence_or_rephrase",
                                "claim_text": match_text,
                            },
                        },
                    }
                )

    return verdicts


def _check_competitor_mentions(
    text: str,
    competitors: list[str],
) -> list[dict[str, Any]]:
    """Check for competitor name mentions.

    Args:
        text: Content text to check.
        competitors: List of competitor names to flag.

    Returns:
        List of verdict dicts for competitor mentions.
    """
    verdicts: list[dict[str, Any]] = []

    for competitor in competitors:
        if competitor.lower() in text.lower():
            verdicts.append(
                {
                    "check": "competitor_mention",
                    "verdict": "DENY",
                    "confidence": 0.9,
                    "severity": "HIGH",
                    "reasoning": (f"競合他社名 '{competitor}' への言及が検出されました"),
                    "remediation": {
                        "kind": "text_rewrite",
                        "description": (f"競合他社 '{competitor}' への言及を削除してください"),
                        "auto_applicable": False,
                        "payload": {
                            "action": "remove_competitor_mention",
                            "competitor_name": competitor,
                        },
                    },
                }
            )

    return verdicts


def _check_price_claims(text: str) -> list[dict[str, Any]]:
    """Validate price/discount claims include conditions and period.

    Args:
        text: Content text to check.

    Returns:
        List of verdict dicts for invalid price claims.
    """
    verdicts: list[dict[str, Any]] = []

    price_matches = _PRICE_DISCOUNT_PATTERN.findall(text)
    if not price_matches:
        return verdicts

    has_conditions = any(p.search(text) for p in _PRICE_CONDITION_PATTERNS)

    if not has_conditions:
        for match_text in price_matches:
            verdicts.append(
                {
                    "check": "price_missing_conditions",
                    "verdict": "DENY",
                    "confidence": 0.85,
                    "severity": "HIGH",
                    "reasoning": (f"価格表示 '{match_text}' に条件・期間の記載がありません"),
                    "remediation": {
                        "kind": "text_rewrite",
                        "description": (f"'{match_text}' に適用条件と有効期間を追加してください"),
                        "auto_applicable": False,
                        "payload": {
                            "action": "add_price_conditions",
                            "price_claim": match_text,
                        },
                    },
                }
            )

    return verdicts


def _check_contact_info(
    text: str,
    content_type: str,
) -> list[dict[str, Any]]:
    """Check contact information completeness for specific ad types.

    Args:
        text: Content text to check.
        content_type: Type of marketing content.

    Returns:
        List of verdict dicts for missing contact info.
    """
    verdicts: list[dict[str, Any]] = []

    if content_type not in _CONTACT_REQUIRED_AD_TYPES:
        return verdicts

    missing_fields: list[str] = []
    for field in _REQUIRED_CONTACT_FIELDS:
        if field not in text:
            missing_fields.append(field)

    if missing_fields:
        verdicts.append(
            {
                "check": "missing_contact_info",
                "verdict": "DENY",
                "confidence": 0.9,
                "severity": "HIGH",
                "reasoning": (f"通信販売広告に必要な表示項目が不足しています: {', '.join(missing_fields)}"),
                "remediation": {
                    "kind": "text_rewrite",
                    "description": (f"以下の情報を追加してください: {', '.join(missing_fields)}"),
                    "auto_applicable": False,
                    "payload": {
                        "action": "add_contact_fields",
                        "missing_fields": missing_fields,
                    },
                },
            }
        )

    return verdicts


class CreativeComplianceEvaluator:
    """Deterministic compliance evaluator for marketing creatives.

    Performs rule-based (non-LLM) checks on marketing content including:
    - Prohibited phrase detection
    - Required disclaimer presence
    - Superlative claim detection without evidence
    - Competitor name mention detection
    - Price/discount claim validation
    - Contact information completeness

    Args:
        prohibited_phrases: Custom list of prohibited phrases.
            Defaults to a standard Japanese marketing blacklist.
        competitors: List of competitor names to flag.
        additional_disclaimers: Extra disclaimer requirements by
            content type.
    """

    def __init__(
        self,
        prohibited_phrases: list[str] | None = None,
        competitors: list[str] | None = None,
        additional_disclaimers: dict[str, list[str]] | None = None,
    ) -> None:
        self._prohibited_phrases = prohibited_phrases or _DEFAULT_PROHIBITED_PHRASES
        self._competitors = competitors or []
        self._additional_disclaimers = additional_disclaimers or {}

    @property
    def name(self) -> str:
        return "creative_compliance_evaluator"

    @property
    def domain(self) -> str:
        return "marketing"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["creative", "document"]

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate marketing content with deterministic compliance checks.

        Args:
            subject_payload: Marketing content data containing at
                minimum 'body_text' or 'content'. May also include
                'content_type', 'headline', 'claims'.
            rules: List of rule dicts (used for prohibited phrases and
                competitor lists from rule metadata).
            context: Additional context (competitors, content_type override).

        Returns:
            List of verdict dicts with text_rewrite remediations.
        """
        # Build full text from payload
        text_parts: list[str] = []
        if "headline" in subject_payload:
            text_parts.append(subject_payload["headline"])
        if "body_text" in subject_payload:
            text_parts.append(subject_payload["body_text"])
        elif "content" in subject_payload:
            text_parts.append(subject_payload["content"])
        if "claims" in subject_payload and isinstance(subject_payload["claims"], list):
            text_parts.extend(subject_payload["claims"])
        if "cta" in subject_payload:
            text_parts.append(subject_payload["cta"])

        full_text = "\n".join(text_parts)

        if not full_text.strip():
            logger.warning("creative_evaluator_empty_content")
            return []

        content_type = subject_payload.get("content_type") or context.get("content_type", "general")

        # Gather competitor names from rules + context + config
        competitors = list(self._competitors)
        if "competitors" in context:
            competitors.extend(context["competitors"])

        logger.info(
            "creative_compliance_evaluation_started",
            content_type=content_type,
            text_length=len(full_text),
            rule_count=len(rules),
        )

        # Run all deterministic checks
        verdicts: list[dict[str, Any]] = []

        verdicts.extend(_check_prohibited_phrases(full_text, self._prohibited_phrases))
        verdicts.extend(_check_required_disclaimers(full_text, content_type))
        verdicts.extend(_check_superlative_claims(full_text))
        if competitors:
            verdicts.extend(_check_competitor_mentions(full_text, competitors))
        verdicts.extend(_check_price_claims(full_text))
        verdicts.extend(_check_contact_info(full_text, content_type))

        logger.info(
            "creative_compliance_evaluation_complete",
            content_type=content_type,
            violation_count=len(verdicts),
        )

        return verdicts
