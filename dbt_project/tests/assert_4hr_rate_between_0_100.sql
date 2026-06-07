/*
assert_4hr_rate_between_0_100

Custom dbt test: every row in fct_ae_performance where pct_within_4hrs is
not null must have a value between 0 and 100 (inclusive).

dbt tests pass when this query returns zero rows.
*/

select
    month_date,
    org_code,
    pct_within_4hrs
from {{ ref('fct_ae_performance') }}
where
    pct_within_4hrs is not null
    and (
        pct_within_4hrs < 0
        or pct_within_4hrs > 100
    )
