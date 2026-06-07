-- PulseBoard database initialisation
-- Creates schemas and raw tables on first container start

-- ── Schemas ────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- ── Raw layer ──────────────────────────────────────────────────────────────
-- Append-only landing table for NHS A&E CSV data.
-- All values stored as TEXT; dbt staging models cast + clean them.
CREATE TABLE IF NOT EXISTS raw.ae_attendances (
    _ingested_at    TIMESTAMPTZ DEFAULT NOW(),
    _source_file    TEXT,
    period          TEXT,
    org_code        TEXT,
    org_name        TEXT,
    type1_att       TEXT,
    type1_4hr       TEXT,
    type2_att       TEXT,
    type2_4hr       TEXT,
    other_att       TEXT,
    other_4hr       TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_ae_period ON raw.ae_attendances(period);
CREATE INDEX IF NOT EXISTS idx_raw_ae_org    ON raw.ae_attendances(org_code);
CREATE INDEX IF NOT EXISTS idx_raw_ae_source ON raw.ae_attendances(_source_file);
