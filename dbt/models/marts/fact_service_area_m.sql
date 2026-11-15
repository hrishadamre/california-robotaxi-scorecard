select distinct
    quarter, company, program, mode, year, month,
    make_date(year, month, 1) as month_start,
    tract, substr(tract, 1, 5) as county_fips, trips_start
from {{ ref('stg_service_area') }}
