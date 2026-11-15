select
    quarter, company, mode, metric,
    try_cast(value as double) as value,
    layout, source_file
from {{ source('landed', 'raw_pilot_metrics') }}
