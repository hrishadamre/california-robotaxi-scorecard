select county_fips, county_name, region
from {{ ref('ca_counties') }}
