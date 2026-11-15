-- T3b: a deployment quarter with no incident rows is a warning (December 2024 has no incident file).
-- source_rows minus 1 removes the placeholder row the original counting produces for an empty file.
{{ config(severity='warn') }}
select q.quarter, coalesce(i.n, 0) as incident_source_rows
from (select distinct quarter from {{ ref('fact_service_month') }} where program = 'deployment') q
left join (
    select quarter, sum(source_rows) - 1 as n from {{ ref('fact_incident_q') }}
    where program = 'deployment' and mode = 'driverless' group by 1
) i using (quarter)
where coalesce(i.n, 0) <= 0
