select
    quarter, company, program, mode,
    {{ to_number('year') }}::int  as year,
    {{ to_number('month') }}::int as month,
    {{ to_number('total_trips') }}         as trips,
    {{ to_number('total_waiting') }}       as waiting_h,
    {{ to_number('total_vmt_p1') }}        as vmt_p1,
    {{ to_number('total_vmt_p2') }}        as vmt_p2,
    {{ to_number('total_vmt_p3') }}        as vmt_p3,
    {{ to_number('total_vmt_zev') }}       as vmt_zev,
    {{ to_number('total_passengers') }}    as passengers,
    {{ to_number('total_pmt') }}           as pmt,
    {{ to_number('total_wav_requested') }} as wav_requested,
    {{ to_number('total_wav_fulfilled') }} as wav_fulfilled,
    source_file
from {{ source('landed', 'raw_month') }}
where {{ to_number('total_trips') }} is not null
