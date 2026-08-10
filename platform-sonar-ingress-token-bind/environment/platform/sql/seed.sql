INSERT INTO postgres_identity(name, address, port, db_name, username, password) VALUES
  ('primary', 'platform-mvp-sonarqube.cluster.platform.test', 5432, 'sonarqube', 'sonarqube', 'rds-sonar-pass'),
  ('restored', 'platform-mvp-sonarqube-restored.cluster.platform.test', 5432, 'sonarqube', 'sonarqube', 'rds-sonar-pass');

INSERT INTO platform_meta(key, value) VALUES
  ('cluster_name', 'platform-mvp-dev'),
  ('domain', 'platform.test'),
  ('ingress_group', 'platform-ingress');

WITH RECURSIVE seq(n) AS (
  SELECT 1
  UNION ALL
  SELECT n + 1 FROM seq WHERE n < 12000
)
INSERT INTO sonar_analysis(
  analysis_id, project_key, status, scanner, gate_result, author, branch, token_kind, started_at, duration_sec
)
SELECT
  printf('ANL-%05d', n),
  printf('app-%02d', ((n - 1) % 48) + 1),
  CASE (n % 5)
    WHEN 0 THEN 'SUCCESS'
    WHEN 1 THEN 'FAILED'
    WHEN 2 THEN 'CANCELED'
    WHEN 3 THEN 'TIMEOUT'
    ELSE 'IN_PROGRESS'
  END,
  CASE (n % 4)
    WHEN 0 THEN 'sonar-scanner-cli'
    WHEN 1 THEN 'maven'
    WHEN 2 THEN 'gradle'
    ELSE 'npm'
  END,
  CASE (n % 4)
    WHEN 0 THEN 'OK'
    WHEN 1 THEN 'ERROR'
    WHEN 2 THEN 'WARN'
    ELSE 'NONE'
  END,
  printf('dev%03d', ((n - 1) % 120) + 1),
  CASE (n % 6)
    WHEN 0 THEN 'main'
    WHEN 1 THEN 'develop'
    WHEN 2 THEN 'release'
    WHEN 3 THEN 'hotfix'
    WHEN 4 THEN 'feature'
    ELSE 'bugfix'
  END,
  CASE (n % 3)
    WHEN 0 THEN 'global-analysis'
    WHEN 1 THEN 'user'
    ELSE 'project'
  END,
  printf(
    '%sT%02d:%02d:00Z',
    date('2024-06-01', printf('+%d day', (n - 1) % 200)),
    (n * 5) % 24,
    (n * 7) % 60
  ),
  30 + (n * 11) % 900
FROM seq;
