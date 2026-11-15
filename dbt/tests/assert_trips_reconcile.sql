-- T1: completed trips in the trip-level files equal the month files, every Waymo quarter.
with trips as (
    select quarter, program, mode, sum(requests) filter (where fulfilled = 'Y') as fulfilled
    from {{ ref('fact_trip_outcome_q') }}
    where company = 'Waymo'
    group by all
),
months as (
    select quarter, program, mode, sum(trips) as month_trips
    from {{ ref('fact_service_month') }}
    where company = 'Waymo'
    group by all
)
select t.quarter, t.program, t.mode, t.fulfilled, m.month_trips
from trips t
join months m using (quarter, program, mode)
where t.fulfilled > 0 and t.fulfilled <> m.month_trips
