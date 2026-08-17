CREATE TABLE IF NOT EXISTS tenant (
    tenant_id TEXT PRIMARY KEY,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sku (
    sku_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    sku_code TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id)
);
CREATE TABLE IF NOT EXISTS offer (
    offer_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    offer_code TEXT NOT NULL,
    qty_on_hand INTEGER NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id),
    FOREIGN KEY (sku_id) REFERENCES sku(sku_id)
);
CREATE TABLE IF NOT EXISTS hold (
    hold_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    qty INTEGER NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id),
    FOREIGN KEY (offer_id) REFERENCES offer(offer_id)
);
