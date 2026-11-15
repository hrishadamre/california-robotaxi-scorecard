"""Step 03a: land the raw files in DuckDB with standard column names.

This is the "extract + load" half of ELT. Python keeps the job it is good at:
reading 362 files whose column names drift between quarters. It writes raw
tables that have the SAME column names every time. dbt then does the
transformation (typing, cleaning, counting flags, joining) in plain SQL.

Rules for this step:
  * No cleaning and no filtering. Values stay as text (all_varchar).
  * Every row carries quarter, company, program, mode and source_file (lineage).
  * Street descriptions and ZIP codes are never selected, so they never enter the database.

Run from the repo root:
    python pipeline/step03a_land_raw.py
"""
import csv
import subprocess

from common import STAGING, RAW, DB_PATH, DUCKDB_EXE, sql_path
# Reuse the per-file helpers from step 03 (column resolver, quarter/company tags).
from step03_build_model_tables import Cols, tag, union, READ, sql_path_str

# raw table -> (manifest table type, [(standard name, name used in the files), ...])
LAND = {
    "raw_month": ("month", [
        ("year", "Year"), ("month", "Month"), ("total_trips", "TotalTrips"),
        ("total_waiting", "TotalWaiting"), ("total_vmt_p1", "TotalVMTPeriod1"),
        ("total_vmt_p2", "TotalVMTPeriod2"), ("total_vmt_p3", "TotalVMTPeriod3"),
        ("total_vmt_zev", "TotalVMTZEV"), ("total_passengers", "TotalPassengersCarried"),
        ("total_pmt", "TotalPMT"), ("total_wav_requested", "TotalWAVsRequested"),
        ("total_wav_fulfilled", "TotalWAVsFulfilled")]),
    "raw_trips": ("trips", [
        ("tcpid", "TCPID"), ("trip_fulfilled", "TripFulfilled"),
        ("reason_unfulfilled", "ReasonUnfulfilled"), ("wav_req", "WAVReq"),
        ("shared_provided", "SharedProvided"), ("fared_ride", "FaredRide")]),
    "raw_incidents": ("incidents_complaints", [
        ("tcpid", "TCPID"),
        ("collision_occupant", "CollisionOccupant"), ("collision_pedestrian", "CollisionPedestrian"),
        ("collision_bicycle_scooter", "CollisionBicycleScooter"),
        ("collision_motorcycles", "CollisionMotorcycles"),
        ("collision_other_vehicle", "CollisionOtherVehicle"), ("collision_rail", "CollisionRail"),
        ("collision_property", "CollisionProperty"),
        ("severity_injury_possible", "CollisionSeverityInjuryPossible"),
        ("severity_injury_minor", "CollisionSeverityInjuryMinor"),
        ("severity_injury_severe", "CollisionSeverityInjurySevere"),
        ("severity_fatality", "CollisionSeverityFatality"),
        ("complaint_safety", "ComplaintSafety"), ("complaint_pudo", "ComplaintPUDO"),
        ("complaint_customer_service", "ComplaintCustomerService"),
        ("complaint_accessibility", "ComplaintAccessibility"), ("complaint_wav", "ComplaintWAV"),
        ("complaint_other", "ComplaintOther"), ("citation", "Citation")]),
    "raw_incident_tract": ("incidents_location", [
        ("tract", "Tract"), ("collisions_all", "CollisionsAll"), ("collisions_pudo", "CollisionsPUDO")]),
    "raw_service_area": ("monthly_tract", [
        ("year", "Year"), ("month", "Month"), ("tract", "Tract"), ("trips_start", "TripsStart")]),
}


