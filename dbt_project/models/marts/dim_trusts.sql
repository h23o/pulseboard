/*
dim_trusts – Slowly-changing dimension for NHS trusts.

Grain:     One row per unique org_code.
Source:    {{ ref('stg_ae_attendances') }}

Because NHS England occasionally updates trust names (mergers, renames), we
take the most recent name observed in the staging data using DISTINCT ON.
*/

with

latest as (

    select distinct on (org_code)
        org_code,
        trust_name,
        month_date      as last_seen_month,
        _ingested_at    as last_ingested_at
    from {{ ref('stg_ae_attendances') }}
    where org_code is not null
    order by org_code, month_date desc nulls last

)

select
    org_code,
    trust_name,
    last_seen_month,
    last_ingested_at

from latest
