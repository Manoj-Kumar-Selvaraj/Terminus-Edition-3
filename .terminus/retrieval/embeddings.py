"""Embedding providers used by local vector retrieval."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Protocol, Sequence

_TOKEN = re.compile(r"[A-Za-z0-9_./:-]+")


class EmbeddingProvider(Protocol):
    """Minimal provider interface; implementations may be local or external."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class HashingEmbedder:
    """Dependency-free signed feature hashing for deterministic local vectors.

    This is the default offline vector provider. It is intentionally modest: it
    supplies reproducible vector retrieval without requiring an API key or model
    download. A stronger embedding provider can be plugged in without changing
    authorization, indexing, caching, or ranking contracts.
    """

    def __init__(self, dimensions: int = 384):
        if dimensions < 32:
            raise ValueError("dimensions must be >= 32")
        self.dimensions = dimensions

    @property
    def name(self) -> str:
        return "hashing"

    @property
    def version(self) -> str:
        return f"signed-blake2b-{self.dimensions}-v1"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        counts = Counter(token.lower() for token in _TOKEN.findall(text))
        vector = [0.0] * self.dimensions
        for token, count in counts.items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            weight = 1.0 + math.log(float(count))
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector


class SentenceTransformerEmbedder:
    """Optional local semantic provider when sentence-transformers is installed."""

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "sentence-transformers is not installed; use hashing or install it locally"
            ) from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    @property
    def name(self) -> str:
        return "sentence-transformers"

    @property
    def version(self) -> str:
        return self.model_name

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions differ")
    return float(sum(a * b for a, b in zip(left, right, strict=True)))
