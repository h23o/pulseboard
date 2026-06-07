"""
load_raw.py – Load normalised DataFrames into raw.ae_attendances.

Design principles
──────────────────
* Append-only: raw.ae_attendances is never truncated or updated.
* Idempotent:  if a source_file has already been loaded, all its rows are
               skipped — re-running the script is safe.
* Auditable:   every row carries _ingested_at (timestamp) and _source_file
               so downstream models know the provenance of each record.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_URL
from fetch_nhs import fetch_all_csvs
from normalise import normalise_csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

RAW_TABLE   = "ae_attendances"
RAW_SCHEMA  = "raw"


def _get_engine():
    """Return a SQLAlchemy engine connected to the PulseBoard database."""
    return create_engine(DB_URL, pool_pre_ping=True)


def _already_loaded(engine, source_file: str) -> bool:
    """
    Return True if *source_file* already has rows in raw.ae_attendances.

    Parameters
    ----------
    engine:      Active SQLAlchemy engine.
    source_file: Basename of the CSV file (used as the idempotency key).

    Returns
    -------
    True if at least one row with _source_file = source_file exists.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT 1 FROM raw.ae_attendances "
                "WHERE _source_file = :sf LIMIT 1"
            ),
            {"sf": source_file},
        )
        return result.fetchone() is not None


def load_to_raw(df: pd.DataFrame, source_file: str) -> int:
    """
    Insert *df* into raw.ae_attendances, tagging each row with metadata.

    The load is skipped entirely if *source_file* was already loaded on a
    previous run (idempotent behaviour).

    Parameters
    ----------
    df:          Clean DataFrame produced by ``normalise_csv``.
    source_file: Logical name of the source file (used as idempotency key
                 and stored in ``_source_file``).  Typically the basename.

    Returns
    -------
    Number of rows actually inserted (0 if the file was already loaded).
    """
    engine = _get_engine()

    if _already_loaded(engine, source_file):
        log.info("Skipping %s – already in raw table.", source_file)
        return 0

    load_df = df.copy()
    load_df["_ingested_at"] = datetime.now(tz=timezone.utc).isoformat()
    load_df["_source_file"] = source_file

    # Reorder to match table column order
    cols = [
        "_ingested_at", "_source_file",
        "period", "org_code", "org_name",
        "type1_att", "type1_4hr",
        "type2_att", "type2_4hr",
        "other_att", "other_4hr",
    ]
    # Only include columns that exist in both df and the target column list
    insert_cols = [c for c in cols if c in load_df.columns]
    load_df = load_df[insert_cols]

    load_df.to_sql(
        name=RAW_TABLE,
        con=engine,
        schema=RAW_SCHEMA,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )

    row_count = len(load_df)
    log.info("Inserted %d rows from %s.", row_count, source_file)
    return row_count


def main() -> None:
    """
    End-to-end pipeline: fetch CSVs → normalise → load to raw.

    1. Calls ``fetch_all_csvs`` to download any new NHS files.
    2. For each file, calls ``normalise_csv`` to clean it.
    3. Calls ``load_to_raw`` to insert into raw.ae_attendances.

    Files already present in data/raw/ are not re-downloaded.
    Files already loaded into the database are not re-inserted.
    """
    log.info("═══ PulseBoard ingestion pipeline start ═══")

    local_files = fetch_all_csvs()
    if not local_files:
        log.warning("No CSV files found. Exiting.")
        return

    total_inserted = 0
    for filepath in local_files:
        try:
            df = normalise_csv(filepath)
            if df.empty:
                log.warning("Empty DataFrame from %s – skipping.", filepath.name)
                continue
            inserted = load_to_raw(df, source_file=filepath.name)
            total_inserted += inserted
        except Exception as exc:
            log.error("Failed to process %s: %s", filepath.name, exc, exc_info=True)
            continue

    log.info("═══ Pipeline complete. %d total rows inserted. ═══", total_inserted)


if __name__ == "__main__":
    main()
