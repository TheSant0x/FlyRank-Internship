-- Stage 4: SQL I ran by hand against tasks.db (same queries DB Browser would run).

-- List every task
SELECT * FROM tasks;

-- Only completed tasks
SELECT * FROM tasks WHERE done = 1;

-- How many tasks are there?
SELECT COUNT(*) FROM tasks;

-- Mark every task completed
UPDATE tasks SET done = 1;

-- Delete all completed tasks
DELETE FROM tasks WHERE done = 1;

-- What each returned: the first three returned the seeded rows (three tasks,
-- then the one done task, then 3), and after the UPDATE every task was done,
-- so the DELETE removed all three and left the table empty.
