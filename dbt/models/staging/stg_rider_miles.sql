select area, try_cast(rider_only_miles_millions as double) as rider_only_miles_millions
from {{ source('landed', 'raw_waymo_rider_miles') }}
