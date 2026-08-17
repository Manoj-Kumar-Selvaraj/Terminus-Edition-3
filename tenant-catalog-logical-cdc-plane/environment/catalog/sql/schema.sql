CREATE TABLE IF NOT EXISTS row_version (
    table_name TEXT NOT NULL,
    pk TEXT NOT NULL,
    xmin INTEGER NOT NULL,
    xmax INTEGER,
    committed INTEGER NOT NULL,
    lsn INTEGER NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS txn_reg (
    txn_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tenant_meta (
    tenant_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    plan TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sku_meta (
    sku_id TEXT PRIMARY KEY,
    category TEXT NOT NULL
);
