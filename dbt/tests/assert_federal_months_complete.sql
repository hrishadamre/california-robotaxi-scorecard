-- T7: the federal crash file covers all 19 months, Dec 2024 to Jun 2026, for California.
select count(distinct month_start) as months_present
from {{ ref('fact_federal_crash_m') }}
where state = 'California' and month_start between date '2024-12-01' and date '2026-06-01'
having count(distinct month_start) <> 19
