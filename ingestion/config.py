"""
config.py – Central configuration for the PulseBoard ingestion pipeline.

All secrets are read from environment variables (with .env fallback via
python-dotenv).  No credentials are hard-coded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")

# ── NHS source ──────────────────────────────────────────────────────────────

NHS_BASE_URL: str = (
    "https://www.england.nhs.uk/statistics/statistical-work-areas/"
    "ae-waiting-times-and-activity/"
)

# ── Database ────────────────────────────────────────────────────────────────

DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: str = os.getenv("DB_PORT", "5432")
DB_NAME: str = os.getenv("DB_NAME", "pulseboard")
DB_USER: str = os.getenv("DB_USER", "pulse")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "pulse")

DB_URL: str = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── Local storage ───────────────────────────────────────────────────────────

RAW_DATA_DIR: Path = _PROJECT_ROOT / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Column alias mapping ────────────────────────────────────────────────────
#
# NHS England has changed the column headers in their A&E CSV files several
# times.  This dict maps every known variant onto the six standard field
# names used in raw.ae_attendances.
#
# Era 1  – pre-2018  (weekly XLS converted to monthly CSV, "within 4hr")
# Era 2  – 2018-19   (first monthly CSV era, "Number of … over 4hrs")
# Era 3  – 2019+     (current CSV format, "A&E attendances …", "over 4hrs")
#
# For eras 2 & 3 the 4-hour metric is "attendances OVER 4 hrs" (failures).
# normalise.py detects which era a file belongs to and converts:
#   type1_4hr = type1_att − type1_over4hr
# so that type1_4hr always means "attendances WITHIN 4 hours" in the raw
# layer, consistent with the original Era 1 definition.

COLUMN_ALIASES: dict[str, str] = {
    # ── Org identifier columns ──────────────────────────────────────────────
    "org code":                                     "org_code",
    "orgcode":                                      "org_code",
    "organisation code":                            "org_code",

    # ── Org name columns ───────────────────────────────────────────────────
    "org name":                                     "org_name",
    "org_name":                                     "org_name",
    "name":                                         "org_name",
    "organisation name":                            "org_name",
    "trust name":                                   "org_name",
    "nhs trust":                                    "org_name",
    "commissioner":                                 "org_name",

    # ── Period / date columns ──────────────────────────────────────────────
    "period":                                       "period",
    "month":                                        "period",
    "date":                                         "period",

    # ────────────────────────────────────────────────────────────────────────
    # ERA 1  (pre-2018, XLS extracts / early monthly CSVs)
    # "Number of attendances within 4 hours" → type1_4hr (already success %)
    # ────────────────────────────────────────────────────────────────────────

    # Type 1 attendances
    "type 1 departments - major a&e - total attendances":           "type1_att",
    "type 1 departments - total attendances":                       "type1_att",
    "type 1 total attendances":                                     "type1_att",
    "a&e type 1 total attendances":                                 "type1_att",
    "major a&e - total attendances":                                "type1_att",

    # Type 1 within 4 hours (Era 1 – successes)
    "type 1 departments - major a&e - number of attendances within 4 hours":  "type1_4hr",
    "type 1 departments - number of attendances within 4 hours":              "type1_4hr",
    "type 1 departments - major a&e - attendances within 4 hours":            "type1_4hr",
    "type 1 departments - attendances within 4 hours":                        "type1_4hr",
    "type 1 attendances within 4 hours":                                      "type1_4hr",
    "a&e type 1 attendances within 4hrs":                                     "type1_4hr",
    "major a&e - attendances within 4 hours":                                 "type1_4hr",

    # Type 2 attendances
    "type 2 departments - single specialty a&e - total attendances":  "type2_att",
    "type 2 departments - total attendances":                         "type2_att",
    "type 2 total attendances":                                       "type2_att",
    "a&e type 2 total attendances":                                   "type2_att",
    "single specialty - total attendances":                           "type2_att",

    # Type 2 within 4 hours (Era 1 – successes)
    "type 2 departments - single specialty a&e - number of attendances within 4 hours":  "type2_4hr",
    "type 2 departments - number of attendances within 4 hours":                         "type2_4hr",
    "type 2 departments - attendances within 4 hours":                                   "type2_4hr",
    "type 2 attendances within 4 hours":                                                 "type2_4hr",
    "a&e type 2 attendances within 4hrs":                                                "type2_4hr",

    # Other A&E attendances
    "other a&e departments - total attendances":                      "other_att",
    "other a&e - total attendances":                                  "other_att",
    "other types - total attendances":                                "other_att",
    "a&e other attendances":                                          "other_att",

    # Other within 4 hours (Era 1 – successes)
    "other a&e departments - number of attendances within 4 hours":   "other_4hr",
    "other a&e departments - attendances within 4 hours":             "other_4hr",
    "other a&e - attendances within 4 hours":                         "other_4hr",
    "other types - attendances within 4 hours":                       "other_4hr",
    "a&e other attendances within 4hrs":                              "other_4hr",

    # ────────────────────────────────────────────────────────────────────────
    # ERA 2  (2018-19 monthly CSV: "Number of … over 4hrs")
    # These map to the _over4hr_ staging columns; normalise.py converts them.
    # ────────────────────────────────────────────────────────────────────────

    "number of a&e attendances type 1":             "type1_att",
    "number of a&e attendances type 2":             "type2_att",
    "number of a&e attendances other a&e department": "other_att",

    "number of attendances over 4hrs type 1":       "type1_over4hr",
    "number of attendances over 4hrs type 2":       "type2_over4hr",
    "number of attendances over 4hrs other a&e department": "other_over4hr",

    # ────────────────────────────────────────────────────────────────────────
    # ERA 3  (2019+ monthly CSV: "A&E attendances …", "Attendances over 4hrs")
    # ────────────────────────────────────────────────────────────────────────

    "a&e attendances type 1":                       "type1_att",
    "a&e attendances type 2":                       "type2_att",
    "a&e attendances other a&e department":         "other_att",

    "attendances over 4hrs type 1":                 "type1_over4hr",
    "attendances over 4hrs type 2":                 "type2_over4hr",
    "attendances over 4hrs other department":       "other_over4hr",
    "attendances over 4hrs other a&e department":   "other_over4hr",
}
