-- Step 04: data tests. Run after step 03:
--   duckdb data/staging/av.duckdb < pipeline/step04_tests.sql                  (macOS / Linux / Git Bash)
--   Get-Content pipeline/step04_tests.sql | duckdb data/staging/av.duckdb       (Windows PowerShell)
-- Run from the repo root. python pipeline/run_all.py runs this for you.
-- Each test returns PASS, WARN (explainable difference, document it) or FAIL (fix before building).
.mode markdown
CREATE OR REPLACE TABLE test_results AS

-- T1. Completed trips in the trip-level files equal the month files, every quarter.
WITH trips AS (
  SELECT quarter, program, mode, sum(requests) FILTER (WHERE fulfilled = 'Y') AS fulfilled
  FROM fact_trip_outcome_q WHERE company = 'Waymo' GROUP BY ALL),
months AS (
  SELECT quarter, program, mode, sum(trips) AS month_trips
  FROM fact_service_month WHERE company = 'Waymo' GROUP BY ALL)
SELECT 'T1 trips reconcile: ' || t.program || ' ' || t.mode || ' ' || t.quarter AS test,
       CASE WHEN t.fulfilled = m.month_trips THEN 'PASS' ELSE 'FAIL' END AS result,
       'trip files ' || t.fulfilled || ' vs month files ' || m.month_trips AS detail
FROM trips t JOIN months m USING (quarter, program, mode)
WHERE t.fulfilled > 0

UNION ALL
-- T2. Two collision counts: incident flags vs the census-tract table.
SELECT 'T2 collisions two sources: ' || i.program || ' ' || i.quarter,
       CASE WHEN i.collisions = l.c THEN 'PASS' ELSE 'WARN' END,
       'incident flags ' || i.collisions || ' vs tract table ' || l.c
FROM (SELECT quarter, program, sum(collisions) AS collisions FROM fact_incident_q
      WHERE company = 'Waymo' AND mode = 'driverless' GROUP BY ALL) i
JOIN (SELECT quarter, program, sum(collisions_all) AS c FROM fact_tract_q
      WHERE company = 'Waymo' AND mode = 'driverless' GROUP BY ALL) l USING (quarter, program)

UNION ALL
-- T3. Every Waymo deployment quarter has month, trip and incident data.
SELECT 'T3 coverage: deployment ' || q.quarter,
       CASE WHEN m.n > 0 AND t.n > 0 AND i.n > 0 THEN 'PASS'
            WHEN m.n > 0 AND t.n > 0 THEN 'WARN' ELSE 'FAIL' END,
       'month rows ' || coalesce(m.n, 0) || ', trip groups ' || coalesce(t.n, 0) || ', incident source rows ' || coalesce(i.n, 0)
FROM (SELECT DISTINCT quarter FROM fact_service_month WHERE program = 'deployment') q
LEFT JOIN (SELECT quarter, count(*) n FROM fact_service_month WHERE program='deployment' AND mode='driverless' GROUP BY 1) m USING (quarter)
LEFT JOIN (SELECT quarter, count(*) n FROM fact_trip_outcome_q WHERE program='deployment' AND mode='driverless' GROUP BY 1) t USING (quarter)
LEFT JOIN (SELECT quarter, sum(source_rows) - 1 n FROM fact_incident_q WHERE program='deployment' AND mode='driverless' GROUP BY 1) i USING (quarter)

UNION ALL
-- T4. No negative counts or miles.
SELECT 'T4 no negative values in fact_service_month',
       CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END, count(*) || ' rows with a negative value'
FROM fact_service_month
WHERE trips < 0 OR vmt_p1 < 0 OR vmt_p2 < 0 OR vmt_p3 < 0 OR passengers < 0

UNION ALL
-- T5. Fulfilled flag only takes expected values.
SELECT 'T5 fulfilled flag values', CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END,
       coalesce(string_agg(DISTINCT coalesce(fulfilled, 'NULL'), ', '), 'none unexpected')
FROM fact_trip_outcome_q WHERE coalesce(fulfilled, 'NULL') NOT IN ('Y', 'N', 'REDACTED')

UNION ALL
-- T6. Every unfulfilled request has a reason.
SELECT 'T6 unfulfilled requests have a reason',
       CASE WHEN sum(requests) FILTER (WHERE fulfilled = 'N' AND reason_unfulfilled = '(none)') = 0 THEN 'PASS' ELSE 'WARN' END,
       coalesce(sum(requests) FILTER (WHERE fulfilled = 'N' AND reason_unfulfilled = '(none)'), 0) || ' unfulfilled requests without a reason'
FROM fact_trip_outcome_q

UNION ALL
-- T7. Federal crash list covers every month Dec 2024 - Jun 2026 for California.
SELECT 'T7 federal crash months (CA, Dec 2024-Jun 2026)',
       CASE WHEN count(DISTINCT month_start) = 19 THEN 'PASS' ELSE 'FAIL' END,
       count(DISTINCT month_start) || ' of 19 months present'
FROM fact_federal_crash_m WHERE state = 'California' AND month_start BETWEEN DATE '2024-12-01' AND DATE '2026-06-01'

UNION ALL
-- T8. Pilot companies: every company-quarter in the parsed workbooks has metrics.
SELECT 'T8 pilot metrics: ' || company, CASE WHEN count(DISTINCT quarter) >= 1 THEN 'PASS' ELSE 'FAIL' END,
       count(DISTINCT quarter) || ' quarters: ' || string_agg(DISTINCT quarter, ', ' ORDER BY quarter)
FROM fact_pilot_metrics_q GROUP BY company

UNION ALL
-- T9. Answer-key spot checks (numbers verified independently during profiling).
SELECT 'T9 answer key: 2026Q2 completed trips = 4,220,075',
       CASE WHEN sum(trips) = 4220075 THEN 'PASS' ELSE 'FAIL' END, 'got ' || sum(trips)
FROM fact_service_month WHERE program = 'deployment' AND mode = 'driverless' AND quarter = '2026Q2'
UNION ALL
SELECT 'T9 answer key: 2025Q4 collisions = 266',
       CASE WHEN sum(collisions) = 266 THEN 'PASS' ELSE 'FAIL' END, 'got ' || sum(collisions)
FROM fact_incident_q WHERE program = 'deployment' AND mode = 'driverless' AND quarter = '2025Q4';

SELECT result, test, detail FROM test_results ORDER BY result = 'PASS', test;
-- Export the results so the report's Methods page can show them (run from the repo root).
COPY (SELECT result, test, detail FROM test_results ORDER BY test) TO 'data/model/test_results.csv' (HEADER);
SELECT result, count(*) AS tests FROM test_results GROUP BY result ORDER BY result;