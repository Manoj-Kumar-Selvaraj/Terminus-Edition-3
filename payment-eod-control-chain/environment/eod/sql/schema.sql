PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE cycles (
    cycle_id TEXT PRIMARY KEY,
    business_date TEXT NOT NULL,
    source TEXT NOT NULL,
    run_id TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (state IN ('OPEN','PROCESSING','RECONCILED','HELD','COMPLETED')),
    reconciliation_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (reconciliation_status IN ('PENDING','BALANCED','HELD')),
    completion_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (completion_status IN ('PENDING','WAITING','COMPLETED')),
    started_at TEXT,
    reconciled_at TEXT,
    completed_at TEXT,
    UNIQUE (business_date, source, run_id)
);

CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','BLOCKED','CLOSED')),
    balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    updated_at TEXT
);

CREATE TABLE payment_history (
    source_ref TEXT PRIMARY KEY,
    accepted_cycle_id TEXT,
    payer_account TEXT NOT NULL,
    beneficiary_ref TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    currency TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACCEPTED','COMPLETED','REJECTED')),
    recorded_at TEXT,
    FOREIGN KEY (accepted_cycle_id) REFERENCES cycles(cycle_id)
);

CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    payer_account TEXT NOT NULL,
    beneficiary_ref TEXT NOT NULL,
    beneficiary_account TEXT,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    fee_cents INTEGER NOT NULL DEFAULT 0 CHECK (fee_cents >= 0),
    tax_cents INTEGER NOT NULL DEFAULT 0 CHECK (tax_cents >= 0),
    currency TEXT NOT NULL,
    purpose TEXT NOT NULL,
    received_seq INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id),
    FOREIGN KEY (payer_account) REFERENCES accounts(account_id),
    UNIQUE (cycle_id, payment_id),
    UNIQUE (cycle_id, source_ref)
);

CREATE TABLE payment_outcomes (
    payment_id INTEGER PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    outcome TEXT NOT NULL
        CHECK (outcome IN ('SUCCESS_INTERNAL','SUCCESS_EXTERNAL','DUPLICATE','REJECTED')),
    reason TEXT NOT NULL,
    execution_state TEXT NOT NULL,
    decided_at TEXT,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE TABLE internal_postings (
    posting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL,
    cycle_id TEXT NOT NULL,
    payer_account TEXT NOT NULL,
    beneficiary_account TEXT NOT NULL,
    debit_cents INTEGER NOT NULL CHECK (debit_cents > 0),
    beneficiary_credit_cents INTEGER NOT NULL CHECK (beneficiary_credit_cents > 0),
    posted_at TEXT,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE TABLE reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL,
    cycle_id TEXT NOT NULL,
    payer_account TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
    created_at TEXT,
    released_at TEXT,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE INDEX one_active_reservation_per_payment
ON reservations(payment_id, active);

CREATE INDEX reservations_by_payer_active
ON reservations(payer_account, active);

CREATE TABLE clearing_items (
    clearing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL,
    cycle_id TEXT NOT NULL,
    reservation_id INTEGER NOT NULL,
    source_ref TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'READY'
        CHECK (status IN ('READY','SUBMITTED','ACKNOWLEDGED')),
    created_at TEXT,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id),
    FOREIGN KEY (reservation_id) REFERENCES reservations(reservation_id)
);

CREATE TABLE ledger_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL,
    cycle_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('D','C')),
    account_code TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    created_at TEXT,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE INDEX ledger_entries_cycle_side
ON ledger_entries(cycle_id, side);

CREATE TABLE cycle_prerequisites (
    cycle_id TEXT PRIMARY KEY,
    delivery_ack INTEGER NOT NULL DEFAULT 0 CHECK (delivery_ack IN (0,1)),
    report_complete INTEGER NOT NULL DEFAULT 0 CHECK (report_complete IN (0,1)),
    archive_complete INTEGER NOT NULL DEFAULT 0 CHECK (archive_complete IN (0,1)),
    updated_at TEXT,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE TABLE delivery_events (
    delivery_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING','ACKNOWLEDGED','FAILED')),
    external_ref TEXT,
    recorded_at TEXT,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id),
    UNIQUE (cycle_id, channel, external_ref)
);

CREATE TABLE publication_batches (
    cycle_id TEXT PRIMARY KEY,
    response_published INTEGER NOT NULL DEFAULT 0 CHECK (response_published IN (0,1)),
    clearing_published INTEGER NOT NULL DEFAULT 0 CHECK (clearing_published IN (0,1)),
    published_at TEXT,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE TABLE success_authorizations (
    authorization_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    business_date TEXT NOT NULL,
    source TEXT NOT NULL,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'AUTHORIZED'),
    authorized_at TEXT,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE TABLE work_checkpoints (
    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    payment_id INTEGER,
    stage TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('STARTED','DONE','HELD')),
    checkpoint_key TEXT NOT NULL,
    recorded_at TEXT,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id),
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    UNIQUE (checkpoint_key)
);

CREATE TABLE audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    payment_id INTEGER,
    event_type TEXT NOT NULL,
    event_key TEXT NOT NULL,
    event_detail TEXT NOT NULL DEFAULT '',
    recorded_at TEXT,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id),
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    UNIQUE (event_key)
);

CREATE TABLE reconciliation_runs (
    reconciliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('BALANCED','HELD')),
    original_count INTEGER NOT NULL,
    outcome_count INTEGER NOT NULL,
    original_value_cents INTEGER NOT NULL,
    response_value_cents INTEGER NOT NULL,
    internal_success_count INTEGER NOT NULL,
    internal_posting_count INTEGER NOT NULL,
    external_success_count INTEGER NOT NULL,
    reservation_count INTEGER NOT NULL,
    clearing_count INTEGER NOT NULL,
    reserved_debit_cents INTEGER NOT NULL,
    clearing_value_cents INTEGER NOT NULL,
    external_fee_tax_cents INTEGER NOT NULL,
    ledger_debits_cents INTEGER NOT NULL,
    ledger_credits_cents INTEGER NOT NULL,
    invalid_effect_count INTEGER NOT NULL,
    mismatch_count INTEGER NOT NULL,
    missing_ledger_count INTEGER NOT NULL,
    reconciled_at TEXT,
    FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
);

CREATE INDEX reconciliation_runs_cycle
ON reconciliation_runs(cycle_id, reconciliation_id);
