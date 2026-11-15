{# '1,217,872' -> 1217872 ; 'Redacted' or blank -> NULL #}
{% macro to_number(col) -%}
try_cast(replace({{ col }}, ',', '') as double)
{%- endmacro %}

{# 1 when a Y/N flag is 'Y' (any case, any spaces), else 0 #}
{% macro is_yes(col) -%}
coalesce((upper(trim({{ col }})) = 'Y')::int, 0)
{%- endmacro %}

{# 1 when ANY of the listed flag columns is 'Y' #}
{% macro any_yes(cols) -%}
coalesce(({% for c in cols %}upper(trim({{ c }})) = 'Y'{% if not loop.last %} or {% endif %}{% endfor %})::int, 0)
{%- endmacro %}
