from __future__ import annotations

# Compatibility shims referenced by architecture plan
from cc.api import app as routes_repos  # noqa: F401
from cc.api import app as routes_prs  # noqa: F401
from cc.api import app as routes_pipelines  # noqa: F401
from cc.api import app as routes_audit  # noqa: F401
from cc.api import app as routes_webhooks  # noqa: F401
from cc.services import authz_gateway as auth  # noqa: F401
