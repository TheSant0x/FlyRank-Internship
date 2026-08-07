-- Queries run against the taskdb Postgres container (Stage 4/5 inspection).

-- The seeded rows, straight from the container:
SELECT * FROM tasks;

-- Row count after a restart (seed-once rule):
SELECT COUNT(*) FROM tasks;
