-- T9a: 2026 Q2 completed paid driverless trips = 4,220,075 (verified independently).
select sum(trips) as got
from {{ ref('fact_service_month') }}
where program = 'deployment' and mode = 'driverless' and quarter = '2026Q2'
having sum(trips) <> 4220075
