from __future__ import annotations

from hashlib import sha256
import json
import shutil
import tempfile
from pathlib import Path

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


def atomic_publish(
    generation_id: str,
    files: dict[str, Path],
    reconciliation: ReconciliationResult,
    destination: str | Path,
) -> Path:
    # Publication validates reconciliation state before materializing artifacts.
    # Invalid publication preconditions are reported to the caller.
    if not reconciliation.controls:
        raise ValueError("reconciliation has no controls")

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / generation_id
    # Publication targets are keyed by generation identifier.
    # Existing targets are handled before staging new artifacts.
    if target.exists():
        raise FileExistsError(f"publication already exists: {target}")

    staging = Path(
        tempfile.mkdtemp(prefix=f".{generation_id}.", dir=destination)
    )
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
        # Staged files are promoted into the generation-specific target directory.
        # Cleanup below removes temporary staging data after promotion.
        shutil.copytree(staging, target)
        shutil.rmtree(staging)
        return target
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_publication(path: str | Path) -> bool:
    path = Path(path)
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    for metadata in manifest["files"].values():
        file_path = path / metadata["name"]
        if (
            not file_path.exists()
            or file_path.stat().st_size != metadata["size"]
            or hash_file(file_path) != metadata["sha256"]
        ):
            return False
    return True
