-- Yard control plane physical model. Occupancy views are selected at health/snapshot.

CREATE TABLE doors (
    door_id TEXT PRIMARY KEY,
    door_class TEXT NOT NULL CHECK (door_class IN ('DRY', 'REEFER', 'OUTBOUND')),
    reefer_plug INTEGER NOT NULL CHECK (reefer_plug IN (0, 1)),
    live_capable INTEGER NOT NULL CHECK (live_capable IN (0, 1)),
    drop_capable INTEGER NOT NULL CHECK (drop_capable IN (0, 1)),
    allowed_equipment TEXT NOT NULL
);

CREATE TABLE spots (
    spot_id TEXT PRIMARY KEY,
    zone TEXT NOT NULL CHECK (zone IN ('DROP_LOT', 'STAGING', 'DOCK_APRON', 'CHASSIS_STACK')),
    door_id TEXT REFERENCES doors(door_id),
    occupant_visit_id TEXT,
    reserved_move_id TEXT
);

CREATE TABLE chassis_units (
    chassis_id TEXT PRIMARY KEY,
    spot_id TEXT REFERENCES spots(spot_id),
    mounted_visit_id TEXT
);

CREATE TABLE appointments (
    appointment_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    scac TEXT NOT NULL,
    visit_type TEXT NOT NULL,
    door_class TEXT NOT NULL,
    trailer_number TEXT,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    door_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'CLAIMED', 'NO_SHOW'))
);

CREATE TABLE visits (
    visit_id TEXT PRIMARY KEY,
    scac TEXT NOT NULL,
    trailer_number TEXT NOT NULL,
    visit_type TEXT NOT NULL,
    equipment TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'SCHEDULED', 'ON_YARD', 'MOVING', 'DOCKED', 'CLOSED', 'NO_SHOW'
    )),
    spot_id TEXT,
    door_id TEXT,
    appointment_id TEXT,
    gate_in TEXT,
    gate_out TEXT,
    seal TEXT,
    on_ground INTEGER NOT NULL DEFAULT 0 CHECK (on_ground IN (0, 1)),
    chassis_id TEXT,
    clock_start TEXT
);

-- Starter uniqueness is trailer-only among open visits (not scac+trailer).
CREATE UNIQUE INDEX idx_open_trailer ON visits(trailer_number)
    WHERE state IN ('ON_YARD', 'MOVING', 'DOCKED');

CREATE TABLE moves (
    move_id TEXT PRIMARY KEY,
    visit_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'REQUESTED', 'DISPATCHED', 'IN_TRANSIT', 'COMPLETED', 'CANCELLED', 'FAILED'
    )),
    origin_spot_id TEXT,
    dest_spot_id TEXT,
    event_id TEXT,
    seq INTEGER
);

CREATE TABLE holds (
    hold_id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id TEXT NOT NULL,
    hold_code TEXT NOT NULL,
    placed_at TEXT NOT NULL,
    released_at TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE event_log (
    event_id TEXT PRIMARY KEY,
    seq INTEGER NOT NULL UNIQUE,
    verb TEXT NOT NULL,
    body TEXT NOT NULL,
    accepted_at TEXT NOT NULL
);

CREATE TABLE applied (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_applied_seq INTEGER NOT NULL
);

INSERT INTO applied (id, last_applied_seq) VALUES (1, 0);

CREATE VIEW v_occupancy AS
SELECT spot_id, zone, occupant_visit_id AS visit_id, reserved_move_id
FROM spots
WHERE occupant_visit_id IS NOT NULL OR reserved_move_id IS NOT NULL;

CREATE VIEW v_open_visits AS
SELECT visit_id, scac, trailer_number, visit_type, equipment, state,
       spot_id, door_id, gate_in, appointment_id, seal, on_ground, chassis_id
FROM visits
WHERE state IN ('ON_YARD', 'MOVING', 'DOCKED');

CREATE VIEW v_active_holds AS
SELECT visit_id, hold_code, placed_at
FROM holds
WHERE active = 1;

CREATE VIEW v_door_occupants AS
SELECT d.door_id, d.door_class, s.occupant_visit_id AS visit_id
FROM doors d
LEFT JOIN spots s ON s.door_id = d.door_id AND s.zone = 'DOCK_APRON';
