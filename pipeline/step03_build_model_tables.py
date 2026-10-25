"""Step 03: aggregate the large CPUC CSVs with DuckDB and write the model tables.

Why DuckDB and not Power BI for this step: the trip and incident files are
about 8 GB. Power BI only needs counts by quarter, reason and flag, so we
aggregate first (millions of rows -> a few hundred) and keep the .pbix small.

Why one SELECT per file (not a single wildcard read): the files change shape
between quarters (different names, a duplicated column, trailing empty
columns). Reading each file on its own, with the quarter, company, program and
mode taken from the manifest, is explicit and easy to debug.

This script writes data/staging/build.sql (so you can read every query) and
runs it with the DuckDB command-line program.

Run:  python pipeline/step03_build_model_tables.py
"""
import csv
import re
import subprocess

from common import STAGING, MODEL, RAW, DB_PATH, DUCKDB_EXE, sql_path

READ = "read_csv('{p}', all_varchar=true, header=true, delim=',', quote='\"', null_padding=true)"


def norm(name: str) -> str:
    """Compare column names loosely: lower case, letters/digits only, and treat
    'Collisions...' (Dec 2024 files) the same as 'Collision...'."""
    n = re.sub(r"[^a-z0-9]", "", name.lower())
    return re.sub(r"^collisions(?=[a-z])", "collision", n)


_headers = {}


def header_of(path: str) -> dict:
    """Map normalised name -> actual column name, read from the file's first line."""
    if path not in _headers:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
            first = next(csv.reader(fh), [])
        _headers[path] = {}
        for h in first:
            if h and norm(h) not in _headers[path]:      # first one wins if a name repeats
                _headers[path][norm(h)] = h
    return _headers[path]


class Cols:
    """col('TotalTrips') -> the file's real column, quoted; NULL if the file lacks it."""
    def __init__(self, m):
        self.h = header_of(m["read_path"])
    def __call__(self, std: str) -> str:
        actual = self.h.get(norm(std))
        return '"' + actual.replace('"', '""') + '"' if actual else "NULL"


def yes(c):
    """1 when a Y/N flag is 'Y' (any case, any spaces), else 0."""
    return f"coalesce((upper(trim({c})) = 'Y')::INT, 0)"


def num(c):
    """'1,217,872' -> 1217872 ; 'Redacted' or blank -> NULL"""
    return f"try_cast(replace({c}, ',', '') AS DOUBLE)"


def tag(m):
    return (f"'{m['quarter']}' AS quarter, '{m['company']}' AS company, "
            f"'{m['program']}' AS program, '{m['mode']}' AS mode")


def union(selects):
    return "\nUNION ALL\n".join(selects) if selects else None


