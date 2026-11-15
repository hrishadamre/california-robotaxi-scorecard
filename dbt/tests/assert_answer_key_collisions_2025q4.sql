-- T9b: 2025 Q4 paid driverless collisions = 266 (verified independently).
select sum(collisions) as got
from {{ ref('fact_incident_q') }}
where program = 'deployment' and mode = 'driverless' and quarter = '2025Q4'
having sum(collisions) <> 266
