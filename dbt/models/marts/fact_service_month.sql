select
    quarter, company, program, mode, year, month,
    make_date(year, month, 1) as month_start,
    sum(trips) as trips, sum(waiting_h) as waiting_h,
    sum(vmt_p1) as vmt_p1, sum(vmt_p2) as vmt_p2, sum(vmt_p3) as vmt_p3, sum(vmt_zev) as vmt_zev,
    sum(passengers) as passengers, sum(pmt) as pmt,
    sum(wav_requested) as wav_requested, sum(wav_fulfilled) as wav_fulfilled,
    string_agg(distinct source_file, ' | ') as source_files
from (
    select * from {{ ref('stg_month') }}
    union all by name
    select * from {{ ref('stg_pilot_month') }}
)
group by all
