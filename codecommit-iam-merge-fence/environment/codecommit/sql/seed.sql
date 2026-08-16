-- Deterministic 12k-row authz history for platform analytics.
WITH RECURSIVE seq(n) AS (
  SELECT 0
  UNION ALL
  SELECT n + 1 FROM seq WHERE n < 11999
)
INSERT INTO authz_events (
  event_id, principal, action, repo, reference, allowed, source_ip, mfa, decided_at
)
SELECT
  n,
  CASE n % 6
    WHEN 0 THEN 'dev-alice'
    WHEN 1 THEN 'dev-ben'
    WHEN 2 THEN 'rev-a'
    WHEN 3 THEN 'rev-b'
    WHEN 4 THEN 'intern'
    ELSE 'pipeline-bot'
  END,
  CASE n % 4
    WHEN 0 THEN 'codecommit:GitPull'
    WHEN 1 THEN 'codecommit:GitPush'
    WHEN 2 THEN 'codecommit:MergePullRequestByFastForward'
    ELSE 'deliver'
  END,
  CASE n % 5
    WHEN 0 THEN 'ledger'
    WHEN 1 THEN 'sandbox'
    WHEN 2 THEN 'team01'
    WHEN 3 THEN 'team02'
    ELSE 'team03'
  END,
  CASE n % 7
    WHEN 0 THEN 'refs/heads/main'
    WHEN 1 THEN 'refs/heads/dev/alice'
    WHEN 2 THEN 'refs/heads/dev/ben'
    WHEN 3 THEN 'refs/heads/release'
    WHEN 4 THEN 'refs/heads/dev/team01'
    WHEN 5 THEN 'refs/heads/dev/team02'
    ELSE 'refs/heads/dev/team03'
  END,
  CASE WHEN (n % 11) < 8 THEN 1 ELSE 0 END,
  CASE n % 3
    WHEN 0 THEN '10.8.12.4'
    WHEN 1 THEN '10.8.44.9'
    ELSE '203.0.113.9'
  END,
  CASE WHEN (n % 5) = 0 THEN 0 ELSE 1 END,
  printf(
    '2026-%02d-%02dT%02d:%02d:00Z',
    1 + (n % 6),
    1 + (n % 28),
    n % 24,
    (n * 7) % 60
  )
FROM seq;
