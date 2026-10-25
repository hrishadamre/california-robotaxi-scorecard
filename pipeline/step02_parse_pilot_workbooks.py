"""Step 02: parse pilot-program workbooks into standard tables.

Two layouts exist in the pilot filings:

1. STANDARD layout (CPUC template): one sheet per table, e.g. 'Month-Level' with
   columns TCPID, Year, Month, TotalTrips, ...  Used by Zoox from 2025 Q2 to
   2026 Q1 (Excel). Waymo and Zoox 2026 Q2 use CSVs, which step 03 reads.
   -> data/staging/pilot_month_standard.csv

2. LEGACY "rows as metrics" layout: one row per reporting requirement (long
   English sentences), a 'Total' column, then one column per vehicle. Used by
   WeRide and Tensor/AutoX in every quarter, Nuro in 2026 Q2, Zoox in 2025 Q1,
   and Waymo's pilot 'Data Appendix' CSVs (2025 Q1, and drivered through Q4).
   Each requirement sentence is mapped to a short standard metric name.
   -> data/staging/pilot_metrics_long.csv  (quarter, company, mode, metric, value)

Run:  python pipeline/step02_parse_pilot_workbooks.py
"""
import csv
import datetime as dt
import re

import openpyxl

from common import STAGING

MONTHS = ("january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december")


def to_number(v):
    """'1,234.5' -> 1234.5 ; 7 -> 7.0 ; 'See separate sheet' -> None"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def metric_name(requirement: str) -> str | None:
    """Map a long reporting-requirement sentence to a standard metric name.
    The order of the checks matters: the most specific phrases come first."""
    r = " ".join(str(requirement).lower().split())
    if r.startswith("daily average"):
        return None                                   # per-day detail; skip
    if "wheelchair" in r or " wav" in r or "accessible" in r:
        if "declined" in r:
            return "wav_declined_by_operator"
        if "no wav was available" in r or "lack of accessible" in r:
            return "wav_unfulfilled_unavailable"
        if "fulfilled" in r:
            return "wav_fulfilled"
        if "requested" in r:
            return "wav_requested"
        return None
    if "occupancy" in r or "passengers transported" in r or "number of passengers" in r:
        return "passengers"
    if "pickup point" in r:
        return "vmt_to_pickup"
    if "electric" in r:
        return "vmt_zev"
    if "miles traveled during passenger service" in r:
        return "vmt_passenger_service"
    if "waited" in r or "idling" in r:
        return "idle_hours"                            # monthly rows are summed below
    return None


def legacy_rows(table, quarter, company, mode, source, layout):
    """table: list of rows (lists). First column = requirement, second = Total."""
    out = {}
    for row in table:
        if not row or row[0] is None or isinstance(row[0], (dt.date, dt.datetime)):
            continue
        name = metric_name(row[0])
        value = to_number(row[1]) if len(row) > 1 else None
        if name is None or value is None:
            continue
        out[name] = out.get(name, 0.0) + value          # sums Jan + Feb + Mar idle rows
    return [dict(quarter=quarter, company=company, mode=mode, metric=k, value=v,
                 layout=layout, source_file=source) for k, v in out.items()]


def occupancy_rows(table, quarter, company, mode, source, layout):
    """Per-trip occupancy lists: count trips and sum passengers."""
    trips, pax = 0, 0.0
    for row in table[1:]:                                # first row is the header
        if not row or len(row) < 2 or row[1] in (None, ""):
            continue
        n = to_number(row[-1] if row[-1] is not None else row[2])
        if n is None:
            continue
        trips += 1
        pax += n
    return [dict(quarter=quarter, company=company, mode=mode, metric=m, value=v,
                 layout=layout, source_file=source)
            for m, v in [("trips_from_occupancy_list", trips), ("passengers_from_occupancy_list", pax)]]


def sheet_table(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def csv_table(path):
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return [row for row in csv.reader(fh)]


def main():
    manifest = list(csv.DictReader(open(STAGING / "manifest.csv", encoding="utf-8")))
    long_rows, month_rows, log = [], [], []

    for m in manifest:
        if m["program"] != "pilot":
            continue
        path, q, co, file_mode = m["path"], m["quarter"], m["company"], m["mode"]

        if m["table"] == "xlsx":
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            names = [ws.title for ws in wb.worksheets]
            if "Month-Level" in names:                    # STANDARD layout (Zoox)
                t = sheet_table(wb["Month-Level"])
                header = [str(h).strip() if h is not None else "" for h in t[0]]
                for r in t[1:]:
                    rec = dict(zip(header, r))
                    if rec.get("TCPID") in (None, "") or to_number(rec.get("Year")) is None:
                        continue
                    month_rows.append(dict(
                        quarter=q, company=co, program="pilot", mode=file_mode,
                        year=int(to_number(rec["Year"])), month=int(to_number(rec["Month"])),
                        trips=to_number(rec.get("TotalTrips")), waiting_h=to_number(rec.get("TotalWaiting")),
                        vmt_p1=to_number(rec.get("TotalVMTPeriod1")), vmt_p2=to_number(rec.get("TotalVMTPeriod2")),
                        vmt_p3=to_number(rec.get("TotalVMTPeriod3")), vmt_zev=to_number(rec.get("TotalVMTZEV")),
                        passengers=to_number(rec.get("TotalPassengersCarried")), pmt=to_number(rec.get("TotalPMT")),
                        wav_requested=to_number(rec.get("TotalWAVsRequested")),
                        wav_fulfilled=to_number(rec.get("TotalWAVsFulfilled")),
                        source_file=path.split("/")[-1]))
                log.append(f"standard  {q} {co:7} {path.split('/')[-1]}")
                continue
            # LEGACY layout: one sheet per mode (+ occupancy sheets)
            for ws in wb.worksheets:
                title = ws.title.lower()
                if "cover" in title:
                    continue
                mode = ("drivered" if "drivered" in title else
                        "driverless" if "driverless" in title else
                        "drivered" if "drivered" in path.lower() else "not stated")
                t = sheet_table(ws)
                if "occupancy" in title:
                    long_rows += occupancy_rows(t, q, co, mode, path.split("/")[-1], "legacy-xlsx")
                elif "external passengers" in title:       # Tensor/AutoX: total external passengers
                    for r in t:
                        if r and str(r[0]).strip().lower() == "total" and to_number(r[1]) is not None:
                            long_rows.append(dict(quarter=q, company=co, mode=mode, metric="passengers",
                                                  value=to_number(r[1]), layout="legacy-xlsx",
                                                  source_file=path.split("/")[-1]))
                else:
                    long_rows += legacy_rows(t, q, co, mode, path.split("/")[-1], "legacy-xlsx")
            log.append(f"legacy    {q} {co:7} {path.split('/')[-1]}")

        elif m["table"] == "legacy_appendix":              # Waymo pilot appendix CSVs
            t = csv_table(path)
            name = path.split("/")[-1].lower()
            if "fleetwide" in name:
                long_rows += legacy_rows(t[1:], q, co, file_mode, path.split("/")[-1], "legacy-csv")
            elif "per-trip" in name or "per trip" in name or "per_trip" in name:
                long_rows += occupancy_rows(t, q, co, file_mode, path.split("/")[-1], "legacy-csv")
            log.append(f"appendix  {q} {co:7} {path.split('/')[-1]}")

    for name, rows in [("pilot_metrics_long.csv", long_rows), ("pilot_month_standard.csv", month_rows)]:
        with open(STAGING / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {len(rows)} rows to {name}")
    print("\n".join(log))


if __name__ == "__main__":
    main()