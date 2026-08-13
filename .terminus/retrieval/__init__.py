"""Policy-aware local retrieval engine for the Terminus control plane."""

from .embeddings import HashingEmbedder
from .engine import RetrievalEngine
from .indexer import RepositoryIndexer
from .ingestion import DynamicEvidenceIngestor
from .models import InvocationContext, RetrievalQuery, SearchResult
from .policy import RetrievalPolicy
from .store import RetrievalStore

__all__ = [
    "DynamicEvidenceIngestor",
    "HashingEmbedder",
    "InvocationContext",
    "RepositoryIndexer",
    "RetrievalEngine",
    "RetrievalPolicy",
    "RetrievalQuery",
    "RetrievalStore",
    "SearchResult",
]
