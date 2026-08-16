"""Normalize shell/script line endings and report substantive Python LOC."""

import sys
from pathlib import Path

TASK = Path(__file__).resolve().parent.parent / "codecommit-iam-merge-fence"


def to_lf(path: Path) -> bool:
    raw = path.read_bytes()
    fixed = raw.replace(b"\r\n", b"\n")
    if fixed != raw:
        path.write_bytes(fixed)
        return True
    return False


def substantive(path: Path) -> int:
    total = 0
    in_doc = False
    marker = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if in_doc:
            total += 1
            if marker in text:
                in_doc = False
            continue
        if not text:
            continue
        if text.startswith("#"):
            continue
        for candidate in ('"""', "'''"):
            if text.startswith(candidate):
                marker = candidate
                if not (text.endswith(candidate) and len(text) > 5):
                    in_doc = True
                break
        total += 1
    return total


if __name__ == "__main__":
    changed = []
    for pattern in ("**/*.sh", "environment/codecommit/bin/*"):
        for path in sorted(TASK.glob(pattern)):
            if path.is_file() and to_lf(path):
                changed.append(str(path.relative_to(TASK)))
    env_files = [
        path
        for path in sorted((TASK / "environment").rglob("*.py"))
        if "__pycache__" not in path.parts
    ]
    bins = [
        TASK / "environment" / "codecommit" / "bin" / "ccctl",
        TASK / "environment" / "codecommit" / "bin" / "cc-api",
    ]
    env_loc = sum(substantive(path) for path in env_files + bins)
    fixed_files = sorted((TASK / "solution" / "fixed").rglob("*.py"))
    test_loc = substantive(TASK / "tests" / "test_outputs.py")
    sys.stdout.write(f"normalized: {changed}\n")
    sys.stdout.write(f"environment python modules: {len(env_files) + len(bins)}\n")
    sys.stdout.write(f"environment substantive LOC: {env_loc}\n")
    sys.stdout.write(f"fixed modules: {len(fixed_files)}\n")
    sys.stdout.write(
        f"fixed substantive LOC: {sum(substantive(p) for p in fixed_files)}\n"
    )
    sys.stdout.write(f"verifier substantive LOC: {test_loc}\n")
