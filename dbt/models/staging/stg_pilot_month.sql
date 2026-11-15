select
    quarter, company, program, mode,
    try_cast(year as int)  as year,
    try_cast(month as int) as month,
    try_cast(trips as double)         as trips,
    try_cast(waiting_h as double)     as waiting_h,
    try_cast(vmt_p1 as double)        as vmt_p1,
    try_cast(vmt_p2 as double)        as vmt_p2,
    try_cast(vmt_p3 as double)        as vmt_p3,
    try_cast(vmt_zev as double)       as vmt_zev,
    try_cast(passengers as double)    as passengers,
    try_cast(pmt as double)           as pmt,
    try_cast(wav_requested as double) as wav_requested,
    try_cast(wav_fulfilled as double) as wav_fulfilled,
    source_file
from {{ source('landed', 'raw_pilot_month') }}
