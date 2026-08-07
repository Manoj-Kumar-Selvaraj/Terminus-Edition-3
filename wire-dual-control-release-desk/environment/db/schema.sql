BEGIN;

CREATE TABLE wire_account (
    account_id char(16) PRIMARY KEY,
    balance_cents bigint NOT NULL CHECK (balance_cents >= 0),
    frozen boolean NOT NULL DEFAULT false
);

CREATE TABLE wire_operator (
    operator_id char(16) PRIMARY KEY,
    active boolean NOT NULL DEFAULT true
);

CREATE TABLE wire_request (
    wire_id char(16) PRIMARY KEY,
    debit_account char(16) NOT NULL REFERENCES wire_account(account_id),
    credit_account char(16) NOT NULL REFERENCES wire_account(account_id),
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    initiator_id char(16) NOT NULL REFERENCES wire_operator(operator_id),
    approver_id char(16) REFERENCES wire_operator(operator_id),
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    state char(12) NOT NULL DEFAULT 'INITIATED',
    CHECK (state IN ('INITIATED', 'APPROVED', 'RELEASED', 'CANCELLED')),
    CHECK (debit_account <> credit_account)
);

CREATE TABLE ledger_entry (
    entry_id bigserial PRIMARY KEY,
    wire_id char(16) NOT NULL REFERENCES wire_request(wire_id),
    account_id char(16) NOT NULL REFERENCES wire_account(account_id),
    amount_cents bigint NOT NULL CHECK (amount_cents > 0),
    side char(6) NOT NULL,
    CHECK (side IN ('DEBIT', 'CREDIT'))
);

CREATE UNIQUE INDEX one_side_per_wire
    ON ledger_entry(wire_id, side);

CREATE TABLE request_record (
    request_id char(24) PRIMARY KEY,
    command_name char(12) NOT NULL,
    fingerprint char(240) NOT NULL,
    response_line char(500) NOT NULL,
    wire_id char(16),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp()
);

CREATE TABLE audit_counter (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    next_value bigint NOT NULL CHECK (next_value > 0)
);

CREATE TABLE audit_event (
    audit_sequence bigint PRIMARY KEY,
    request_id char(24) NOT NULL UNIQUE REFERENCES request_record(request_id) DEFERRABLE INITIALLY DEFERRED,
    wire_id char(16) NOT NULL REFERENCES wire_request(wire_id),
    action char(12) NOT NULL,
    prior_state char(12) NOT NULL,
    new_state char(12) NOT NULL,
    resulting_revision integer NOT NULL,
    CHECK (resulting_revision > 0)
);

INSERT INTO audit_counter(singleton, next_value) VALUES (true, 1);

INSERT INTO wire_account(account_id, balance_cents, frozen) VALUES
    ('ACC-D1', 1000000, false),
    ('ACC-D2', 500000, false),
    ('ACC-C1', 100000, false),
    ('ACC-C2', 0, false),
    ('ACC-FZ', 800000, true),
    ('ACC-LOW', 250, false);

INSERT INTO wire_operator(operator_id, active) VALUES
    ('OP-A1', true),
    ('OP-A2', true),
    ('OP-B1', true),
    ('OP-B2', true);

COMMIT;
