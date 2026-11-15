select
    year, month, month_start, state, county, road_type, crash_type, sgo_rule_version,
    count(*) as crashes,
    sum(injury_crash)          as injury_crashes,
    sum(police_reported_crash) as police_reported_crashes,
    sum(serious_injury_crash)  as serious_injury_crashes,
    sum(airbag_crash)          as airbag_crashes
from {{ ref('stg_federal') }}
group by all