def main():
    manifest = list(csv.DictReader(open(STAGING / "manifest.csv", encoding="utf-8")))
    by_table = {}
    for m in manifest:
        by_table.setdefault(m["table"], []).append(m)

    def src(m):
        return READ.format(p=sql_path_str(m["read_path"]))

    def fname(m):
        return m["path"].split("/")[-1].replace("'", "''")

    # 1. Monthly service totals (CSV month files) ---------------------------
    month_sel = []
    for m in by_table.get("month", []):
        c = Cols(m)
        month_sel.append(f"""SELECT {tag(m)}, {num(c('Year'))}::INT AS year, {num(c('Month'))}::INT AS month,
  {num(c('TotalTrips'))} AS trips, {num(c('TotalWaiting'))} AS waiting_h,
  {num(c('TotalVMTPeriod1'))} AS vmt_p1, {num(c('TotalVMTPeriod2'))} AS vmt_p2, {num(c('TotalVMTPeriod3'))} AS vmt_p3,
  {num(c('TotalVMTZEV'))} AS vmt_zev, {num(c('TotalPassengersCarried'))} AS passengers, {num(c('TotalPMT'))} AS pmt,
  {num(c('TotalWAVsRequested'))} AS wav_requested, {num(c('TotalWAVsFulfilled'))} AS wav_fulfilled,
  '{fname(m)}' AS source_file
FROM {src(m)} WHERE {num(c('TotalTrips'))} IS NOT NULL""")

    # 2. Trip outcomes (one row per request in the source) ------------------
    trip_sel = []
    for m in by_table.get("trips", []):
        c = Cols(m)
        trip_sel.append(f"""SELECT {tag(m)}, upper(trim({c('TripFulfilled')})) AS fulfilled,
  coalesce(nullif(trim({c('ReasonUnfulfilled')}), ''), '(none)') AS reason_unfulfilled,
  upper(trim({c('WAVReq')})) AS wav_requested, upper(trim({c('SharedProvided')})) AS shared,
  upper(trim({c('FaredRide')})) AS fared, count(*) AS requests
FROM {src(m)} WHERE {c('TCPID')} IS NOT NULL AND trim({c('TCPID')}) <> '' GROUP BY ALL""")

    # 3. Incidents and complaints: count the Y flags, never the rows --------
    inc_sel = []
    for m in by_table.get("incidents_complaints", []):
        c = Cols(m)
        any_of = lambda cols: " OR ".join(f"upper(trim({c(x)}))='Y'" for x in cols)
        coll = any_of(["CollisionOccupant", "CollisionPedestrian", "CollisionBicycleScooter",
                       "CollisionMotorcycles", "CollisionOtherVehicle", "CollisionRail", "CollisionProperty"])
        inj = any_of(["CollisionSeverityInjuryPossible", "CollisionSeverityInjuryMinor",
                      "CollisionSeverityInjurySevere", "CollisionSeverityFatality"])
        inc_sel.append(f"""SELECT {tag(m)},
  sum(coalesce(({coll})::INT, 0)) AS collisions,
  sum(coalesce(({inj})::INT, 0)) AS injury_collisions,
  sum({yes(c('CollisionSeverityInjurySevere'))}) AS severe_injury_collisions,
  sum({yes(c('CollisionPedestrian'))}) AS pedestrian_collisions,
  sum({yes(c('CollisionBicycleScooter'))}) AS bike_scooter_collisions,
  sum({yes(c('ComplaintSafety'))}) AS complaints_safety,
  sum({yes(c('ComplaintPUDO'))}) AS complaints_pickup_dropoff,
  sum({yes(c('ComplaintCustomerService'))}) AS complaints_customer_service,
  sum(({yes(c('ComplaintAccessibility'))} + {yes(c('ComplaintWAV'))} > 0)::INT) AS complaints_accessibility,
  sum({yes(c('ComplaintOther'))}) AS complaints_other,
  sum({yes(c('Citation'))}) AS citations,
  count(*) AS source_rows
FROM {src(m)} WHERE {c('TCPID')} IS NOT NULL AND trim({c('TCPID')}) <> ''""")

    # 4. Collisions by census tract (quarter taken from the folder, not the file)
    loc_sel = []
    for m in by_table.get("incidents_location", []):
        c = Cols(m)
        loc_sel.append(f"""SELECT {tag(m)}, lpad(trim({c('Tract')}), 11, '0') AS tract,
  {num(c('CollisionsAll'))} AS collisions_all, {num(c('CollisionsPUDO'))} AS collisions_pickup_dropoff
FROM {src(m)} WHERE regexp_full_match(trim({c('Tract')}), '[0-9]{{9,11}}')""")

    # 5. Service area: which tracts were in service each month --------------
    tract_sel = []
    for m in by_table.get("monthly_tract", []):
        c = Cols(m)
        tract_sel.append(f"""SELECT {tag(m)}, {num(c('Year'))}::INT AS year, {num(c('Month'))}::INT AS month,
  lpad(trim({c('Tract')}), 11, '0') AS tract, {num(c('TripsStart'))} AS trips_start
FROM {src(m)} WHERE regexp_full_match(trim({c('Tract')}), '[0-9]{{9,11}}')""")

    waymo = (RAW / "Waymo Safety Data")
    csv2 = next(waymo.glob("CSV2*.csv"))
    csv3 = next(waymo.glob("CSV3*.csv"))
    csv1 = next(waymo.glob("CSV1*.csv"))
    out = MODEL.as_posix()

    sql = f"""
-- Generated by step03_build_model_tables.py. Read it; do not edit it by hand.
CREATE OR REPLACE TABLE stg_month AS
{union(month_sel)};
CREATE OR REPLACE TABLE stg_month_pilot_xlsx AS
SELECT * FROM read_csv('{sql_path(STAGING / 'pilot_month_standard.csv')}', header=true);

CREATE OR REPLACE TABLE fact_service_month AS
SELECT quarter, company, program, mode, year, month,
       make_date(year, month, 1) AS month_start,
       sum(trips) AS trips, sum(waiting_h) AS waiting_h,
       sum(vmt_p1) AS vmt_p1, sum(vmt_p2) AS vmt_p2, sum(vmt_p3) AS vmt_p3, sum(vmt_zev) AS vmt_zev,
       sum(passengers) AS passengers, sum(pmt) AS pmt,
       sum(wav_requested) AS wav_requested, sum(wav_fulfilled) AS wav_fulfilled,
       string_agg(DISTINCT source_file, ' | ') AS source_files
FROM (SELECT quarter, company, program, mode, year, month, trips, waiting_h, vmt_p1, vmt_p2, vmt_p3,
             vmt_zev, passengers, pmt, wav_requested, wav_fulfilled, source_file FROM stg_month
      UNION ALL
      SELECT quarter, company, program, mode, year, month, trips, waiting_h, vmt_p1, vmt_p2, vmt_p3,
             vmt_zev, passengers, pmt, wav_requested, wav_fulfilled, source_file FROM stg_month_pilot_xlsx)
GROUP BY ALL;

CREATE OR REPLACE TABLE fact_trip_outcome_q AS
SELECT quarter, company, program, mode, fulfilled, reason_unfulfilled, wav_requested, shared, fared,
       sum(requests) AS requests
FROM ({union(trip_sel)}) GROUP BY ALL;

CREATE OR REPLACE TABLE fact_incident_q AS
SELECT quarter, company, program, mode,
       sum(collisions) AS collisions, sum(injury_collisions) AS injury_collisions,
       sum(severe_injury_collisions) AS severe_injury_collisions,
       sum(pedestrian_collisions) AS pedestrian_collisions, sum(bike_scooter_collisions) AS bike_scooter_collisions,
       sum(complaints_safety) AS complaints_safety, sum(complaints_pickup_dropoff) AS complaints_pickup_dropoff,
       sum(complaints_customer_service) AS complaints_customer_service,
       sum(complaints_accessibility) AS complaints_accessibility, sum(complaints_other) AS complaints_other,
       sum(citations) AS citations, sum(source_rows) AS source_rows
FROM ({union(inc_sel)}) GROUP BY ALL;

CREATE OR REPLACE TABLE fact_tract_q AS
SELECT quarter, company, program, mode, tract, substr(tract, 1, 5) AS county_fips,
       sum(collisions_all) AS collisions_all, sum(collisions_pickup_dropoff) AS collisions_pickup_dropoff
FROM ({union(loc_sel)}) GROUP BY ALL;

CREATE OR REPLACE TABLE fact_service_area_m AS
SELECT DISTINCT quarter, company, program, mode, year, month, make_date(year, month, 1) AS month_start,
       tract, substr(tract, 1, 5) AS county_fips, trips_start
FROM ({union(tract_sel)});

CREATE OR REPLACE TABLE fact_pilot_metrics_q AS
SELECT * FROM read_csv('{sql_path(STAGING / 'pilot_metrics_long.csv')}', header=true);

-- Waymo Safety Impact hub (company-published) --------------------------
CREATE OR REPLACE TABLE fact_federal_crash_m AS
SELECT try_cast(substr("Year Month", 1, 4) AS INT) AS year, try_cast(substr("Year Month", 5, 2) AS INT) AS month,
       make_date(try_cast(substr("Year Month", 1, 4) AS INT), try_cast(substr("Year Month", 5, 2) AS INT), 1) AS month_start,
       State AS state, County AS county, "Road Type" AS road_type, "Crash Type" AS crash_type,
       "SGO Amendment" AS sgo_rule_version,
       count(*) AS crashes,
       sum(("Is Any-Injury-Reported" = 'True')::INT) AS injury_crashes,
       sum(("Is Police-Reported" = 'True')::INT) AS police_reported_crashes,
       sum(("Is Suspected Serious Injury+" = 'True')::INT) AS serious_injury_crashes,
       sum(("Is Any Vehicle Airbag Deployment" = 'True')::INT) AS airbag_crashes
FROM read_csv('{sql_path(csv2)}', header=true, all_varchar=true)
GROUP BY ALL;   -- street descriptions and ZIP codes are deliberately left out

CREATE OR REPLACE TABLE fact_benchmark AS
SELECT Outcome AS outcome, "Benchmark Comparison" AS benchmark_version, "County Name" AS area,
       "Grouping Type" AS grouping_type, "Conflict Partner Type Group" AS crash_group,
       "Waymo Count" AS waymo_count, "Waymo IPMM" AS waymo_per_million_miles,
       "Benchmark IPMM" AS benchmark_per_million_miles,
       "Waymo Percent Reduction" AS pct_difference,
       "Waymo Percent Reduction CI Lower" AS pct_difference_low,
       "Waymo Percent Reduction CI Upper" AS pct_difference_high
FROM read_csv('{sql_path(csv3)}', header=true);

CREATE OR REPLACE TABLE fact_rider_only_miles AS
SELECT "County Name" AS area, "Waymo RO Miles (Millions)" AS rider_only_miles_millions
FROM read_csv('{sql_path(csv1)}', header=true);

-- Write every model table to CSV for Power BI --------------------------
COPY fact_service_month   TO '{out}/fact_service_month.csv'   (HEADER);
COPY fact_trip_outcome_q  TO '{out}/fact_trip_outcome_q.csv'  (HEADER);
COPY fact_incident_q      TO '{out}/fact_incident_q.csv'      (HEADER);
COPY fact_tract_q         TO '{out}/fact_tract_q.csv'         (HEADER);
COPY fact_service_area_m  TO '{out}/fact_service_area_m.csv'  (HEADER);
COPY fact_pilot_metrics_q TO '{out}/fact_pilot_metrics_q.csv' (HEADER);
COPY fact_federal_crash_m TO '{out}/fact_federal_crash_m.csv' (HEADER);
COPY fact_benchmark       TO '{out}/fact_benchmark.csv'       (HEADER);
COPY fact_rider_only_miles TO '{out}/fact_rider_only_miles.csv' (HEADER);
"""
    MODEL.mkdir(parents=True, exist_ok=True)
    sql_file = STAGING / "build.sql"
    sql_file.write_text(sql, encoding="utf-8")
    print(f"Wrote {sql_file}  ({len(sql.splitlines())} lines). Running DuckDB ...")
    res = subprocess.run([DUCKDB_EXE, str(DB_PATH)], input=sql, text=True, encoding="utf-8", capture_output=True)
    if res.returncode != 0 or "Error" in res.stderr:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise SystemExit("DuckDB failed - see the error above")
    print("Done. Model tables written to", MODEL)


def sql_path_str(p: str) -> str:
    return p.replace("\\", "/").replace("'", "''")


if __name__ == "__main__":
    main()