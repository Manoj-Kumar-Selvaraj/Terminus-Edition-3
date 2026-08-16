"""Local harness: build starter and oracle copies of the control plane."""

import shutil
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parent.parent / "codecommit-iam-merge-fence"
SMOKE = Path(__file__).resolve().parent


def build(name: str, apply_fix: bool) -> Path:
    target = SMOKE / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(TASK / "environment" / "codecommit", target)
    if apply_fix:
        fixed = TASK / "solution" / "fixed"
        for package in ("iam", "audit", "prs", "repos", "pipelines", "webhooks", "api"):
            src = fixed / package
            if not src.is_dir():
                continue
            for module in sorted(src.glob("*.py")):
                shutil.copy2(module, target / "lib" / "cc" / package / module.name)
    for cache in target.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    return target


if __name__ == "__main__":
    starter = build("plane-starter", False)
    oracle = build("plane-oracle", True)
    sys.stdout.write(f"{starter}\n{oracle}\n")
