"""
conftest.py – Pytest configuration for PulseBoard tests.

Adds the ingestion/ directory to sys.path so test files can import
normalise, config, etc. directly without package-relative imports.
"""

import sys
from pathlib import Path

# ingestion/ sits one level up from tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingestion"))
