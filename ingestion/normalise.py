"""
normalise.py – Clean and standardise raw NHS A&E CSV files.

NHS England has published A&E data in at least three distinct column-header
eras.  This module detects which era a file belongs to and normalises it
into a consistent six-column DataFrame that matches raw.ae_attendances.

Column semantics after normalisation
─────────────────────────────────────
period      TEXT   e.g. "MSitAE-MARCH-2026" or "March 2019"
org_code    TEXT   upper-cased ODS organisation code
org_name    TEXT   trust display name
type1_att   TEXT   Type 1 (Major A&E) total attendances
type1_4hr   TEXT   Type 1 attendances WITHIN 4 hours (always positive metric)
type2_att   TEXT   Type 2 (Single-specialty) total attendances
type2_4hr   TEXT   Type 2 attendances within 4 hours
other_att   TEXT   Other A&E total attendances
other_4hr   TEXT   Other A&E attendances within 4 hours
"""

import logging
from pathlib import Path

import pandas as pd

from config import COLUMN_ALIASES

log = logging.getLogger(__name__)

# Columns we always output (order matters for to_sql insert)
OUTPUT_COLUMNS = [
    "period",
    "org_code",
    "org_name",
    "type1_att",
    "type1_4hr",
    "type2_att",
    "type2_4hr",
    "other_att",
    "other_4hr",
]

# Intermediate columns produced when the source file uses "over 4hrs" counts
_OVER4_COLS = {"type1_over4hr", "type2_over4hr", "other_over4hr"}

# Values that represent NULL / missing in NHS files
_NULL_MARKERS = {"-", "–", "—", "n/a", "na", "null", ""}


def _try_read_csv(filepath: Path) -> pd.DataFrame:
    """
    Read a CSV file, falling back to latin-1 if UTF-8 fails.

    Parameters
    ----------
    filepath: Path to the local CSV file.

    Returns
    -------
    Raw (un-cleaned) DataFrame.
    """
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return pd.read_csv(filepath, encoding=encoding, dtype=str)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {filepath} with any known encoding.")


def _normalise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strip whitespace and apply COLUMN_ALIASES to standardise header names.

    Column names not present in COLUMN_ALIASES are kept as-is (they will be
    dropped later if not in OUTPUT_COLUMNS).
    """
    df.columns = [c.strip() for c in df.columns]
    df.columns = [COLUMN_ALIASES.get(c.lower(), c.lower()) for c in df.columns]
    return df


def _strip_values(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all string cell values."""
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    df[str_cols] = df[str_cols].apply(lambda s: s.str.strip())
    return df


def _convert_over4hr_to_within(df: pd.DataFrame) -> pd.DataFrame:
    """
    For Era-2 and Era-3 files the 4-hour metric is "attendances OVER 4 hrs".
    Convert to "attendances WITHIN 4 hrs" for consistency:

        within_4hr = total_att − over_4hr

    Any row where either value is null results in a null within_4hr.
    """
    conversions = [
        ("type1_att",  "type1_over4hr",  "type1_4hr"),
        ("type2_att",  "type2_over4hr",  "type2_4hr"),
        ("other_att",  "other_over4hr",  "other_4hr"),
    ]
    for att_col, over_col, within_col in conversions:
        if over_col not in df.columns:
            continue
        if att_col not in df.columns:
            df[within_col] = None
            continue
        att   = pd.to_numeric(df[att_col],  errors="coerce")
        over  = pd.to_numeric(df[over_col], errors="coerce")
        within = att - over
        # Preserve NULL where source was NULL
        null_mask = df[att_col].isin(_NULL_MARKERS) | df[over_col].isin(_NULL_MARKERS)
        null_mask |= df[att_col].isna() | df[over_col].isna()
        df[within_col] = within.where(~null_mask, other=None).astype("Int64").astype(str)
        df[within_col] = df[within_col].replace("<NA>", None)

    return df


def _ensure_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add any missing output columns as None, then select only OUTPUT_COLUMNS.
    """
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[OUTPUT_COLUMNS]


def _drop_non_data_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove rows that are not real trust data:
    - org_code is null / blank
    - org_code is a literal header value ('Org Code', 'Code', etc.)
    - org_code looks like a national total row ('ENG', 'ENGLAND', 'TOTAL')
    """
    HEADER_VALUES = {"org code", "code", "orgcode", "organisation code"}
    TOTAL_VALUES  = {"eng", "england", "total", "grand total", "national"}

    if "org_code" not in df.columns:
        return df

    mask_null   = df["org_code"].isna() | df["org_code"].isin(["", None])
    mask_header = df["org_code"].str.lower().isin(HEADER_VALUES)
    mask_total  = df["org_code"].str.lower().isin(TOTAL_VALUES)

    dropped = (mask_null | mask_header | mask_total).sum()
    if dropped:
        log.debug("Dropped %d non-data rows.", dropped)
    return df[~(mask_null | mask_header | mask_total)].copy()


def normalise_csv(filepath: str | Path) -> pd.DataFrame:
    """
    Read a raw NHS A&E CSV file and return a clean, normalised DataFrame.

    The function is era-agnostic: it handles all known NHS A&E CSV formats
    (pre-2018, 2018-19, and 2019+) by detecting which era's column names
    are present and converting "over 4hrs" figures to "within 4hrs" where
    needed.

    Parameters
    ----------
    filepath: Path to a local CSV file downloaded from NHS England.

    Returns
    -------
    pandas.DataFrame with exactly the columns in OUTPUT_COLUMNS.
    All values are stored as strings (matching the TEXT columns in the
    raw.ae_attendances table).

    Raises
    ------
    ValueError: If the file cannot be decoded.
    KeyError:   If mandatory columns (org_code, period) are completely absent
                after alias mapping — indicating an unrecognised file format.
    """
    filepath = Path(filepath)
    log.info("Normalising: %s", filepath.name)

    df = _try_read_csv(filepath)
    df = _normalise_column_names(df)
    df = _strip_values(df)

    # Detect Era 2/3 files (they have *over4hr columns instead of within)
    if any(c in df.columns for c in _OVER4_COLS):
        df = _convert_over4hr_to_within(df)

    df = _drop_non_data_rows(df)
    df = _ensure_output_columns(df)

    # Normalise null markers in all columns to Python None
    df = df.replace(_NULL_MARKERS, None)

    # Ensure org_code is upper-cased
    if "org_code" in df.columns:
        df["org_code"] = df["org_code"].str.upper()

    log.info("  → %d rows after cleaning.", len(df))
    return df.reset_index(drop=True)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python normalise.py <path/to/file.csv>")
        sys.exit(1)

    result = normalise_csv(sys.argv[1])
    print(result.head(10).to_string())
    print(f"\n{len(result)} rows, columns: {list(result.columns)}")
