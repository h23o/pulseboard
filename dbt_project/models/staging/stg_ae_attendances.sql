/*
stg_ae_attendances – Staging model for NHS A&E raw attendance data.

Transformations applied
────────────────────────
1. period       → month_date (DATE, truncated to first day of month)
2. type*_att    → INTEGER, with '-' / blanks treated as NULL
3. type*_4hr    → INTEGER, same null handling
4. org_code     → UPPER + TRIM
5. org_name     → INITCAP
6. Header rows and null org_code rows are filtered out
*/

with

source as (

    select *
    from {{ source('raw_data', 'ae_attendances') }}

),

cleaned as (

    select

        -- ── Date ──────────────────────────────────────────────────────────
        -- The period field can look like:
        --   "MSitAE-MARCH-2026"  (current format)
        --   "March 2019"         (older monthly CSVs)
        -- We attempt to cast via TO_DATE; rows where this fails are kept
        -- but month_date will be null (flagged by not_null test).
        case
            when period ~* '^MSitAE-[A-Z]+-[0-9]{4}$'
                then to_date(
                        regexp_replace(period, '^MSitAE-', '', 'i'),
                        'MONTH-YYYY'
                     )
            when period ~* '^[A-Z]+ [0-9]{4}$'
                then to_date(period, 'Month YYYY')
            else null
        end                                                     as month_date,

        -- ── Organisation ──────────────────────────────────────────────────
        upper(trim(org_code))                                   as org_code,
        initcap(trim(org_name))                                 as trust_name,

        -- ── Attendance counts ─────────────────────────────────────────────
        nullif(trim(type1_att), '-')::integer                   as type1_attendances,
        nullif(trim(type1_4hr), '-')::integer                   as type1_within_4hr,

        nullif(trim(type2_att), '-')::integer                   as type2_attendances,
        nullif(trim(type2_4hr), '-')::integer                   as type2_within_4hr,

        nullif(trim(other_att), '-')::integer                   as other_attendances,
        nullif(trim(other_4hr), '-')::integer                   as other_within_4hr,

        -- ── Audit columns ─────────────────────────────────────────────────
        _source_file,
        _ingested_at

    from source

    -- Remove header rows and blanks that slipped through ingestion
    where
        org_code is not null
        and trim(org_code) != ''
        and upper(trim(org_code)) not in ('ORG CODE', 'CODE', 'ORGCODE')

)

select * from cleaned
