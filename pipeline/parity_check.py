"""Parity check: tables built by dbt (schema main_marts) vs the tables the original
Python step 03 built (schema main). Run from the repo root:

    python pipeline/parity_check.py

MATCH means same row count and no row exists in only one of the two tables.
"""
import subprocess

from common import DB_PATH, DUCKDB_EXE

TABLES = ["fact_service_month", "fact_trip_outcome_q", "fact_incident_q", "fact_tract_q",
          "fact_service_area_m", "fact_pilot_metrics_q", "fact_federal_crash_m",
          "fact_benchmark", "fact_rider_only_miles"]

# source_files lists file names in arbitrary order, so compare it as a sorted list.
REPLACE = {"fact_service_month":
           " REPLACE (array_to_string(list_sort(string_split(source_files, ' | ')), '|') AS source_files)"}


def side(schema: str, table: str) -> str:
    return f"SELECT *{REPLACE.get(table, '')} FROM {schema}.{table}"


def main():
    parts = []
    for t in TABLES:
        old, new = side("main", t), side("main_marts", t)
        parts.append(
            f"SELECT '{t}' AS tbl, (SELECT count(*) FROM main.{t}) AS old_rows, "
            f"(SELECT count(*) FROM main_marts.{t}) AS new_rows, "
            f"(SELECT count(*) FROM ({old} EXCEPT {new})) AS only_in_old, "
            f"(SELECT count(*) FROM ({new} EXCEPT {old})) AS only_in_new")
    sql = (".mode markdown\nSELECT *, CASE WHEN old_rows = new_rows AND only_in_old = 0 AND only_in_new = 0 "
           "THEN 'MATCH' ELSE 'DIFFERENT' END AS verdict FROM (\n"
           + "\nUNION ALL\n".join(parts) + "\n);\n")
    res = subprocess.run([DUCKDB_EXE, str(DB_PATH)], input=sql, text=True, encoding="utf-8", capture_output=True)
    if res.returncode != 0 or "Error" in res.stderr:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise SystemExit("DuckDB failed - see the error above")
    print(res.stdout)
    if "DIFFERENT" in res.stdout:
        raise SystemExit("Some tables differ - do not retire the Python SQL yet.")
    print("All tables match.")


if __name__ == "__main__":
    main()