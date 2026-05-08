"""Contract corpus mining analyzer — extracts de facto standard clauses.

Analyzes a body of historical contracts to identify high-frequency clause
patterns and draft candidate standard-clause rules.

See: CLAUDE.md §16.4, IMPROVEMENT.md §4.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.discovery.analyzers.base import (
    DiscoveryContext,
    RawPattern,
    SourceAnalyzer,
)
from rulerepo_server.services.extraction.contract.clause_classifier import (
    classify_all,
)
from rulerepo_server.services.extraction.contract.clause_segmenter import (
    Clause,
    segment_contract,
)

logger = get_logger(__name__)

# Minimum number of contracts to perform corpus analysis
_MIN_CONTRACTS = 3
# Minimum frequency (proportion of contracts) for a clause type to be "standard"
_MIN_FREQUENCY = 0.5
# Minimum similarity threshold for clause clustering
_CLUSTER_SIMILARITY = 0.4


@dataclass
class ClauseCluster:
    """A cluster of similar clauses from multiple contracts.

    Attributes:
        clause_type: The classified clause type.
        representative: The most common/central clause text.
        members: All clause texts in this cluster.
        frequency: Proportion of contracts containing this clause type.
        contract_count: Number of contracts with this clause type.
    """

    clause_type: str
    representative: str = ""
    members: list[str] = field(default_factory=list)
    frequency: float = 0.0
    contract_count: int = 0


class ContractCorpusAnalyzer(SourceAnalyzer):
    """Analyzes historical contracts to extract de facto standard clauses.

    Use case: a Legal team has many historical contracts but no codified
    standard. This analyzer:
    1. Segments each contract into clauses.
    2. Classifies clauses by type.
    3. Clusters similar clauses across contracts.
    4. Identifies high-frequency patterns as candidate standards.
    5. Drafts candidate rules for Legal reviewer approval.
    """

    async def analyze(self, context: DiscoveryContext) -> list[RawPattern]:
        """Analyze contract texts in the discovery context.

        Expects file_contents to contain contract texts (one per entry).
        Files should be named with .txt, .md, or have 'contract' in the path.

        Args:
            context: Discovery context with file_contents.

        Returns:
            List of RawPattern candidates representing standard clauses.
        """
        contract_texts = _select_contract_files(context)
        if len(contract_texts) < _MIN_CONTRACTS:
            logger.info(
                "contract_corpus_insufficient",
                contracts_found=len(contract_texts),
                minimum_required=_MIN_CONTRACTS,
            )
            return []

        # Segment and classify all contracts
        all_clauses_by_contract: list[list[tuple[Clause, str]]] = []
        for text in contract_texts:
            doc = segment_contract(text)
            if doc.clause_count == 0:
                continue
            classified = classify_all(doc.clauses)
            pairs = [(cc.clause, cc.clause_type) for cc in classified]
            all_clauses_by_contract.append(pairs)

        if not all_clauses_by_contract:
            return []

        # Cluster by clause type
        clusters = _cluster_by_type(all_clauses_by_contract, len(contract_texts))

        # Generate patterns from frequent clusters
        patterns: list[RawPattern] = []
        for cluster in clusters:
            if cluster.frequency < _MIN_FREQUENCY:
                continue

            statement = (
                f"Standard {cluster.clause_type} clause: contracts MUST include "
                f"a {cluster.clause_type} clause consistent with the organization's "
                f"standard. Reference text: {cluster.representative[:200]}"
            )

            patterns.append(
                RawPattern(
                    statement=statement,
                    modality="MUST",
                    severity="MEDIUM",
                    scope=f"legal/contracts/{cluster.clause_type}",
                    tags=["contract_corpus", "standard_clause", cluster.clause_type],
                    source_type="contract_corpus",
                    source_evidence=(
                        f"Found in {cluster.contract_count}/{len(contract_texts)} "
                        f"contracts ({cluster.frequency:.0%} frequency)"
                    ),
                    confidence=min(cluster.frequency * 0.9, 0.85),
                )
            )

        logger.info(
            "contract_corpus_analyzed",
            contracts=len(contract_texts),
            clusters=len(clusters),
            patterns=len(patterns),
        )
        return patterns


def _select_contract_files(context: DiscoveryContext) -> list[str]:
    """Select files likely to be contracts from the discovery context."""
    texts: list[str] = []
    for path, content in context.file_contents.items():
        lower_path = path.lower()
        if any(kw in lower_path for kw in ("contract", "agreement", "nda", "msa", "sow", "keiyaku", "契約")):
            texts.append(content)
        elif lower_path.endswith((".txt", ".md")) and len(content) > 500:
            # Heuristic: check if content looks like a contract
            lower_content = content[:500].lower()
            if any(kw in lower_content for kw in ("agreement", "parties", "hereby", "whereas", "第1条", "甲", "乙")):
                texts.append(content)
    return texts


def _cluster_by_type(
    contracts: list[list[tuple[Clause, str]]],
    total_contracts: int,
) -> list[ClauseCluster]:
    """Cluster clauses by type across contracts."""
    # Group all clauses by type
    type_clauses: dict[str, list[str]] = {}
    type_contracts: dict[str, set[int]] = {}

    for contract_idx, clause_pairs in enumerate(contracts):
        for clause, clause_type in clause_pairs:
            if clause_type == "general":
                continue
            type_clauses.setdefault(clause_type, []).append(clause.text)
            type_contracts.setdefault(clause_type, set()).add(contract_idx)

    clusters: list[ClauseCluster] = []
    for clause_type, texts in type_clauses.items():
        contract_count = len(type_contracts.get(clause_type, set()))
        frequency = contract_count / max(total_contracts, 1)

        # Find the most representative text (closest to centroid by similarity)
        representative = _find_representative(texts)

        clusters.append(
            ClauseCluster(
                clause_type=clause_type,
                representative=representative,
                members=texts,
                frequency=frequency,
                contract_count=contract_count,
            )
        )

    return sorted(clusters, key=lambda c: c.frequency, reverse=True)


def _find_representative(texts: list[str]) -> str:
    """Find the most representative text (highest average similarity to others)."""
    if not texts:
        return ""
    if len(texts) == 1:
        return texts[0]

    best_text = texts[0]
    best_score = 0.0

    for candidate in texts[:10]:  # Cap computation for large corpora
        total_sim = sum(
            SequenceMatcher(None, candidate.lower(), other.lower()).ratio() for other in texts if other != candidate
        )
        avg_sim = total_sim / (len(texts) - 1)
        if avg_sim > best_score:
            best_score = avg_sim
            best_text = candidate

    return best_text
