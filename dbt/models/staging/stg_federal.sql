-- Street descriptions and ZIP codes were never landed, so they cannot appear here.
select
    try_cast(substr(year_month, 1, 4) as int) as year,
    try_cast(substr(year_month, 5, 2) as int) as month,
    make_date(try_cast(substr(year_month, 1, 4) as int), try_cast(substr(year_month, 5, 2) as int), 1) as month_start,
    state, county, road_type, crash_type,
    sgo_amendment as sgo_rule_version,
    (is_any_injury = 'True')::int      as injury_crash,
    (is_police_reported = 'True')::int as police_reported_crash,
    (is_serious_injury = 'True')::int  as serious_injury_crash,
    (is_airbag = 'True')::int          as airbag_crash
from {{ source('landed', 'raw_waymo_federal') }}
