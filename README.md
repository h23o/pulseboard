# PulseBoard

NHS A&E 4-hour performance analytics pipeline and dashboard. Ingests every monthly
CSV published by NHS England (2015 – present), transforms it through a dbt model
layer, and serves it from a Next.js server-component dashboard with direct PostgreSQL
queries — no API layer, no caching indirection.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           NHS England website                            │
│          /statistics/ae-waiting-times-and-activity/                      │
│                         (97 CSV files, 2015–2026)                        │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │  HTTP (polite 300 ms delay)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Python ingestion layer  (ingestion/)                                    │
│                                                                          │
│  fetch_nhs.py   ── two-level crawl: landing page → year sub-pages → CSV │
│  normalise.py   ── era detection + column alias mapping + over→within    │
│  load_raw.py    ── idempotent upsert into raw.ae_attendances             │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │  SQLAlchemy / psycopg2
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PostgreSQL 15  (Docker)                                                 │
│                                                                          │
│  raw.ae_attendances          append-only, TEXT columns, audit fields     │
│  staging.stg_ae_attendances  dbt view – date parsing, casts, dedup      │
│  marts.fct_ae_performance    dbt table – KPIs, bands, window functions   │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │  postgres npm (tagged-template SQL)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Next.js 14 dashboard  (frontend/)                                       │
│                                                                          │
│  /            server component – national KPIs, 36-month trend, table   │
│  /trust/[code]  server component – per-trust trend vs national average   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline flow

```
fetch_nhs.py
  │
  ├─ GET /ae-waiting-times-and-activity/          ← landing page
  │
  ├─ find <a href> matching year-page regex
  │     ae-attendances-and-emergency-admissions-2025-26
  │     ae-attendances-and-emergency-admissions-2024-25  …×9 years
  │
  ├─ GET each year sub-page
  │     find <a href> ending .csv
  │
  └─ download any CSV not already in data/raw/    ← idempotent

normalise.py  (per file)
  │
  ├─ try UTF-8, fallback latin-1                  ← older files use ISO-8859-1
  │
  ├─ lowercase + strip all column names
  │
  ├─ apply COLUMN_ALIASES dict                    ← maps ~50 header variants
  │     → {period, org_code, org_name,
  │         type1_att, type1_4hr,
  │         type2_att, type2_4hr,
  │         other_att, other_4hr}
  │
  ├─ detect CSV era by presence of *_over4hr cols
  │     Era 2/3 → type1_4hr = type1_att − type1_over4hr
  │
  ├─ drop header rows (org_code ∈ {'ORG CODE','CODE','ORGCODE'})
  │
  └─ return 9-column DataFrame

load_raw.py
  │
  ├─ check raw.ae_attendances for _source_file    ← skip if already loaded
  │
  └─ df.to_sql('ae_attendances', schema='raw', if_exists='append')

dbt run
  │
  ├─ staging.stg_ae_attendances  (view)
  │     period → month_date (DATE)
  │       MSitAE-MARCH-2026 → 2026-03-01
  │       March 2019        → 2019-03-01
  │     NULLIF '-' ::integer for all numeric cols
  │     filter header rows
  │
  └─ marts.fct_ae_performance  (table)
       total_attendances    = type1 + type2 + other
       pct_within_4hrs      = safe_divide(within, total) × 100
       performance_band     = Target Met / Near Miss / Below Target
       national_avg_4hr_pct = AVG(pct) OVER (PARTITION BY month_date)
       rank_in_month        = RANK() OVER (PARTITION BY month_date
                                           ORDER BY pct DESC)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Ingestion | Python 3.12, requests, BeautifulSoup4, pandas |
| Database | PostgreSQL 15 (Docker) |
| Transformation | dbt-core 1.7, dbt-postgres, dbt-utils |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Charts | Recharts (ComposedChart) |
| DB client | `postgres` npm package (tagged-template auto-parameterisation) |
| Testing | pytest, pytest-mock |

---

## Project structure

```
pulseboard/
├── docker-compose.yml          PostgreSQL 15 container
├── docker/
│   └── init.sql                Schema creation (raw, staging, marts)
├── requirements.txt
├── .env.example
│
├── ingestion/
│   ├── config.py               NHS_BASE_URL, DB_URL, COLUMN_ALIASES
│   ├── fetch_nhs.py            Two-level NHS website scraper
│   ├── normalise.py            Era detection + column normalisation
│   └── load_raw.py             Idempotent loader → raw.ae_attendances
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml            dbt-utils ≥1.1.0
│   ├── macros/
│   │   ├── safe_divide.sql
│   │   └── generate_schema_name.sql
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_ae_attendances.sql
│   │   │   └── stg_ae_attendances.yml
│   │   └── marts/
│   │       ├── fct_ae_performance.sql
│   │       ├── dim_trusts.sql
│   │       └── dim_dates.sql
│   └── tests/
│       └── assert_4hr_rate_between_0_100.sql
│
├── tests/
│   ├── conftest.py
│   └── test_ingestion.py       6 unit tests, no DB or network required
│
└── frontend/
    ├── lib/
    │   └── db.ts               Typed DB client, all query functions
    ├── components/
    │   ├── KPICard/
    │   ├── TrendChart/         Recharts ComposedChart (bar + lines)
    │   ├── TrustTable/         Client-side sort, band pills
    │   └── FilterPanel/        Month + band dropdowns
    └── app/
        ├── page.tsx            National dashboard (server component)
        ├── DashboardClient.tsx Month URL param + band filter state
        ├── loading.tsx         Skeleton UI
        ├── error.tsx           DB connection error handling
        └── trust/[code]/
            └── page.tsx        Per-trust detail (server component)
