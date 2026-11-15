-- One row per (quarter, company, program, mode) that has an incidents file,
-- even if that file has no qualifying rows (then counts are NULL and source_rows is 0).
with files as (
    select distinct quarter, company, program, mode
    from {{ source('landed', 'raw_manifest') }}
    where table_type = 'incidents_complaints'
),
agg as (
    select
        quarter, company, program, mode,
        sum(collision)                as collisions,
        sum(injury_collision)         as injury_collisions,
        sum(severe_injury_collision)  as severe_injury_collisions,
        sum(pedestrian_collision)     as pedestrian_collisions,
        sum(bike_scooter_collision)   as bike_scooter_collisions,
        sum(complaint_safety)         as complaints_safety,
        sum(complaint_pickup_dropoff) as complaints_pickup_dropoff,
        sum(complaint_customer_service) as complaints_customer_service,
        sum(complaint_accessibility)  as complaints_accessibility,
        sum(complaint_other)          as complaints_other,
        sum(citation)                 as citations,
        count(*)                      as source_rows
    from {{ ref('stg_incidents') }}
    group by all
)
select
    f.quarter, f.company, f.program, f.mode,
    a.collisions, a.injury_collisions, a.severe_injury_collisions,
    a.pedestrian_collisions, a.bike_scooter_collisions,
    a.complaints_safety, a.complaints_pickup_dropoff, a.complaints_customer_service,
    a.complaints_accessibility, a.complaints_other, a.citations,
    coalesce(a.source_rows, 0) as source_rows
from files f
left join agg a using (quarter, company, program, mode)
