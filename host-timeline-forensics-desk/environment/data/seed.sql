WITH digits(d) AS (
    VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)
), numbers(n) AS (
    SELECT a.d + 10*b.d + 100*c.d + 1000*d.d + 10000*e.d + 1
    FROM digits a CROSS JOIN digits b CROSS JOIN digits c CROSS JOIN digits d CROSS JOIN digits e
    WHERE a.d + 10*b.d + 100*c.d + 1000*d.d + 10000*e.d < 14200
)
INSERT INTO seed_records(record_id,record_type,tenant_id,case_id,endpoint_id,platform,site_id,source_id,acquisition_mode,disposition,artifact_family)
SELECT
    printf('record-%06d', n),
    CASE
      WHEN n <= 20 THEN 'tenant'
      WHEN n <= 180 THEN 'actor'
      WHEN n <= 420 THEN 'case'
      WHEN n <= 1020 THEN 'endpoint'
      WHEN n <= 1220 THEN 'policy'
      WHEN n <= 3220 THEN 'collection_item'
      WHEN n <= 6220 THEN 'collection_attempt'
      WHEN n <= 8720 THEN 'evidence_object'
      WHEN n <= 11220 THEN 'evidence_item'
      WHEN n <= 13220 THEN 'custody_event'
      WHEN n <= 13720 THEN 'event_observation'
      WHEN n <= 13920 THEN 'case_hold'
      ELSE 'export_job'
    END,
    printf('tenant-%02d', ((n-1) % 20) + 1),
    CASE WHEN n <= 20 OR (n > 20 AND n <= 180) OR (n > 420 AND n <= 1020) OR (n > 1020 AND n <= 1220)
         THEN NULL ELSE printf('CASE-%06d', ((n-1) % 240) + 1) END,
    CASE WHEN n > 420 AND n <= 1020 THEN printf('HOST-%06d', ((n-421) % 600) + 1) ELSE NULL END,
    CASE ((n-1) % 3) WHEN 0 THEN 'linux' WHEN 1 THEN 'windows' ELSE 'macos' END,
    CASE ((n-1) % 4) WHEN 0 THEN 'north' WHEN 1 THEN 'south' WHEN 2 THEN 'west' ELSE 'lab' END,
    CASE ((n-1) % 6) WHEN 0 THEN 'filesystem' WHEN 1 THEN 'eventlog' WHEN 2 THEN 'volatile-state' WHEN 3 THEN 'registry' WHEN 4 THEN 'browser' ELSE 'execution-trace' END,
    CASE WHEN (n % 4)=0 THEN 'offline' ELSE 'live' END,
    CASE ((n-1) % 6) WHEN 0 THEN 'complete' WHEN 1 THEN 'partial' WHEN 2 THEN 'unavailable' WHEN 3 THEN 'rejected' WHEN 4 THEN 'cancelled' ELSE 'failed' END,
    CASE ((n-1) % 6) WHEN 0 THEN 'filesystem.metadata' WHEN 1 THEN 'eventlog.system' WHEN 2 THEN 'volatile.processes' WHEN 3 THEN 'registry.autoruns' WHEN 4 THEN 'browser.history' ELSE 'execution.prefetch' END
FROM numbers;
