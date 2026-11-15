-- T6: every unfulfilled request should have a reason. A gap is a warning.
{{ config(severity='warn') }}
select sum(requests) as unfulfilled_without_reason
from {{ ref('fact_trip_outcome_q') }}
where fulfilled = 'N' and reason_unfulfilled = '(none)'
having sum(requests) > 0
