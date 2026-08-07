PRAGMA foreign_keys = ON;

CREATE TABLE cycles (
  cycle_id TEXT PRIMARY KEY,
  business_date TEXT NOT NULL,
  source TEXT NOT NULL,
  run_id TEXT NOT NULL,
  completion_status TEXT NOT NULL DEFAULT 'PENDING'
);

CREATE TABLE payments (
  payment_id INTEGER PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES cycles(cycle_id),
  source_ref TEXT NOT NULL,
  payer_account TEXT NOT NULL,
  beneficiary_ref TEXT NOT NULL,
  beneficiary_account TEXT,
  amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
  fee_cents INTEGER NOT NULL DEFAULT 0 CHECK (fee_cents >= 0),
  tax_cents INTEGER NOT NULL DEFAULT 0 CHECK (tax_cents >= 0),
  currency TEXT NOT NULL,
  purpose TEXT NOT NULL
);

CREATE TABLE payment_history (
  source_ref TEXT PRIMARY KEY,
  payer_account TEXT NOT NULL,
  beneficiary_ref TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  currency TEXT NOT NULL,
  purpose TEXT NOT NULL,
  status TEXT NOT NULL
);

CREATE TABLE accounts (
  account_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  balance_cents INTEGER NOT NULL
);

CREATE TABLE payment_outcomes (
  payment_id INTEGER PRIMARY KEY REFERENCES payments(payment_id),
  outcome TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE internal_postings (
  posting_id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id INTEGER NOT NULL UNIQUE REFERENCES payments(payment_id),
  debit_cents INTEGER NOT NULL,
  beneficiary_credit_cents INTEGER NOT NULL
);

CREATE TABLE reservations (
  reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id INTEGER NOT NULL REFERENCES payments(payment_id),
  amount_cents INTEGER NOT NULL,
  active INTEGER NOT NULL CHECK (active IN (0,1))
);
CREATE UNIQUE INDEX one_active_reservation_per_payment
  ON reservations(payment_id) WHERE active = 1;

CREATE TABLE clearing_items (
  clearing_id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id INTEGER NOT NULL UNIQUE REFERENCES payments(payment_id),
  amount_cents INTEGER NOT NULL,
  currency TEXT NOT NULL
);

CREATE TABLE ledger_entries (
  entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id INTEGER NOT NULL REFERENCES payments(payment_id),
  side TEXT NOT NULL CHECK (side IN ('D','C')),
  account_code TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
  UNIQUE(payment_id, side, account_code)
);

CREATE TABLE cycle_prerequisites (
  cycle_id TEXT PRIMARY KEY REFERENCES cycles(cycle_id),
  delivery_ack INTEGER NOT NULL CHECK (delivery_ack IN (0,1)),
  report_complete INTEGER NOT NULL CHECK (report_complete IN (0,1)),
  archive_complete INTEGER NOT NULL CHECK (archive_complete IN (0,1))
);

CREATE TABLE completion_register (
  cycle_id TEXT PRIMARY KEY REFERENCES cycles(cycle_id),
  status TEXT NOT NULL,
  original_count INTEGER NOT NULL,
  final_count INTEGER NOT NULL,
  original_value_cents INTEGER NOT NULL,
  response_value_cents INTEGER NOT NULL
);

CREATE TABLE success_authorizations (
  cycle_id TEXT PRIMARY KEY REFERENCES cycles(cycle_id),
  business_date TEXT NOT NULL,
  source TEXT NOT NULL,
  run_id TEXT NOT NULL,
  status TEXT NOT NULL
);
