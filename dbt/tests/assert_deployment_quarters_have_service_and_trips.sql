-- T3a: every deployment quarter must have month data and trip data.
select q.quarter
from (select distinct quarter from {{ ref('fact_service_month') }} where program = 'deployment') q
left join (
    select quarter, count(*) as n from {{ ref('fact_service_month') }}
    where program = 'deployment' and mode = 'driverless' group by 1
) m using (quarter)
left join (
    select quarter, count(*) as n from {{ ref('fact_trip_outcome_q') }}
    where program = 'deployment' and mode = 'driverless' group by 1
) t using (quarter)
where coalesce(m.n, 0) = 0 or coalesce(t.n, 0) = 0
