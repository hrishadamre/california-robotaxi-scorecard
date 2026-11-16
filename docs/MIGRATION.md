# From a Python pipeline to dbt

## Why
The first version built the model tables with Python-run SQL and a hand-written
SQL test file. It worked, but the logic had no lineage view, no per-model
documentation and no standard way to test. I moved the transformation layer to
dbt (dbt Core + DuckDB) and kept the original for comparison.

## What changed
| Layer | v1 (Python) | v2 (dbt) |
|---|---|---|
| Extract and parse | Python | Python (unchanged) |
| Load | inside step03 | `step03a_land_raw.py`, text columns, tolerant of column-name changes |
| Clean | inside SQL strings | `stg_*` views and macros |
| Build facts | `step03_build_model_tables.py` | 9 fact tables + `dim_county` in `dbt/models/marts` |
| Tests | `step04_tests.sql` | generic + singular dbt tests, severity `warn` for known data gaps |
| Docs and lineage | none | `dbt docs`, image in `docs/dbt_lineage.png` |

## How I checked the migration
`pipeline/parity_check.py` compares each v2 table with the v1 table in both
directions (EXCEPT). Result: all 9 fact tables match (0 rows only in old,
0 only in new). The exported CSVs contain the same rows as the v1 CSVs; only
the row order changed (deterministic `ORDER BY ALL`).

dbt build: 37 pass, 3 warn, 0 error. The 3 warnings are known data-source
gaps (for example collision counts that differ between two CPUC sources),
and they reproduce the warnings the v1 tests showed.

## What I learned
- Quarters with an empty incident file must stay in the data with a blank
  rate, not disappear. In dbt that needed the file manifest as a source.
- Keep raw values as text when landing, then cast in staging, so a changed
  column name or number format cannot silently drop rows.
- A refactor needs a proof of equivalence, not just passing tests.

## What is still v1
`step03_build_model_tables.py`, `step04_tests.sql` and `test_results.csv` are
the earlier version. `test_results.csv` is refreshed only with `--engine python`
or `--engine both`.
