import os
import sys

BASE = r"D:\Manoj\Projects\Portfolio\TerminalBench\Terminus-Edition-3"
os.environ["CC_ROOT"] = BASE + r"\.smoke\cc"
sys.path.insert(0, BASE + r"\codecommit-iam-merge-fence\environment\codecommit\lib")

from cc.api.app import handle

print("health", handle("GET", "/api/v1/health"))
print("repos", handle("GET", "/api/v1/repos", {"X-Cc-Principal": "intern"})[0])
print(
    "deliver-ghost",
    handle("POST", "/api/v1/pipelines/deliver", {"X-Cc-Principal": "ghost"}, {"repo": "ledger", "ref": "main"}),
)
print(
    "audit",
    handle(
        "GET",
        "/api/v1/audit?principal=rev-a&decision=allow",
        {"X-Cc-Principal": "audit-ro", "X-Cc-Source-Ip": "10.8.12.4"},
    )[0],
)
print("missing-route", handle("GET", "/api/v1/nope"))
print("bad-method", handle("PUT", "/api/v1/health"))
print(
    "outbox",
    handle("GET", "/api/v1/webhooks/outbox", {"X-Cc-Principal": "pipeline-bot", "X-Cc-Source-Ip": "10.8.12.4"})[0],
)
print(
    "refs",
    handle(
        "GET",
        "/api/v1/repos/ledger/refs",
        {"X-Cc-Principal": "intern", "X-Cc-Source-Ip": "10.8.12.4"},
    ),
)
