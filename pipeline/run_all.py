"""Run the whole pipeline: extract -> parse workbooks -> build model tables -> tests.

Run from the repo root:   python pipeline/run_all.py
Needs: Python 3.10+, `pip install openpyxl`, and the DuckDB command-line program
(set the DUCKDB environment variable if duckdb is not on your PATH).
"""
import subprocess
import sys
from pathlib import Path

from common import DB_PATH, DUCKDB_EXE

HERE = Path(__file__).resolve().parent
for step in ["step01_extract_and_manifest.py", "step02_parse_pilot_workbooks.py", "step03_build_model_tables.py"]:
    print(f"\n=== {step}")
    subprocess.run([sys.executable, str(HERE / step)], check=True)

print("\n=== step04_tests.sql")
tests = (HERE / "step04_tests.sql").read_text(encoding="utf-8")
res = subprocess.run([DUCKDB_EXE, str(DB_PATH)], input=tests, text=True, encoding="utf-8", capture_output=True, cwd=HERE.parent)
print(res.stdout)
if "| FAIL" in res.stdout:
    sys.exit("Some tests FAILED - fix them before opening Power BI.")