def main():
    manifest = list(csv.DictReader(open(STAGING / "manifest.csv", encoding="utf-8")))
    by_table = {}
    for m in manifest:
        by_table.setdefault(m["table"], []).append(m)

    statements = []
    for raw_name, (kind, cols) in LAND.items():
        selects = []
        for m in by_table.get(kind, []):
            c = Cols(m)
            fname = m["path"].split("/")[-1].replace("'", "''")
            col_sql = ", ".join(f"{c(src)} AS {std}" for std, src in cols)
            src = READ.format(p=sql_path_str(m["read_path"]))
            selects.append(f"SELECT {tag(m)}, {col_sql}, '{fname}' AS source_file FROM {src}")
        if not selects:
            raise SystemExit(f"No files of type '{kind}' in the manifest - run step 01 first.")
        statements.append(f"CREATE OR REPLACE TABLE {raw_name} AS\n{union(selects)};")

    # Company-published and parsed files: land them as text with standard names.
    waymo = RAW / "Waymo Safety Data"
    csv1 = next(waymo.glob("CSV1*.csv"))
    csv2 = next(waymo.glob("CSV2*.csv"))
    csv3 = next(waymo.glob("CSV3*.csv"))
    rd = "read_csv('{p}', header=true, all_varchar=true)"
    statements += [
        f"CREATE OR REPLACE TABLE raw_manifest AS SELECT * EXCLUDE (\"table\"), \"table\" AS table_type FROM {rd.format(p=sql_path(STAGING / 'manifest.csv'))};",
        f"CREATE OR REPLACE TABLE raw_pilot_month AS SELECT * FROM {rd.format(p=sql_path(STAGING / 'pilot_month_standard.csv'))};",
        f"CREATE OR REPLACE TABLE raw_pilot_metrics AS SELECT * FROM {rd.format(p=sql_path(STAGING / 'pilot_metrics_long.csv'))};",
        # Federal crash file: only the columns the project uses. Street text and ZIP are left out on purpose.
        f"""CREATE OR REPLACE TABLE raw_waymo_federal AS
SELECT "Year Month" AS year_month, State AS state, County AS county, "Road Type" AS road_type,
       "Crash Type" AS crash_type, "SGO Amendment" AS sgo_amendment,
       "Is Any-Injury-Reported" AS is_any_injury, "Is Police-Reported" AS is_police_reported,
       "Is Suspected Serious Injury+" AS is_serious_injury, "Is Any Vehicle Airbag Deployment" AS is_airbag
FROM {rd.format(p=sql_path(csv2))};""",
        f"""CREATE OR REPLACE TABLE raw_waymo_benchmark AS
SELECT Outcome AS outcome, "Benchmark Comparison" AS benchmark_version, "County Name" AS area,
       "Grouping Type" AS grouping_type, "Conflict Partner Type Group" AS crash_group,
       "Waymo Count" AS waymo_count, "Waymo IPMM" AS waymo_ipmm, "Benchmark IPMM" AS benchmark_ipmm,
       "Waymo Percent Reduction" AS pct_reduction, "Waymo Percent Reduction CI Lower" AS pct_reduction_lower,
       "Waymo Percent Reduction CI Upper" AS pct_reduction_upper
FROM {rd.format(p=sql_path(csv3))};""",
        f"""CREATE OR REPLACE TABLE raw_waymo_rider_miles AS
SELECT "County Name" AS area, "Waymo RO Miles (Millions)" AS rider_only_miles_millions
FROM {rd.format(p=sql_path(csv1))};""",
    ]

    counts = " UNION ALL ".join(
        f"SELECT '{t}' AS raw_table, count(*) AS row_count FROM {t}"
        for t in list(LAND) + ["raw_pilot_month", "raw_pilot_metrics", "raw_waymo_federal",
                               "raw_waymo_benchmark", "raw_waymo_rider_miles"])
    sql = ("-- Generated by step03a_land_raw.py. Read it; do not edit it by hand.\n"
           + "\n\n".join(statements) + f"\n\n.mode markdown\n{counts};\n")
    sql_file = STAGING / "land_raw.sql"
    sql_file.write_text(sql, encoding="utf-8")
    print(f"Wrote {sql_file} ({len(sql.splitlines())} lines). Running DuckDB (this can take a few minutes) ...")
    res = subprocess.run([DUCKDB_EXE, str(DB_PATH)], input=sql, text=True, encoding="utf-8", capture_output=True)
    if res.returncode != 0 or "Error" in res.stderr:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise SystemExit("DuckDB failed - see the error above")
    print(res.stdout)
    print("Done. Raw tables are in", DB_PATH)


if __name__ == "__main__":
    main()
    