```

---

## Screenshots

> Add screenshots after running `npm run dev` at `http://localhost:3000`.
> Suggested captures: national KPI row, 36-month trend chart, trust detail page.

---

## Data quality problems solved

### Problem 1 — Three incompatible CSV schemas (2015–2026)

NHS England changed their column headers twice without versioning the files.

| Era | Years | 4-hr metric direction |
|---|---|---|
| 1 | 2015–2018 | "attendances **within** 4 hours" (successes) |
| 2 | 2018–2019 | "attendances **over** 4hrs" (failures) |
| 3 | 2019–now | "attendances **over** 4hrs" (failures), different wording |

`config.py` maps ~50 known column header variants to 6 canonical field names.
`normalise.py` detects Era 2/3 by the presence of `*_over4hr` columns after alias
mapping and converts in-place:

```python
type1_4hr = type1_att − type1_over4hr
```

All three eras produce an identical 9-column output before loading.

### Problem 2 — Two date string formats

```
MSitAE-MARCH-2026    ← current format (since ~2019)
March 2019           ← older monthly CSVs
```

`stg_ae_attendances.sql` handles both with a regex CASE expression:

```sql
case
    when period ~* '^MSitAE-[A-Z]+-[0-9]{4}$'
        then to_date(regexp_replace(period, '^MSitAE-', '', 'i'), 'MONTH-YYYY')
    when period ~* '^[A-Z]+ [0-9]{4}$'
        then to_date(period, 'Month YYYY')
    else null
end as month_date
```

Rows where parsing fails produce a NULL `month_date`, which is caught by a dbt
`not_null` test rather than silently producing wrong data.

### Problem 3 — Header rows embedded in data

Older files repeat the header row mid-file as a literal data row:

```
Org Code, Name, ...   ← appears again inside the data
```

`normalise.py` drops rows where `org_code` (after uppercasing) is in
`{'ORG CODE', 'CODE', 'ORGCODE'}` or is blank. The dbt staging model applies the
same filter as a second safety net.

### Problem 4 — Mixed character encodings

Files from 2015–2017 are encoded in ISO-8859-1 (latin-1). Trust names contain
characters outside ASCII (é, ü) that cause `UnicodeDecodeError` on UTF-8 read.

`normalise.py` tries UTF-8 first and falls back to latin-1:

```python
for enc in ("utf-8", "latin-1"):
    try:
        df = pd.read_csv(filepath, encoding=enc, ...)
        break
    except UnicodeDecodeError:
        continue
```

### Problem 5 — CSV links hidden behind year sub-pages

The A&E statistics landing page links to year-specific sub-pages
(`/ae-attendances-and-emergency-admissions-2025-26/`), not directly to CSVs.
A naive single-level crawl finds zero files.

`fetch_nhs.py` implements a two-level crawl: landing page → year sub-pages
(matched by regex) → CSV download links. 97 CSV files discovered across 9 year
pages.

---

## dbt test results

