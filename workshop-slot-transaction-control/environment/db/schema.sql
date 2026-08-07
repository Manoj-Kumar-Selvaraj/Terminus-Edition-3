BEGIN;

CREATE TABLE workshop_bay (
    bay_id char(8) PRIMARY KEY,
    capability char(16) NOT NULL,
    active boolean NOT NULL DEFAULT true,
    CHECK (capability IN ('TRANSPORT', 'GENERATOR', 'RADIO', 'MEDICAL', 'UNIVERSAL'))
);

CREATE TABLE technician (
    technician_id char(8) PRIMARY KEY,
    certification char(16) NOT NULL,
    active boolean NOT NULL DEFAULT true,
    CHECK (certification IN ('TRANSPORT', 'GENERATOR', 'RADIO', 'MEDICAL', 'UNIVERSAL'))
);

CREATE TABLE work_order (
    work_order_id char(16) PRIMARY KEY,
    equipment_class char(16) NOT NULL,
    priority smallint NOT NULL,
    revision integer NOT NULL DEFAULT 1,
    state char(12) NOT NULL DEFAULT 'OPEN',
    CHECK (equipment_class IN ('TRANSPORT', 'GENERATOR', 'RADIO', 'MEDICAL')),
    CHECK (priority BETWEEN 1 AND 9),
    CHECK (revision > 0),
    CHECK (state IN ('OPEN', 'RESERVED', 'STARTED', 'COMPLETED', 'CANCELLED'))
);

CREATE TABLE booking (
    booking_id char(20) PRIMARY KEY,
    work_order_id char(16) NOT NULL REFERENCES work_order(work_order_id),
    bay_id char(8) NOT NULL REFERENCES workshop_bay(bay_id),
    technician_id char(8) NOT NULL REFERENCES technician(technician_id),
    start_tick integer NOT NULL,
    end_tick integer NOT NULL,
    policy_id char(16) NOT NULL,
    shift_code char(1) NOT NULL,
    supervision_level smallint NOT NULL,
    capacity_percent smallint NOT NULL,
    state char(12) NOT NULL,
    revision integer NOT NULL,
    CHECK (start_tick >= 0 AND end_tick <= 999999 AND start_tick < end_tick),
    CHECK (shift_code IN ('D', 'N')),
    CHECK (supervision_level BETWEEN 1 AND 3),
    CHECK (capacity_percent BETWEEN 1 AND 100),
    CHECK (state IN ('RESERVED', 'STARTED', 'COMPLETED', 'CANCELLED')),
    CHECK (revision > 0)
);

CREATE UNIQUE INDEX one_active_booking_per_order
    ON booking(work_order_id)
    WHERE state IN ('RESERVED', 'STARTED');

CREATE INDEX active_bay_schedule
    ON booking(bay_id, start_tick, end_tick)
    WHERE state IN ('RESERVED', 'STARTED');

CREATE INDEX active_technician_schedule
    ON booking(technician_id, start_tick, end_tick)
    WHERE state IN ('RESERVED', 'STARTED');

CREATE TABLE request_record (
    request_id char(24) PRIMARY KEY,
    command_name char(12) NOT NULL,
    fingerprint char(240) NOT NULL,
    response_line char(500) NOT NULL,
    work_order_id char(16),
    created_at timestamptz NOT NULL DEFAULT transaction_timestamp()
);

CREATE TABLE audit_counter (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    next_value bigint NOT NULL CHECK (next_value > 0)
);

CREATE TABLE audit_event (
    audit_sequence bigint PRIMARY KEY,
    request_id char(24) NOT NULL UNIQUE REFERENCES request_record(request_id) DEFERRABLE INITIALLY DEFERRED,
    work_order_id char(16) NOT NULL REFERENCES work_order(work_order_id),
    action char(12) NOT NULL,
    prior_state char(12) NOT NULL,
    new_state char(12) NOT NULL,
    resulting_revision integer NOT NULL,
    CHECK (resulting_revision > 0)
);

INSERT INTO audit_counter(singleton, next_value) VALUES (true, 1);

INSERT INTO workshop_bay(bay_id, capability) VALUES
    ('BAY-T1', 'TRANSPORT'),
    ('BAY-T2', 'TRANSPORT'),
    ('BAY-G1', 'GENERATOR'),
    ('BAY-R1', 'RADIO'),
    ('BAY-M1', 'MEDICAL'),
    ('BAY-U1', 'UNIVERSAL');

INSERT INTO technician(technician_id, certification) VALUES
    ('TECH-T1', 'TRANSPORT'),
    ('TECH-T2', 'TRANSPORT'),
    ('TECH-G1', 'GENERATOR'),
    ('TECH-R1', 'RADIO'),
    ('TECH-M1', 'MEDICAL'),
    ('TECH-U1', 'UNIVERSAL');

COMMIT;
