/*
fct_ae_performance – Trust-level A&E 4-hour performance fact table.

Grain:       One row per trust (org_code) per calendar month (month_date).
Source:      {{ ref('stg_ae_attendances') }}

Metrics produced
─────────────────
total_attendances    INTEGER   Sum of Type 1 + Type 2 + Other attendances.
total_within_4hr     INTEGER   Sum of within-4-hour counts across all types.
pct_within_4hrs      NUMERIC   Percentage of attendances within 4 hours.
performance_band     TEXT      "Target Met" / "Near Miss" / "Below Target"
national_avg_4hr_pct NUMERIC   National average pct_within_4hrs for the month
                               (window function, all trusts equal weight).
rank_in_month        INTEGER   Trust rank within the month (1 = best performer).
*/

with

stg as (

    select *
    from {{ ref('stg_ae_attendances') }}
    where month_date is not null
      and org_code   is not null

),

aggregated as (

    select

        month_date,
        org_code,
        trust_name,

        -- ── Attendance totals ──────────────────────────────────────────────
        coalesce(type1_attendances, 0)
            + coalesce(type2_attendances, 0)
            + coalesce(other_attendances, 0)                    as total_attendances,

        coalesce(type1_within_4hr, 0)
            + coalesce(type2_within_4hr, 0)
            + coalesce(other_within_4hr, 0)                     as total_within_4hr,

        -- ── Individual type metrics (kept for drill-down) ─────────────────
        type1_attendances,
        type1_within_4hr,
        type2_attendances,
        type2_within_4hr,
        other_attendances,
        other_within_4hr,

        _source_file,
        _ingested_at

    from stg

),

with_pct as (

    select

        *,

        -- ── 4-hour performance percentage ─────────────────────────────────
        round(
            {{ safe_divide('total_within_4hr', 'total_attendances', scale=100) }},
            2
        )                                                       as pct_within_4hrs

    from aggregated

),

with_bands as (

    select

        *,

        -- ── Performance banding ───────────────────────────────────────────
        -- NHS target: 95 % within 4 hours (4-hour standard)
        case
            when pct_within_4hrs >= 95   then 'Target Met'
            when pct_within_4hrs >= 85   then 'Near Miss'
            else                              'Below Target'
        end                                                     as performance_band,

        -- ── National average for the month (equal-weight across trusts) ───
        round(
            avg(pct_within_4hrs) over (partition by month_date),
            2
        )                                                       as national_avg_4hr_pct,

        -- ── Trust rank within month (1 = highest % within 4hrs) ──────────
        rank() over (
            partition by month_date
            order by pct_within_4hrs desc nulls last
        )                                                       as rank_in_month

    from with_pct

)

select
    month_date,
    org_code,
    trust_name,
    total_attendances,
    total_within_4hr,
    pct_within_4hrs,
    performance_band,
    national_avg_4hr_pct,
    rank_in_month,
    type1_attendances,
    type1_within_4hr,
    type2_attendances,
    type2_within_4hr,
    other_attendances,
    other_within_4hr,
    _source_file,
    _ingested_at

from with_bands
