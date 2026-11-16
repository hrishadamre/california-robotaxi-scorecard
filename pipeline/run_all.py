"""Run the whole pipeline.

Run from the repo root:
    python pipeline/run_all.py                    # default: dbt engine
    python pipeline/run_all.py --engine python    # v1: original Python SQL + SQL tests
    python pipeline/run_all.py --engine both      # v1 + dbt + parity check (proves they match)
    python pipeline/run_all.py --from-landing     # skip extract/parse (steps 01-02), re-run the rest

Engines (steps 01-02 are shared: extract workbooks, parse pilot files):
  python : step03 builds the model tables in Python SQL, step04 tests them.
  dbt    : step03a lands raw tables, dbt builds + tests the models, export_marts writes the CSVs.
  both   : python, then dbt, then parity_check.py, then export (final CSVs come from dbt).

Needs: Python 3.10+, `pip install openpyxl`, the DuckDB command-line program
(set DUCKDB if it is not on your PATH) and dbt in .venv-dbt (set DBT to override).
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import DB_PATH, DUCKDB_EXE

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def find_dbt():
    """dbt lives in its own venv (.venv-dbt); look there first."""
    if os.environ.get("DBT"):
        return os.environ["DBT"]
    for rel in (".venv-dbt/bin/dbt", ".venv-dbt/Scripts/dbt.exe"):
        p = ROOT / rel
        if p.exists():
            return str(p)
    return shutil.which("dbt")


def py(script):
    print(f"\n=== {script}")
    subprocess.run([sys.executable, str(HERE / script)], check=True)


def run_python_tests():
    print("\n=== step04_tests.sql")
    tests = (HERE / "step04_tests.sql").read_text(encoding="utf-8")
    res = subprocess.run([DUCKDB_EXE, str(DB_PATH)], input=tests, text=True,
                         encoding="utf-8", capture_output=True, cwd=ROOT)
    print(res.stdout)
    if "| FAIL" in res.stdout:
        sys.exit("Some tests FAILED - fix them before opening Power BI.")


def run_dbt():
    dbt = find_dbt()
    if not dbt:
        sys.exit("dbt not found. Create .venv-dbt (see README) or set the DBT variable.")
    print("\n=== dbt build (seeds + models + tests)")
    subprocess.run([dbt, "build"], check=True, cwd=ROOT / "dbt")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=["dbt", "python", "both"], default="dbt")
    ap.add_argument("--from-landing", action="store_true",
                    help="skip steps 01-02 (extract/parse) and start from the data already extracted")
    args = ap.parse_args()

    if not args.from_landing:
        py("step01_extract_and_manifest.py")
        py("step02_parse_pilot_workbooks.py")

    if args.engine in ("python", "both"):
        py("step03_build_model_tables.py")
        run_python_tests()

    if args.engine in ("dbt", "both"):
        py("step03a_land_raw.py")
        run_dbt()
        py("dbt_results_to_csv.py")
        if args.engine == "both":
            py("parity_check.py")
        py("export_marts.py")

    print("\nDone. Engine:", args.engine)


if __name__ == "__main__":
    main()