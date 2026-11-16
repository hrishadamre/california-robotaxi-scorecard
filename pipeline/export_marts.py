"""Export dbt mart tables (schema main_marts) to data/model/*.csv.
Power BI reads these CSVs. dbt builds them; this script only writes files."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "staging" / "av.duckdb"
OUT = ROOT / "data" / "model"

TABLES = [
    "dim_county",
    "fact_service_month",
    "fact_trip_outcome_q",
    "fact_incident_q",
    "fact_tract_q",
    "fact_service_area_m",
    "fact_pilot_metrics_q",
    "fact_federal_crash_m",
    "fact_benchmark",
    "fact_rider_only_miles",
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sql = "\n".join(
        f"COPY (SELECT * FROM main_marts.{t} ORDER BY ALL) "
        f"TO '{(OUT / (t + '.csv')).as_posix()}' (HEADER, DELIMITER ',');"
        for t in TABLES
    )
    subprocess.run(["duckdb", str(DB), "-c", sql], check=True)
    print(f"Exported {len(TABLES)} tables to {OUT}")

if __name__ == "__main__":
    main()