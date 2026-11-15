-- T4: no negative counts or miles.
select *
from {{ ref('fact_service_month') }}
where trips < 0 or vmt_p1 < 0 or vmt_p2 < 0 or vmt_p3 < 0 or passengers < 0
