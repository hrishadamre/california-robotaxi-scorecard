-- One row per reported event. Count the Y flags, never the rows.
select
    quarter, company, program, mode,
    {{ any_yes(['collision_occupant', 'collision_pedestrian', 'collision_bicycle_scooter',
                'collision_motorcycles', 'collision_other_vehicle', 'collision_rail',
                'collision_property']) }} as collision,
    {{ any_yes(['severity_injury_possible', 'severity_injury_minor',
                'severity_injury_severe', 'severity_fatality']) }} as injury_collision,
    {{ is_yes('severity_injury_severe') }}   as severe_injury_collision,
    {{ is_yes('collision_pedestrian') }}     as pedestrian_collision,
    {{ is_yes('collision_bicycle_scooter') }} as bike_scooter_collision,
    {{ is_yes('complaint_safety') }}         as complaint_safety,
    {{ is_yes('complaint_pudo') }}           as complaint_pickup_dropoff,
    {{ is_yes('complaint_customer_service') }} as complaint_customer_service,
    (({{ is_yes('complaint_accessibility') }} + {{ is_yes('complaint_wav') }}) > 0)::int as complaint_accessibility,
    {{ is_yes('complaint_other') }}          as complaint_other,
    {{ is_yes('citation') }}                 as citation
from {{ source('landed', 'raw_incidents') }}
where tcpid is not null and trim(tcpid) <> ''
