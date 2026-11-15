select
    quarter, company, program, mode,
    upper(trim(trip_fulfilled)) as fulfilled,
    coalesce(nullif(trim(reason_unfulfilled), ''), '(none)') as reason_unfulfilled,
    upper(trim(wav_req))         as wav_requested,
    upper(trim(shared_provided)) as shared,
    upper(trim(fared_ride))      as fared
from {{ source('landed', 'raw_trips') }}
where tcpid is not null and trim(tcpid) <> ''
