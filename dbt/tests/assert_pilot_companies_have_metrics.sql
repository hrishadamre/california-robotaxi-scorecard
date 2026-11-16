-- Every pilot company we expect must have at least one quarter of metrics.
-- Returns the missing companies; the test fails if any row comes back.
with expected as (
    select unnest(['Nuro', 'Tensor', 'Waymo', 'WeRide', 'Zoox']) as company
),
actual as (
    select distinct company from {{ ref('fact_pilot_metrics_q') }}
)
select e.company
from expected e
left join actual a on e.company = a.company
where a.company is null
