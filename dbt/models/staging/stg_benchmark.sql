select
    outcome, benchmark_version, area, grouping_type, crash_group,
    try_cast(waymo_count as bigint)           as waymo_count,
    try_cast(waymo_ipmm as double)            as waymo_per_million_miles,
    try_cast(benchmark_ipmm as double)        as benchmark_per_million_miles,
    try_cast(pct_reduction as double)         as pct_difference,
    try_cast(pct_reduction_lower as double)   as pct_difference_low,
    try_cast(pct_reduction_upper as double)   as pct_difference_high
from {{ source('landed', 'raw_waymo_benchmark') }}
