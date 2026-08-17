from __future__ import annotations

from src.paths import WAREHOUSE_DIR

CATALOG_FILENAME = "catalog.sqlite"
CATALOG_PATH = WAREHOUSE_DIR / CATALOG_FILENAME
PRIMARY_TABLE = "click_event"
TENANT_TABLE = "tenant"
USER_TABLE = "click_user"
BATCH_TABLE = "ingest_batch"
RUN_TABLE = "processor_run"

REQUIRED_EVENT_COLUMNS = (
    "event_id",
    "tenant_id",
    "user_id",
    "event_time_ms",
    "payload",
    "channel",
    "kind",
    "page",
    "device",
    "country",
    "ingest_batch_id",
)

INVENTORY_QUERIES = {
    "event_count": f'SELECT COUNT(*) FROM "{PRIMARY_TABLE}"',
    "tenant_count": f'SELECT COUNT(*) FROM "{TENANT_TABLE}"',
    "user_count": f'SELECT COUNT(*) FROM "{USER_TABLE}"',
    "batch_count": f'SELECT COUNT(*) FROM "{BATCH_TABLE}"',
    "kind_count": f'SELECT COUNT(DISTINCT kind) FROM "{PRIMARY_TABLE}"',
    "channel_count": f'SELECT COUNT(DISTINCT channel) FROM "{PRIMARY_TABLE}"',
    "device_count": f'SELECT COUNT(DISTINCT device) FROM "{PRIMARY_TABLE}"',
    "country_count": f'SELECT COUNT(DISTINCT country) FROM "{PRIMARY_TABLE}"',
    "page_count": f'SELECT COUNT(DISTINCT page) FROM "{PRIMARY_TABLE}"',
    "min_event_time_ms": f'SELECT MIN(event_time_ms) FROM "{PRIMARY_TABLE}"',
    "max_event_time_ms": f'SELECT MAX(event_time_ms) FROM "{PRIMARY_TABLE}"',
}
