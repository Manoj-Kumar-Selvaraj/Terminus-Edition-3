PRAGMA foreign_keys = ON;

CREATE TABLE catalog_warehouse (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL,
    az_id TEXT NOT NULL,
    status TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE catalog_product (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    active INTEGER NOT NULL,
    fulfillment_class TEXT NOT NULL
);

CREATE TABLE catalog_pricebook (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES catalog_product(id),
    currency TEXT NOT NULL,
    unit_cents INTEGER NOT NULL,
    effective_from TEXT NOT NULL,
    UNIQUE (product_id, currency, effective_from)
);

CREATE TABLE identity_shopper (
    id INTEGER PRIMARY KEY,
    shopper_ref TEXT NOT NULL UNIQUE,
    email_hash TEXT NOT NULL,
    region TEXT NOT NULL,
    loyalty_tier TEXT NOT NULL,
    created_at TEXT NOT NULL,
    risk_band TEXT NOT NULL
);

CREATE TABLE identity_address (
    id INTEGER PRIMARY KEY,
    shopper_id INTEGER NOT NULL REFERENCES identity_shopper(id),
    kind TEXT NOT NULL,
    postal TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE inventory_stocklot (
    id INTEGER PRIMARY KEY,
    warehouse_id INTEGER NOT NULL REFERENCES catalog_warehouse(id),
    product_id INTEGER NOT NULL REFERENCES catalog_product(id),
    lot_code TEXT NOT NULL,
    qty_on_hand INTEGER NOT NULL,
    qty_reserved INTEGER NOT NULL,
    UNIQUE (warehouse_id, product_id, lot_code)
);

CREATE TABLE inventory_reservation (
    id INTEGER PRIMARY KEY,
    stocklot_id INTEGER NOT NULL REFERENCES inventory_stocklot(id),
    attempt_id TEXT NOT NULL,
    qty INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE checkout_cart (
    id INTEGER PRIMARY KEY,
    shopper_id INTEGER NOT NULL REFERENCES identity_shopper(id),
    warehouse_id INTEGER NOT NULL REFERENCES catalog_warehouse(id),
    status TEXT NOT NULL,
    currency TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE checkout_cartline (
    id INTEGER PRIMARY KEY,
    cart_id INTEGER NOT NULL REFERENCES checkout_cart(id),
    product_id INTEGER NOT NULL REFERENCES catalog_product(id),
    qty INTEGER NOT NULL
);

CREATE TABLE checkout_attempt (
    id INTEGER PRIMARY KEY,
    attempt_id TEXT NOT NULL UNIQUE,
    cart_id INTEGER NOT NULL REFERENCES checkout_cart(id),
    shopper_id INTEGER NOT NULL REFERENCES identity_shopper(id),
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL,
    az_origin TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE checkout_order (
    id INTEGER PRIMARY KEY,
    order_ref TEXT NOT NULL UNIQUE,
    shopper_id INTEGER NOT NULL REFERENCES identity_shopper(id),
    attempt_id TEXT NOT NULL,
    warehouse_id INTEGER NOT NULL REFERENCES catalog_warehouse(id),
    status TEXT NOT NULL,
    channel TEXT NOT NULL,
    currency TEXT NOT NULL,
    total_cents INTEGER NOT NULL,
    az_origin TEXT NOT NULL,
    placed_at TEXT NOT NULL,
    write_lsn INTEGER NOT NULL
);

CREATE TABLE checkout_orderline (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES checkout_order(id),
    product_id INTEGER NOT NULL REFERENCES catalog_product(id),
    qty INTEGER NOT NULL,
    unit_cents INTEGER NOT NULL
);

CREATE TABLE checkout_payment (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES checkout_order(id),
    provider_ref TEXT NOT NULL,
    status TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    captured_at TEXT
);

CREATE TABLE fulfill_side_effect (
    id INTEGER PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    delivered_at TEXT,
    write_lsn INTEGER NOT NULL
);

CREATE TABLE fulfill_webhook (
    id INTEGER PRIMARY KEY,
    side_effect_id INTEGER NOT NULL REFERENCES fulfill_side_effect(id),
    target TEXT NOT NULL,
    attempt_no INTEGER NOT NULL,
    http_status INTEGER NOT NULL
);

CREATE TABLE ha_watermark (
    role TEXT PRIMARY KEY,
    wal_lsn INTEGER NOT NULL,
    applied_lsn INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE ha_fence_lease (
    resource TEXT PRIMARY KEY,
    owner_node TEXT NOT NULL,
    epoch INTEGER NOT NULL,
    writable INTEGER NOT NULL,
    fenced_until TEXT NOT NULL
);

CREATE TABLE ha_node (
    node_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    ready INTEGER NOT NULL
);

CREATE TABLE django_session (
    session_key TEXT PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TEXT NOT NULL
);

CREATE INDEX idx_order_shopper ON checkout_order(shopper_id);
CREATE INDEX idx_order_status ON checkout_order(status);
CREATE INDEX idx_order_placed ON checkout_order(placed_at);
CREATE INDEX idx_order_lsn ON checkout_order(write_lsn);
CREATE INDEX idx_effect_attempt ON fulfill_side_effect(attempt_id);
CREATE INDEX idx_reservation_attempt ON inventory_reservation(attempt_id);
