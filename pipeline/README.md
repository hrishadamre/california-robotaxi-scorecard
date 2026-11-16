# Pipeline

One command rebuilds everything from the raw CPUC / DMV / Waymo files:

    python pipeline/run_all.py                  # dbt engine (default)
    python pipeline/run_all.py --engine python  # original v1 Python SQL
    python pipeline/run_all.py --engine both    # v1 + dbt + parity check
    python pipeline/run_all.py --from-landing   # skip extract/parse (slow steps)

| Script | Version | What it does |
|---|---|---|
| `step01_extract_and_manifest.py` | shared | Unzips quarterly files, writes a file manifest |
| `step02_parse_pilot_workbooks.py` | shared | Parses the pilot-era Excel workbooks |
| `step03_build_model_tables.py` | v1 (Python) | Original aggregation SQL, kept for comparison |
| `step04_tests.sql` | v1 (Python) | Original SQL data tests |
| `step03a_land_raw.py` | v2 (dbt) | Loads raw files into DuckDB tables as text |
| `../dbt/` | v2 (dbt) | Cleans, builds and tests the model tables |
| `parity_check.py` | both | Proves v1 and v2 tables are identical |
| `export_marts.py` | v2 (dbt) | Writes dbt tables to `data/model/*.csv` for Power BI |

The default engine is dbt. v1 stays so the migration can be checked, see `docs/MIGRATION.md`.