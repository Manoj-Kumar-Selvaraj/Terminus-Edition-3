"""Phrase-contamination checks for solver-visible instruction drafts."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Iterable


def analyze_contamination(
    draft: str,
    references: Iterable[dict[str, str]],
    *,
    token_ngram: int = 5,
    ngram_containment_threshold: float = 0.32,
    sequence_threshold: float = 0.68,
    window_sequence_threshold: float = 0.58,
    longest_match_threshold: float = 0.34,
    minimum_contiguous_tokens: int = 10,
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
        containment = _containment(draft_ngrams, ref_ngrams)
        sequence = SequenceMatcher(None, draft_tokens, ref_tokens, autojunk=False).ratio()
        matcher = SequenceMatcher(None, draft_tokens, ref_tokens, autojunk=False)
        longest = matcher.find_longest_match(0, len(draft_tokens), 0, len(ref_tokens)).size
        denominator = min(len(draft_tokens), len(ref_tokens)) or 1
        longest_ratio = longest / denominator
        window_sequence = _max_window_sequence(draft_tokens, ref_tokens)
        material_longest = (
            longest >= minimum_contiguous_tokens
            and longest_ratio >= longest_match_threshold
        )
        if (
            containment >= ngram_containment_threshold
            or sequence >= sequence_threshold
            or window_sequence >= window_sequence_threshold
            or material_longest
        ):
            findings.append(
                {
                    "source_key": ref.get("source_key", "unknown"),
                    "ngram_containment": round(containment, 6),
                    "whole_sequence_ratio": round(sequence, 6),
                    "window_sequence_ratio": round(window_sequence, 6),
                    "longest_contiguous_tokens": longest,
                    "longest_contiguous_ratio": round(longest_ratio, 6),
                }
            )
    findings.sort(
        key=lambda item: (
            -max(
                item["ngram_containment"],
                item["whole_sequence_ratio"],
                item["window_sequence_ratio"],
                item["longest_contiguous_ratio"],
            ),
            item["source_key"],
        )
    )
    return {
        "status": "REWRITE_REQUIRED" if findings else "PASS",
        "finding_count": len(findings),
        "findings": findings,
        "thresholds": {
            "token_ngram": token_ngram,
            "ngram_containment": ngram_containment_threshold,
            "whole_sequence": sequence_threshold,
            "window_sequence": window_sequence_threshold,
            "longest_match": longest_match_threshold,
            "minimum_contiguous_tokens": minimum_contiguous_tokens,
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


def _containment(
    left: set[tuple[str, ...]], right: set[tuple[str, ...]]
) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _max_window_sequence(draft_tokens: list[str], ref_tokens: list[str]) -> float:
    if not draft_tokens or not ref_tokens:
        return 0.0
    if len(ref_tokens) <= len(draft_tokens):
        return SequenceMatcher(None, draft_tokens, ref_tokens, autojunk=False).ratio()
    width = len(draft_tokens)
    stride = max(1, width // 4)
    starts = list(range(0, max(1, len(ref_tokens) - width + 1), stride))
    final_start = len(ref_tokens) - width
    if final_start not in starts:
        starts.append(final_start)
    return max(
        SequenceMatcher(
            None,
            draft_tokens,
            ref_tokens[start : start + width],
            autojunk=False,
        ).ratio()
        for start in starts
    )
