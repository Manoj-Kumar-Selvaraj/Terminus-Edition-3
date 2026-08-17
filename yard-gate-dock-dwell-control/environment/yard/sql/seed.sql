-- Compact deterministic seed for authenticity checks. Runtime sqlite is built by cmd/seed.py.
WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)
INSERT INTO doors(door_id, door_class, reefer_plug, live_capable, drop_capable, allowed_equipment)
SELECT printf('D%02d', n+1),
  CASE WHEN n < 32 THEN 'DRY' WHEN n < 40 THEN 'REEFER' ELSE 'OUTBOUND' END,
  CASE WHEN n >= 32 AND n < 40 THEN 1 ELSE 0 END,
  1,
  CASE WHEN n >= 40 THEN 1 ELSE 0 END,
  CASE WHEN n < 32 THEN '["DRY_53","TANK"]' WHEN n < 40 THEN '["REEFER_53"]' ELSE '["DRY_53","CONTAINER_40","TANK"]' END
FROM x WHERE n < 48;
WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)
INSERT INTO spots(spot_id, zone, door_id) SELECT printf('A%02d', n+1), 'DOCK_APRON', printf('D%02d', n+1) FROM x WHERE n < 48;
WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)
INSERT INTO spots(spot_id, zone) SELECT printf('L%04d', a.n + 126*b.n + 1), 'DROP_LOT' FROM x a CROSS JOIN x b WHERE a.n + 126*b.n < 400;
WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)
INSERT INTO spots(spot_id, zone) SELECT printf('S%04d', a.n + 126*b.n + 1), 'STAGING' FROM x a CROSS JOIN x b WHERE a.n + 126*b.n < 200;
WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)
INSERT INTO spots(spot_id, zone) SELECT printf('C%04d', n+1), 'CHASSIS_STACK' FROM x WHERE n < 72;
WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)
INSERT INTO chassis_units(chassis_id, spot_id) SELECT printf('CH%04d', n+1), printf('C%04d', n+1) FROM x WHERE n < 72;
WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)
INSERT INTO visits(visit_id, scac, trailer_number, visit_type, equipment, state, spot_id, door_id, appointment_id, gate_in, gate_out, seal, on_ground, chassis_id, clock_start)
SELECT
  printf('V%06d', n),
 CASE WHEN n % 72 = 0 THEN 'AAAA' WHEN n % 72 = 1 THEN 'AAAB' WHEN n % 72 = 2 THEN 'AAAC' WHEN n % 72 = 3 THEN 'AAAD' WHEN n % 72 = 4 THEN 'AAAE' WHEN n % 72 = 5 THEN 'AAAF' WHEN n % 72 = 6 THEN 'AAAG' WHEN n % 72 = 7 THEN 'AAAH' WHEN n % 72 = 8 THEN 'AAAJ' WHEN n % 72 = 9 THEN 'AAAK' WHEN n % 72 = 10 THEN 'AAAL' WHEN n % 72 = 11 THEN 'AAAM' WHEN n % 72 = 12 THEN 'AAAN' WHEN n % 72 = 13 THEN 'AAAP' WHEN n % 72 = 14 THEN 'AAAQ' WHEN n % 72 = 15 THEN 'AAAR' WHEN n % 72 = 16 THEN 'AAAS' WHEN n % 72 = 17 THEN 'AAAT' WHEN n % 72 = 18 THEN 'AAAU' WHEN n % 72 = 19 THEN 'AAAV' WHEN n % 72 = 20 THEN 'AAAW' WHEN n % 72 = 21 THEN 'AAAX' WHEN n % 72 = 22 THEN 'AAAY' WHEN n % 72 = 23 THEN 'AAAZ' WHEN n % 72 = 24 THEN 'AABA' WHEN n % 72 = 25 THEN 'AABB' WHEN n % 72 = 26 THEN 'AABC' WHEN n % 72 = 27 THEN 'AABD' WHEN n % 72 = 28 THEN 'AABE' WHEN n % 72 = 29 THEN 'AABF' WHEN n % 72 = 30 THEN 'AABG' WHEN n % 72 = 31 THEN 'AABH' WHEN n % 72 = 32 THEN 'AABJ' WHEN n % 72 = 33 THEN 'AABK' WHEN n % 72 = 34 THEN 'AABL' WHEN n % 72 = 35 THEN 'AABM' WHEN n % 72 = 36 THEN 'AABN' WHEN n % 72 = 37 THEN 'AABP' WHEN n % 72 = 38 THEN 'AABQ' WHEN n % 72 = 39 THEN 'AABR' WHEN n % 72 = 40 THEN 'AABS' WHEN n % 72 = 41 THEN 'AABT' WHEN n % 72 = 42 THEN 'AABU' WHEN n % 72 = 43 THEN 'AABV' WHEN n % 72 = 44 THEN 'AABW' WHEN n % 72 = 45 THEN 'AABX' WHEN n % 72 = 46 THEN 'AABY' WHEN n % 72 = 47 THEN 'AABZ' WHEN n % 72 = 48 THEN 'AACA' WHEN n % 72 = 49 THEN 'AACB' WHEN n % 72 = 50 THEN 'AACC' WHEN n % 72 = 51 THEN 'AACD' WHEN n % 72 = 52 THEN 'AACE' WHEN n % 72 = 53 THEN 'AACF' WHEN n % 72 = 54 THEN 'AACG' WHEN n % 72 = 55 THEN 'AACH' WHEN n % 72 = 56 THEN 'AACJ' WHEN n % 72 = 57 THEN 'AACK' WHEN n % 72 = 58 THEN 'AACL' WHEN n % 72 = 59 THEN 'AACM' WHEN n % 72 = 60 THEN 'AACN' WHEN n % 72 = 61 THEN 'AACP' WHEN n % 72 = 62 THEN 'AACQ' WHEN n % 72 = 63 THEN 'AACR' WHEN n % 72 = 64 THEN 'AACS' WHEN n % 72 = 65 THEN 'AACT' WHEN n % 72 = 66 THEN 'AACU' WHEN n % 72 = 67 THEN 'AACV' WHEN n % 72 = 68 THEN 'AACW' WHEN n % 72 = 69 THEN 'AACX' WHEN n % 72 = 70 THEN 'AACY' WHEN n % 72 = 71 THEN 'AACZ' END,
  printf('U%06d', n),
  CASE WHEN n % 20 < 8 THEN 'LIVE_IN' WHEN n % 20 < 13 THEN 'DROP_IN' WHEN n % 20 < 17 THEN 'LIVE_OUT' WHEN n % 20 < 19 THEN 'EMPTY_OUT' ELSE 'LOADED_PICKUP' END,
  CASE n % 4 WHEN 0 THEN 'DRY_53' WHEN 1 THEN 'REEFER_53' WHEN 2 THEN 'TANK' ELSE 'CONTAINER_40' END,
  CASE WHEN n >= 12500 THEN 'ON_YARD' ELSE 'CLOSED' END,
  NULL, NULL, NULL,
  datetime('2026-03-02T12:00:00Z', printf('+%d minutes', (n / 900) * 1440 + (n % 900))),
  CASE WHEN n >= 12500 THEN NULL ELSE datetime('2026-03-02T12:00:00Z', printf('+%d minutes', (n / 900) * 1440 + (n % 900) + 90)) END,
  printf('SL%06d', n), 0, NULL,
  datetime('2026-03-02T12:00:00Z', printf('+%d minutes', (n / 900) * 1440 + (n % 900)))
FROM (SELECT a.n + 126 * b.n AS n FROM x a CROSS JOIN x b) WHERE n < 12600;
