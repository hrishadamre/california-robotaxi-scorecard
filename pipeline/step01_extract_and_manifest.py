"""Step 01: unzip each quarterly CPUC zip and write a manifest of every file.

Why a manifest: it is the data lineage record. Every number in the report can be
traced back to a file, its quarter, company, program (deployment or pilot),
mode (driverless or drivered) and table type. It also catches surprises early,
for example a file that matches no known table type.

Run:  python pipeline/step01_extract_and_manifest.py
"""
import csv
import zipfile

import openpyxl

from common import RAW, EXTRACTED, STAGING, quarter_from_name, company_from_parts, table_type

CONVERTED = STAGING / "converted"


def real_format(path) -> str:
    """Look at the first bytes, not the extension. One pilot 'trips .csv' is
    really an Excel workbook (an .xlsx file starts with the zip signature PK)."""
    head = open(path, "rb").read(4)
    if head.startswith(b"PK\x03\x04"):
        return "xlsx"
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf16"
    return "csv"


def convert_xlsx_to_csv(src, rel):
    """Write the first sheet of a disguised workbook as a real CSV in staging."""
    dst = CONVERTED / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as fh:                    # pass a file object: openpyxl checks extensions
        wb = openpyxl.load_workbook(fh, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        with open(dst, "w", newline="", encoding="utf-8") as out:
            w = csv.writer(out)
            for row in ws.iter_rows(values_only=True):
                w.writerow(["" if v is None else v for v in row])
    return dst


def extract_inner_zips() -> int:
    count = 0
    for program_dir, program in [("CPUC Deployment Data", "deployment"), ("CPUC Pilot Data", "pilot")]:
        for z in sorted((RAW / program_dir).glob("*.zip")):
            target = EXTRACTED / program / z.stem
            if target.exists():          # already extracted on an earlier run
                continue
            with zipfile.ZipFile(z) as zf:
                members = [m for m in zf.namelist()
                           if not m.startswith("__MACOSX") and not m.endswith(".DS_Store")]
                zf.extractall(target, members)
            count += 1
    return count


def build_manifest() -> list[dict]:
    rows = []
    for program in ["deployment", "pilot"]:
        for f in sorted((EXTRACTED / program).rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(EXTRACTED / program)
            quarter_folder = rel.parts[0]
            company, filed_as = company_from_parts(rel.parts[1:-1])
            if program == "deployment":
                company, filed_as = "Waymo", "Waymo"
            fmt = real_format(f) if f.suffix.lower() == ".csv" else f.suffix.lower().lstrip(".")
            read_path = f
            if f.suffix.lower() == ".csv" and fmt == "xlsx":
                read_path = convert_xlsx_to_csv(f, rel)
                print("CONVERTED disguised workbook:", rel)
            rows.append({
                "path": f.as_posix(),
                "read_path": read_path.as_posix(),
                "real_format": fmt,
                "program": program,
                "quarter": quarter_from_name(quarter_folder),
                "company": company,
                "company_as_filed": filed_as,
                "mode": "drivered" if "drivered" in f.as_posix().lower() else "driverless",
                "table": table_type(f.name) if f.suffix.lower() == ".csv" else f.suffix.lower().lstrip("."),
                "bytes": f.stat().st_size,
            })
    return rows


if __name__ == "__main__":
    STAGING.mkdir(parents=True, exist_ok=True)
    n = extract_inner_zips()
    print(f"Extracted {n} quarterly zips")
    rows = build_manifest()
    out = STAGING / "manifest.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}")
    unknown = [r for r in rows if r["quarter"] is None or (r["program"] == "pilot" and r["company"] is None)]
    for r in unknown:
        print("CHECK: could not classify", r["path"])
    other = [r for r in rows if r["table"] == "other"]
    for r in other:
        print("CHECK: unknown table type", r["path"])