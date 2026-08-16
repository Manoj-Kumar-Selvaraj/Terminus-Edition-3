# django-checkout-failover-ha

Shopdesk checkout after a messy writer cutover. The lab keeps two SQLite shop files plus a Django cache alias for sticky reads. The agent makes place/pay/reload and `/readyz` match one fenced writer.

Tree root: `/app/ha`.

Agent image uses the canonical `python:3.13-slim-bookworm` digest from Edition 3 instructions (Django/pytest via pip; `tmux`/`asciinema`/`sqlite3` from apt).
