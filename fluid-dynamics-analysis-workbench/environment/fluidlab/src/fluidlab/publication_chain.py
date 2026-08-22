from __future__ import annotations

import hashlib

from .lineage_digest import operating_point_keys


def publication_revision(case_results: list[dict[str, object]]) -> str:
  digest = hashlib.sha256()
  for case in case_results:
    digest.update(str(case["case_id"]).encode("utf-8"))
    digest.update(str(case["source_digest"]).encode("utf-8"))
    digest.update(str(case["status"]).encode("utf-8"))
  return digest.hexdigest()[:20]


def extended_revision(case_results: list[dict[str, object]]) -> str:
  digest = hashlib.sha256()
  digest.update(publication_revision(case_results).encode("utf-8"))
  digest.update(str(operating_point_keys(case_results)).encode("utf-8"))
  return digest.hexdigest()[:24]


def artifact_chain_digest(artifact_paths: list[str]) -> str:
  digest = hashlib.sha256()
  for path in sorted(artifact_paths):
    digest.update(path.encode("utf-8"))
  return digest.hexdigest()[:16]
