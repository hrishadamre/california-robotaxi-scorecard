"""Turn dbt's test results (dbt/target/run_results.json) into data/model/test_results.csv.
Same columns the Power BI Methods page already reads: result, test, detail."""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "dbt" / "target" / "run_results.json"
OUT = ROOT / "data" / "model" / "test_results.csv"

STATUS = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "error": "FAIL"}
ORDER = {"FAIL": 0, "WARN": 1, "PASS": 2}


def main():
    if not RESULTS.exists():
        raise SystemExit(f"{RESULTS} not found. Run `dbt build` first.")
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = []
    for r in data["results"]:
        uid = r["unique_id"]
        if not uid.startswith("test."):
            continue  # skip seeds and models
        # test.robotaxi.<test_name>.<hash>  ->  <test_name>
        name = re.sub(r"\.[0-9a-f]{10}$", "", uid.split(".", 2)[2])
        result = STATUS.get(r["status"], "FAIL")
        n = r.get("failures")
        if result == "PASS":
            detail = "0 failing rows"
        else:
            detail = f"{n} failing rows" if n is not None else (r.get("message") or "")
            if result == "WARN":
                detail += " (severity: warn, known data-source gap)"
        rows.append((result, name, detail))
    rows.sort(key=lambda x: (ORDER[x[0]], x[1]))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["result", "test", "detail"])
        w.writerows(rows)
    counts = {k: sum(1 for x in rows if x[0] == k) for k in ORDER}
    print(f"Wrote {len(rows)} tests to {OUT}: {counts}")


if __name__ == "__main__":
    main()