select
    quarter, company, program, mode, tract, substr(tract, 1, 5) as county_fips,
    sum(collisions_all) as collisions_all,
    sum(collisions_pickup_dropoff) as collisions_pickup_dropoff
from {{ ref('stg_tract') }}
group by all
