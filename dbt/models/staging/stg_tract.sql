select
    quarter, company, program, mode,
    lpad(trim(tract), 11, '0') as tract,
    {{ to_number('collisions_all') }}  as collisions_all,
    {{ to_number('collisions_pudo') }} as collisions_pickup_dropoff
from {{ source('landed', 'raw_incident_tract') }}
where regexp_full_match(trim(tract), '[0-9]{9,11}')
