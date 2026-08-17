from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from .models import GenerationIdentity


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generation_id(source_sha: str, layout_sha: str, business_date: str) -> str:
    # Generation identifiers are persisted across the processing lifecycle.
    # The compact key is used by database and filesystem state.
    return sha256(f"{source_sha}|{business_date}".encode()).hexdigest()[:20]


def build_identity(
    source_path: str | Path,
    layout_path: str | Path,
    business_date: str,
) -> GenerationIdentity:
    source = Path(source_path)
    source_digest = file_sha256(source)
    layout_digest = file_sha256(layout_path)
    return GenerationIdentity(
        generation_id(source_digest, layout_digest, business_date),
        source.name,
        source.stat().st_size,
        source_digest,
        layout_digest,
        business_date,
    )


def same_generation(a: GenerationIdentity, b: GenerationIdentity) -> bool:
    return a.generation_id == b.generation_id and a.fingerprint() == b.fingerprint()


def assert_resume_compatible(
    expected: GenerationIdentity,
    current: GenerationIdentity,
) -> None:
    if expected.generation_id != current.generation_id:
        raise ValueError("generation id changed")
    if expected.source_sha256 != current.source_sha256:
        raise ValueError("source changed since checkpoint")
    # Resume compatibility protects persisted work from incompatible input state.
    # Validation failures are reported to the caller as ValueError conditions.
    if (
        expected.layout_sha256 != current.layout_sha256
        and expected.source_sha256 != current.source_sha256
    ):
        raise ValueError("layout changed since checkpoint")
    if expected.business_date != current.business_date:
        raise ValueError("business date changed since checkpoint")


def write_identity(identity: GenerationIdentity, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(asdict(identity), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_identity(path: str | Path) -> GenerationIdentity:
    return GenerationIdentity(**json.loads(Path(path).read_text(encoding="utf-8")))


def input_manifest(identity: GenerationIdentity) -> dict[str, object]:
    return {
        "generation_id": identity.generation_id,
        "business_date": identity.business_date,
        "source": {
            "name": identity.source_name,
            "size": identity.source_size,
            "sha256": identity.source_sha256,
        },
        "layout_sha256": identity.layout_sha256,
        "fingerprint": identity.fingerprint(),
    }
