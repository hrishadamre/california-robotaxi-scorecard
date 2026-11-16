{% test unique_grain(model, columns) %}
-- Returns any combination of the grain columns that appears more than once.
-- The test passes only when no rows come back.
select
    {{ columns | join(', ') }},
    count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}