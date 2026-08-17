from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile

from .models import ReconciliationResult


def hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(generation_id: str, files: dict[str, Path]) -> dict:
    return {
        "generation_id": generation_id,
        "files": {
            name: {
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": hash_file(path),
            }
            for name, path in sorted(files.items())
        },
    }


def verify_publication(path: str | Path) -> bool:
    path = Path(path)
    try:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        files = manifest["files"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False
    if not isinstance(files, dict):
        return False
    for metadata in files.values():
        try:
            file_path = path / metadata["name"]
            expected_size = metadata["size"]
            expected_sha = metadata["sha256"]
        except (KeyError, TypeError):
            return False
        if (
            not file_path.exists()
            or file_path.stat().st_size != expected_size
            or hash_file(file_path) != expected_sha
        ):
            return False
    return True


def atomic_publish(
    generation_id: str,
    files: dict[str, Path],
    reconciliation: ReconciliationResult,
    destination: str | Path,
) -> Path:
    if not reconciliation.passed:
        raise ValueError("cannot publish failed reconciliation")

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / generation_id
    if target.exists():
        existing = target / "manifest.json"
        if not existing.exists():
            raise ValueError("existing publication missing manifest")
        try:
            manifest = json.loads(existing.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("existing publication manifest is invalid") from exc
        if manifest.get("generation_id") != generation_id:
            raise ValueError("publication generation mismatch")
        if not verify_publication(target):
            raise ValueError("existing publication failed integrity verification")
        return target

    staging = Path(tempfile.mkdtemp(prefix=f".{generation_id}.", dir=destination))
    try:
        copied: dict[str, Path] = {}
        for name, source in files.items():
            copied_path = staging / source.name
            shutil.copy2(source, copied_path)
            copied[name] = copied_path
        manifest = build_manifest(generation_id, copied)
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, target)
        return target
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
