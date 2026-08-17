CREATE TABLE subnets (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  az TEXT NOT NULL,
  tier TEXT NOT NULL,
  cidr TEXT NOT NULL
);

CREATE TABLE images (
  ami_id TEXT PRIMARY KEY,
  owner_account_id TEXT NOT NULL,
  architecture TEXT NOT NULL,
  state TEXT NOT NULL,
  deprecated INTEGER NOT NULL
);

CREATE INDEX idx_subnets_account_tier ON subnets(account_id, tier);
CREATE INDEX idx_subnets_az ON subnets(az);
