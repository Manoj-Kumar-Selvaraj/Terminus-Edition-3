"""Phrase-contamination checks for solver-visible instruction drafts."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Iterable


def analyze_contamination(
    draft: str,
    references: Iterable[dict[str, str]],
    *,
    token_ngram: int = 5,
    jaccard_threshold: float = 0.24,
    sequence_threshold: float = 0.68,
) -> dict[str, Any]:
    """Compare a draft against source text without returning copied phrases."""
    draft_tokens = _tokens(draft)
    draft_ngrams = _ngrams(draft_tokens, token_ngram)
    findings: list[dict[str, Any]] = []
    for ref in references:
        text = ref.get("text", "")
        if not text.strip():
            continue
        ref_tokens = _tokens(text)
        ref_ngrams = _ngrams(ref_tokens, token_ngram)
        jaccard = _jaccard(draft_ngrams, ref_ngrams)
        sequence = SequenceMatcher(
            None, " ".join(draft_tokens), " ".join(ref_tokens), autojunk=True
        ).ratio()
        if jaccard >= jaccard_threshold or sequence >= sequence_threshold:
            findings.append(
                {
                    "source_key": ref.get("source_key", "unknown"),
                    "ngram_jaccard": round(jaccard, 6),
                    "sequence_ratio": round(sequence, 6),
                }
            )
    findings.sort(
        key=lambda item: (
            -max(item["ngram_jaccard"], item["sequence_ratio"]),
            item["source_key"],
        )
    )
    return {
        "status": "REWRITE_REQUIRED" if findings else "PASS",
        "finding_count": len(findings),
        "findings": findings,
        "thresholds": {
            "token_ngram": token_ngram,
            "jaccard": jaccard_threshold,
            "sequence": sequence_threshold,
        },
        "note": "Findings report source IDs and scores only; source phrases are not exposed.",
    }


def _tokens(value: str) -> list[str]:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return [token for token in normalized.split() if len(token) >= 2]


def _ngrams(tokens: list[str], size: int) -> set[tuple[str, ...]]:
    if size <= 0 or len(tokens) < size:
        return set()
    return {tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1)}


def _jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
