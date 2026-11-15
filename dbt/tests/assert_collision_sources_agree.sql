-- T2: collisions from incident flags vs the census-tract table. A difference is a warning, not a failure.
{{ config(severity='warn') }}
select i.quarter, i.program, i.collisions as incident_flags, l.c as tract_table
from (
    select quarter, program, sum(collisions) as collisions
    from {{ ref('fact_incident_q') }}
    where company = 'Waymo' and mode = 'driverless'
    group by all
) i
join (
    select quarter, program, sum(collisions_all) as c
    from {{ ref('fact_tract_q') }}
    where company = 'Waymo' and mode = 'driverless'
    group by all
) l using (quarter, program)
where i.collisions is distinct from l.c
