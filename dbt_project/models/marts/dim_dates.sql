/*
dim_dates – Date dimension spanning the range of months in the dataset.

Grain:     One row per calendar month present in the fact table.
Source:    {{ ref('fct_ae_performance') }}

Derived attributes (useful for dashboard filtering / grouping)
──────────────────────────────────────────────────────────────
year            INTEGER   e.g. 2026
month_num       INTEGER   1–12
month_name      TEXT      e.g. 'March'
quarter         INTEGER   1–4
quarter_label   TEXT      e.g. 'Q4 2025/26' (UK NHS financial year)
financial_year  TEXT      e.g. '2025/26'     (Apr–Mar)
is_covid_period BOOLEAN   TRUE for Apr 2020 – Mar 2022
*/

with

months as (

    select distinct month_date
    from {{ ref('fct_ae_performance') }}
    where month_date is not null

)

select

    month_date,

    extract(year  from month_date)::integer                 as year,
    extract(month from month_date)::integer                 as month_num,
    to_char(month_date, 'Month')                            as month_name,

    -- Calendar quarter
    extract(quarter from month_date)::integer               as quarter,

    -- NHS financial year runs Apr–Mar (e.g. Apr 2025 → '2025/26')
    case
        when extract(month from month_date) >= 4
            then extract(year from month_date)::integer
        else extract(year from month_date)::integer - 1
    end                                                     as fin_year_start,

    case
        when extract(month from month_date) >= 4
            then (extract(year from month_date)::integer + 1)
        else extract(year from month_date)::integer
    end                                                     as fin_year_end,

    -- NHS financial quarter (Q1 = Apr–Jun, Q4 = Jan–Mar)
    case
        when extract(month from month_date) between 4 and 6   then 1
        when extract(month from month_date) between 7 and 9   then 2
        when extract(month from month_date) between 10 and 12 then 3
        else 4
    end                                                     as fin_quarter,

    -- Human-readable labels computed in a second pass below
    month_date                                              as month_date_key

from months
