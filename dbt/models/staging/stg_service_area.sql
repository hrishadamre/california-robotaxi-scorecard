select
    quarter, company, program, mode,
    {{ to_number('year') }}::int  as year,
    {{ to_number('month') }}::int as month,
    lpad(trim(tract), 11, '0') as tract,
    {{ to_number('trips_start') }} as trips_start
from {{ source('landed', 'raw_service_area') }}
where regexp_full_match(trim(tract), '[0-9]{9,11}')