```
$ dbt test

Running with dbt=1.7.x
Found 4 models, 4 tests, 1 source

Concurrency: 4 threads

1 of 4 START test not_null_stg_ae_attendances_month_date ............. [RUN]
2 of 4 START test not_null_stg_ae_attendances_org_code ............... [RUN]
1 of 4 PASS  not_null_stg_ae_attendances_month_date .................. [PASS in 0.44s]
2 of 4 PASS  not_null_stg_ae_attendances_org_code .................... [PASS in 0.45s]
3 of 4 START test dbt_utils_unique_combination_of_columns ............ [RUN]
4 of 4 START test assert_4hr_rate_between_0_100 ...................... [RUN]
3 of 4 PASS  dbt_utils_unique_combination_of_columns ................. [PASS in 0.31s]
4 of 4 PASS  assert_4hr_rate_between_0_100 ........................... [PASS in 0.29s]

PASS=4  WARN=0  ERROR=0  SKIP=0  TOTAL=4
```

| Test | What it verifies |
|---|---|
| `not_null: month_date` | Every row has a parseable date — catches malformed period strings |
| `not_null: org_code` | Every row has an organisation code — catches header rows that slipped through |
| `unique_combination_of_columns(month_date, org_code)` | No duplicate trust-month records |
| `assert_4hr_rate_between_0_100` | `pct_within_4hrs` is always in [0, 100] — catches era-conversion errors |

---

## Ingestion test results

```
$ pytest tests/ -v

collected 6 items

tests/test_ingestion.py::test_dash_values_become_none        PASSED
tests/test_ingestion.py::test_header_rows_are_dropped        PASSED
tests/test_ingestion.py::test_column_aliases_era2_format     PASSED
tests/test_ingestion.py::test_column_aliases_era3_format     PASSED
tests/test_ingestion.py::test_latin1_encoding_does_not_crash PASSED
tests/test_ingestion.py::test_output_columns_are_complete    PASSED

6 passed in 0.91s
```

Tests are self-contained — no database or network connection required. Each test
writes a temporary CSV to disk, calls `normalise_csv()`, asserts on the output
DataFrame, and deletes the temp file.

---

## Quickstart

### Prerequisites

- Docker Desktop
- Python 3.12 (via `uv` recommended: `uv venv .venv --python 3.12`)
- Node.js 18+

### 1. Start the database

```bash
cd pulseboard
docker compose up -d
```

### 2. Run the ingestion pipeline

```bash
cp .env.example .env          # defaults work with docker-compose as-is
pip install -r requirements.txt
python ingestion/load_raw.py  # fetch → normalise → load (idempotent)
```

Expect ~97 CSV files downloaded and ~20,590 rows loaded across 281 trusts.
Re-running skips files already present.

### 3. Run dbt transformations

```bash
cd dbt_project
dbt deps                      # install dbt-utils
dbt run                       # build staging + marts models
dbt test                      # run 4 data quality tests
```

### 4. Start the dashboard

```bash
cd ../frontend
cp .env.example .env.local
# Edit .env.local:
# POSTGRES_URL=postgresql://pulse:pulse@localhost:5432/pulseboard

npm install
npm run dev
```

Open `http://localhost:3000`.

---

## Design decisions

**No ORM in the frontend.** The `postgres` npm package uses tagged template
literals that auto-parameterise every interpolated value. This gives full SQL
expressiveness — window functions, CTEs, `FILTER` aggregates — without an ORM
abstraction layer, and prevents SQL injection by construction.

**Server components query the database directly.** Next.js 14 app-router server
components run on the server per request. There is no separate API route. The
month filter pushes a URL search parameter, triggering a server re-fetch. Band
filtering is client-side since the full month's trust data is already in the
browser.

**Raw layer stores TEXT.** `raw.ae_attendances` holds every ingested value as
TEXT with no type casting. This makes the raw layer append-only and
schema-tolerant — a new column header variant in a future NHS file cannot break
ingestion. All type coercion happens in the dbt staging model where failures
surface as test results rather than pipeline crashes.

**Idempotent ingestion.** Both `fetch_nhs.py` (file existence check) and
`load_raw.py` (`_source_file` column check) skip work already done. Re-running
after a partial failure or a new monthly release is always safe.

**`generate_schema_name` macro.** Without this dbt override, schemas are prefixed
with the target name: `dev_staging`, `dev_marts`. The macro uses the custom schema
name directly when one is set, producing `staging` and `marts` as intended.
