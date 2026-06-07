"""
test_ingestion.py – Pytest unit tests for ingestion/normalise.py.

Tests are self-contained: they create temporary CSV files in memory (or as
temp files) and verify normalise_csv() output without touching the database
or the network.
"""

import io
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Ensure the ingestion package is importable when pytest is run from the
# project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ingestion"))

from normalise import normalise_csv  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────────


def _write_temp_csv(content: str, encoding: str = "utf-8") -> Path:
    """Write *content* to a named temporary file and return its Path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="wb", suffix=".csv", delete=False
    )
    tmp.write(content.encode(encoding))
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


# ── Test 1: Dash values become None ──────────────────────────────────────────


def test_dash_values_become_none():
    """
    Rows containing '-' in numeric columns should produce None (SQL NULL)
    after normalisation, not the literal string '-'.

    Uses Era-1 column headers (pre-2018 "within 4 hours" format).
    """
    csv_content = (
        "Period,Org Code,Org name,"
        "Type 1 Departments - Major A&E - Total Attendances,"
        "Type 1 Departments - Major A&E - Number of attendances within 4 hours,"
        "Type 2 Departments - Single Specialty A&E - Total Attendances,"
        "Type 2 Departments - Single Specialty A&E - Number of attendances within 4 hours,"
        "Other A&E Departments - Total Attendances,"
        "Other A&E Departments - Number of attendances within 4 hours\n"
        "March 2019,RJ1,St Thomas' Hospital,1000,-,50,-,200,-\n"
    )
    tmp = _write_temp_csv(csv_content)
    try:
        df = normalise_csv(tmp)
        assert len(df) == 1
        row = df.iloc[0]
        # type1_4hr was '-' → should be None
        assert row["type1_4hr"] is None, (
            f"Expected None for '-' value, got {row['type1_4hr']!r}"
        )
        # type1_att was '1000' → should remain as a string '1000'
        assert row["type1_att"] == "1000"
    finally:
        tmp.unlink(missing_ok=True)


# ── Test 2: Header rows are dropped ──────────────────────────────────────────


def test_header_rows_are_dropped():
    """
    Rows where org_code equals common header labels ('Org Code', 'Code')
    or is blank should be dropped from the output.
    """
    csv_content = (
        "Period,Org Code,Org name,"
        "A&E attendances Type 1,A&E attendances Type 2,"
        "A&E attendances Other A&E Department,"
        "Attendances over 4hrs Type 1,Attendances over 4hrs Type 2,"
        "Attendances over 4hrs Other Department\n"
        "MSitAE-MARCH-2026,Org Code,Name,,,,,, \n"   # literal header row
        "MSitAE-MARCH-2026,,Some Trust,100,10,20,5,2,3\n"  # blank org_code
        "MSitAE-MARCH-2026,RJ1,St Thomas' Hospital,1000,50,200,100,20,40\n"
    )
    tmp = _write_temp_csv(csv_content)
    try:
        df = normalise_csv(tmp)
        # Only the real trust row should survive
        assert len(df) == 1, f"Expected 1 row, got {len(df)}: {df}"
        assert df.iloc[0]["org_code"] == "RJ1"
    finally:
        tmp.unlink(missing_ok=True)


# ── Test 3: Column aliases map correctly ──────────────────────────────────────


def test_column_aliases_era2_format():
    """
    Era-2 column names ('Number of A&E attendances Type 1', etc.) should map
    to the standard output columns and 'over 4hrs' counts should be converted
    to 'within 4hrs' counts.
    """
    csv_content = (
        "Period,Org Code,Org name,"
        "Number of A&E attendances Type 1,"
        "Number of A&E attendances Type 2,"
        "Number of A&E attendances Other A&E Department,"
        "Number of attendances over 4hrs Type 1,"
        "Number of attendances over 4hrs Type 2,"
        "Number of attendances over 4hrs Other A&E Department\n"
        "MSitAE-DECEMBER-2018,RJ1,St Thomas' Hospital,1000,50,200,100,10,30\n"
    )
    tmp = _write_temp_csv(csv_content)
    try:
        df = normalise_csv(tmp)
        assert len(df) == 1
        row = df.iloc[0]
        # Attendance totals should map through
        assert row["type1_att"] == "1000"
        assert row["type2_att"] == "50"
        assert row["other_att"] == "200"
        # within_4hr = total - over4hr: 1000-100=900, 50-10=40, 200-30=170
        assert row["type1_4hr"] == "900", f"Expected 900, got {row['type1_4hr']!r}"
        assert row["type2_4hr"] == "40",  f"Expected 40, got {row['type2_4hr']!r}"
        assert row["other_4hr"] == "170", f"Expected 170, got {row['other_4hr']!r}"
    finally:
        tmp.unlink(missing_ok=True)


def test_column_aliases_era3_format():
    """
    Era-3 column names ('A&E attendances Type 1', 'Attendances over 4hrs …')
    should produce the same standard output columns.
    """
    csv_content = (
        "Period,Org Code,Parent Org,Org name,"
        "A&E attendances Type 1,A&E attendances Type 2,"
        "A&E attendances Other A&E Department,"
        "A&E attendances Booked Appointments Type 1,"
        "A&E attendances Booked Appointments Type 2,"
        "A&E attendances Booked Appointments Other Department,"
        "Attendances over 4hrs Type 1,Attendances over 4hrs Type 2,"
        "Attendances over 4hrs Other Department\n"
        "MSitAE-MARCH-2026,RJ1,NHS ENGLAND LONDON,St Thomas' Hospital,"
        "2000,100,300,50,10,20,200,15,45\n"
    )
    tmp = _write_temp_csv(csv_content)
    try:
        df = normalise_csv(tmp)
        assert len(df) == 1
        row = df.iloc[0]
        assert row["type1_att"] == "2000"
        # within = 2000 - 200 = 1800
        assert row["type1_4hr"] == "1800", f"Got {row['type1_4hr']!r}"
    finally:
        tmp.unlink(missing_ok=True)


# ── Test 4: Latin-1 encoding does not crash ───────────────────────────────────


def test_latin1_encoding_does_not_crash():
    """
    Some older NHS files are encoded in latin-1 (ISO-8859-1).  Trust names
    can contain characters like é, ü, ñ that are not valid UTF-8.
    normalise_csv() should handle these without raising an exception.
    """
    # Construct a CSV string with a latin-1 character in the trust name
    csv_content = (
        "Period,Org Code,Org name,"
        "Type 1 Departments - Major A&E - Total Attendances,"
        "Type 1 Departments - Major A&E - Number of attendances within 4 hours,"
        "Type 2 Departments - Single Specialty A&E - Total Attendances,"
        "Type 2 Departments - Single Specialty A&E - Number of attendances within 4 hours,"
        "Other A&E Departments - Total Attendances,"
        "Other A&E Departments - Number of attendances within 4 hours\n"
        "March 2015,RA9,Caf\xe9 Hospital NHS Trust,500,450,30,28,100,90\n"
    )
    tmp = _write_temp_csv(csv_content, encoding="latin-1")
    try:
        df = normalise_csv(tmp)
        assert len(df) == 1
        assert df.iloc[0]["org_code"] == "RA9"
        # Trust name may be decoded differently across encodings – just
        # confirm it's a non-empty string and didn't raise.
        assert isinstance(df.iloc[0]["org_name"], str)
        assert len(df.iloc[0]["org_name"]) > 0
    finally:
        tmp.unlink(missing_ok=True)


# ── Test 5: Output always has exactly the required columns ────────────────────


def test_output_columns_are_complete():
    """
    The returned DataFrame must always contain exactly the nine standard
    columns regardless of which era's headers the source file uses.
    """
    expected_cols = {
        "period", "org_code", "org_name",
        "type1_att", "type1_4hr",
        "type2_att", "type2_4hr",
        "other_att", "other_4hr",
    }
    csv_content = (
        "Period,Org Code,Org name,"
        "A&E attendances Type 1,A&E attendances Type 2,"
        "A&E attendances Other A&E Department,"
        "Attendances over 4hrs Type 1,Attendances over 4hrs Type 2,"
        "Attendances over 4hrs Other Department\n"
        "MSitAE-MARCH-2026,RJ1,St Thomas' Hospital,1000,50,200,100,20,40\n"
    )
    tmp = _write_temp_csv(csv_content)
    try:
        df = normalise_csv(tmp)
        assert set(df.columns) == expected_cols, (
            f"Column mismatch. Got: {set(df.columns)}"
        )
    finally:
        tmp.unlink(missing_ok=True)
