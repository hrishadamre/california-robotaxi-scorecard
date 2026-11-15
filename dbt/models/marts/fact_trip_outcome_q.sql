select
    quarter, company, program, mode, fulfilled, reason_unfulfilled,
    wav_requested, shared, fared,
    count(*) as requests
from {{ ref('stg_trips') }}
group by all
