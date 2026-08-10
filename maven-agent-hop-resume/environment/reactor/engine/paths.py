from pathlib import Path

ROOT = Path("/app/reactor")
SRC = ROOT / "src"
PIPELINE = SRC / "pipeline.json"
MODULES = SRC / "modules.json"
AGENTS = ROOT / "agents" / "inventory.json"
LIBS = ROOT / "libs"
VAR = ROOT / "var"
JOURNAL = VAR / "journal.json"
FINGERPRINTS = VAR / "fingerprints"
ARCHIVE = VAR / "archive"
WORK = VAR / "work"
CRASH_LOG = ROOT / "log" / "crash.log"

KIND_LABEL = {"scm": "linux", "maven": "maven", "docker": "docker"}
SECRET_SUFFIXES = ("_TOKEN", "_PASSWORD", "_SECRET")
