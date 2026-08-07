-- Queries run against the taskdb Postgres container (Stage 4/5 inspection).

-- The seeded rows, straight from the container:
SELECT * FROM tasks;

-- Row count after a restart (seed-once rule):
SELECT COUNT(*) FROM tasks;

-- Extras: index on the done column, with EXPLAIN ANALYZE before and after.
-- Before the index (Seq Scan, cost 0.00..22.50):
EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = true;

-- Create the index:
CREATE INDEX idx_tasks_done ON tasks (done);

-- After the index (cost drops to 0.00..1.05; the planner still seq-scans
-- a 5-row table, which is the right call at this size):
EXPLAIN ANALYZE SELECT * FROM tasks WHERE done = true;
