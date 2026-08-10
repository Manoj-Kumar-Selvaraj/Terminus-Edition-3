WITH RECURSIVE seq(n) AS (
  SELECT 1
  UNION ALL
  SELECT n + 1 FROM seq WHERE n < 4000
)
INSERT INTO users(name)
SELECT printf('user-%04d', n) FROM seq;

WITH RECURSIVE seq(n) AS (
  SELECT 1
  UNION ALL
  SELECT n + 1 FROM seq WHERE n < 6000
)
INSERT INTO posts(content, user_id)
SELECT printf('post-%04d', n), ((n - 1) % 4000) + 1 FROM seq;
