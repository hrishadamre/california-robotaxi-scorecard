# Autonomy in California: from testing to paid rides

A data project on how robotaxis moved from permitted testing to paid, driverless service in California, built from public regulator and company data.

**Status:** data pipeline complete and tested. Power BI report in progress.

## The question
As robotaxi service scales in California, are safety and service quality keeping up? The scorecard follows one company (Waymo) from DMV permits through CPUC quarterly service reports to safety outcomes.

## Key findings (Dec 2024 to Jun 2026)
- Paid, driverless trips grew from **1.82 million** (2025 Q1) to **4.22 million** (2026 Q2), about **2.3x** in five quarters.
- Collisions per 100,000 trips stayed in a narrow band, **6.2 to 7.6**, and the exact 95% intervals overlap across quarters. Quarter-to-quarter moves are within what chance would produce.
- About **95%** of ride requests ended in a completed trip, and that held as volume more than doubled.
- Federal crash reports for California drop from **70 (May 2025) to 33 (June 2025)** while trips kept rising. A federal reporting rule changed on June 16, 2025, so this is a change in what is counted, not evidence of safer driving. The report compares rates per trip and marks the break.

## Data sources
| Source | What it provides |
|---|---|
| CPUC autonomous vehicle quarterly data reports (13 quarterly zips) | Trips, miles, incidents, complaints, service area by tract |
| California DMV autonomous vehicle permit holders | Permit stage by company |
| Waymo Safety Impact hub | Federal crash reports and human-benchmark comparisons |

## How it works
```
raw zips (362 files, ~8 GB)
  -> 01 extract + manifest (lineage, file-type detection)
  -> 02 parse legacy pilot workbooks
  -> 03 aggregate in DuckDB to 11 model tables (~11 MB)
  -> 04 data tests (43 checks)
  -> data/model/*.csv  -> Power BI (star schema, DAX)
```
Things worth knowing:
- **Schema drift** across quarters is handled by a column resolver, and a legacy "one row per requirement" layout is unpivoted so no quarter is dropped.
- **A disguised file:** one trips file with a `.csv` extension is actually an Excel workbook. The pipeline reads file signatures, not extensions.
- **Grain:** a row is a reported event, and collisions are counted from the Y flags, never from row counts.
- **Data quality:** 43 tests, **33 PASS, 10 WARN, 0 FAIL**. WARN means a documented, explainable difference. Results are exported to `data/model/test_results.csv`.
- **Redactions** are reported as redacted and never inferred.

## What is deliberately excluded
Assault and harassment complaint fields, street addresses and ZIP codes in the federal crash file, and any policy opinion. The project describes a measurement change; it does not judge it.

## Repository layout
```
pipeline/     step 01 to 04 scripts and run_all.py
data/
  reference/  DMV permits, county list
  model/      the 11 model tables Power BI reads (committed on purpose)
  raw/        CPUC zips (not committed)
powerbi/      report (in progress)
```

## Run it
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python pipeline/run_all.py
```
Requires the DuckDB command-line tool and the raw CPUC zips in `data/raw/` (see `pipeline/common.py`).

## Roadmap
- Power BI report: Overview, Safety, Service, Methods pages (in progress)
- Refactor the transform layer into dbt models and tests (planned)

## Limitations
Reconciliation tests show the processing is internally consistent, not that the source filings are correct. Trip timestamps, locations and miles are redacted in the public files.