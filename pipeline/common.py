"""Shared paths and helpers for the Autonomy in California pipeline.

Folder layout (relative to the repo root):
  data/raw/Datasets/...        the folder you unzipped from Datasets.zip (never edited)
  data/staging/extracted/...   inner quarterly zips, unzipped by step 01
  data/staging/*.csv           intermediate files (manifest, parsed workbooks)
  data/model/*.csv             final tables that Power BI loads
"""
from pathlib import Path
import os
import re

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Datasets"
STAGING = ROOT / "data" / "staging"
EXTRACTED = STAGING / "extracted"
MODEL = ROOT / "data" / "model"
DB_PATH = STAGING / "av.duckdb"
# Path to the DuckDB command-line program. Set the DUCKDB environment variable
# if it is not on your PATH, e.g.  export DUCKDB=/opt/homebrew/bin/duckdb
DUCKDB_EXE = os.environ.get("DUCKDB", "duckdb")

# Every name a company has filed under -> one canonical company name.
COMPANY_ALIASES = {
    "waymo": "Waymo",
    "zoox": "Zoox",
    "weride": "WeRide",
    "tensor": "Tensor",
    "autox": "Tensor",      # AutoX renamed itself Tensor in 2025
    "nuro": "Nuro",
    "aurora": "Aurora",
    "cruise": "Cruise",
}


def quarter_from_name(name: str) -> str | None:
    """'Waymo Deployment 2025Q2' -> '2025Q2'; 'AV Pilot - 2025 Q1' -> '2025Q1';
    'Waymo Dep Dec 2024 Public_2' -> '2024Q4' (it holds December 2024 only)."""
    m = re.search(r"(20\d\d)\s*Q\s*([1-4])", name, re.I)
    if m:
        return f"{m.group(1)}Q{m.group(2)}"
    if re.search(r"dec\s*2024", name, re.I):
        return "2024Q4"
    return None


def company_from_parts(parts) -> tuple[str | None, str | None]:
    """Return (canonical company, name as filed) from the folders in a path."""
    for p in parts:
        key = re.sub(r"[^a-z]", "", p.lower())
        for alias, canonical in COMPANY_ALIASES.items():
            if key.startswith(alias):
                return canonical, p
    return None, None


def table_type(filename: str) -> str:
    """Classify a CPUC file by its name. Order matters: check the most specific
    names first (e.g. 'Monthly Tract' before 'Month')."""
    n = re.sub(r"[^a-z]", "", filename.lower())
    rules = [
        ("appendix", "legacy_appendix"),      # Waymo pilot, older summary layout
        ("fleetwide", "legacy_appendix"),
        ("pervehicle", "legacy_appendix"),
        ("pertrip", "legacy_appendix"),
        ("monthlytract", "monthly_tract"),
        ("incidentslocation", "incidents_location"),
        ("incidentlocation", "incidents_location"),
        ("incidentscomplaints", "incidents_complaints"),
        ("stoppagefleet", "stoppage_fleet"),
        ("stoppageincident", "stoppage_incident"),
        ("chargingsessions", "charging_sessions"),
        ("chargers", "chargers"),
        ("referencekey", "reference_key"),
        ("triplevel", "trips"),
        ("trips", "trips"),
        ("monthlevel", "month"),
        ("month", "month"),
        ("cover", "cover"),
    ]
    for needle, kind in rules:
        if needle in n:
            return kind
    return "other"


def sql_path(p: Path) -> str:
    """A path written for DuckDB: forward slashes, single quotes escaped."""
    return p.as_posix().replace("'", "''")