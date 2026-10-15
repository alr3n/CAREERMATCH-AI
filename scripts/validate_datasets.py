#!/usr/bin/env python
"""Validate downloaded datasets before preprocessing.

Checks each file for required columns, empty or malformed text, duplicate
records and duplicate IDs, and prints a report. Exits with status 1 if a
present dataset is missing required columns (so CI or a Makefile can stop).

    python scripts/validate_datasets.py [keys...] [--raw-dir data/raw] [--report path.json]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from _common import DATA_RAW, find_files, load_table, write_json
from dataset_specs import SPECS, DatasetSpec

MIN_TEXT_CHARS = 30
_HTML_ONLY = re.compile(r"^\s*(<[^>]+>\s*)+$")


def malformed_mask(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str)
    printable = text.map(lambda s: (sum(ch.isprintable() or ch in "\n\t" for ch in s) / len(s)) if s else 0.0)
    return (text.str.strip().str.len() < MIN_TEXT_CHARS) | (printable < 0.9) | text.str.match(_HTML_ONLY)


def validate_frame(df: pd.DataFrame, spec: DatasetSpec) -> dict:
    report: dict = {"rows": int(len(df))}
    missing = [c for c in spec.required_columns if c not in df.columns]
    report["missing_required_columns"] = missing
    report["duplicate_rows"] = int(df.duplicated().sum())
    present_text = [c for c in spec.text_columns if c in df.columns]
    report["duplicate_text"] = int(df.duplicated(subset=present_text).sum()) if present_text else 0
    if spec.id_column and spec.id_column in df.columns:
        report["duplicate_ids"] = int(df[spec.id_column].duplicated().sum())
    text_issues = {}
    for col in spec.text_columns:
        if col in df.columns:
            mask = malformed_mask(df[col])
            text_issues[col] = {"missing_or_malformed": int(mask.sum()), "share": round(float(mask.mean()), 4) if len(df) else 0.0}
    report["text_issues"] = text_issues
    report["null_share"] = {c: round(float(v), 4) for c, v in df.isna().mean().items() if v > 0}
    report["ok"] = not missing
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("datasets", nargs="*", choices=list(SPECS))
    parser.add_argument("--raw-dir", type=Path, default=DATA_RAW)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    results: dict = {}
    failed = False
    for key in args.datasets or SPECS:
        spec = SPECS[key]
        files = find_files(args.raw_dir / key)
        if not files:
            results[key] = {"present": False}
            print(f"{key}: not downloaded (skipped)")
            continue
        results[key] = {"present": True, "files": {}}
        for path in files:
            rep = validate_frame(load_table(path), spec)
            results[key]["files"][path.name] = rep
            status = "OK" if rep["ok"] else "FAILED"
            failed |= not rep["ok"]
            print(f"{key}/{path.name}: {status} rows={rep['rows']:,} duplicate_rows={rep['duplicate_rows']:,} "
                  f"duplicate_text={rep['duplicate_text']:,} "
                  f"missing_columns={rep['missing_required_columns'] or '-'}")
            for col, issue in rep["text_issues"].items():
                print(f"    {col}: {issue['missing_or_malformed']:,} empty/malformed ({issue['share']:.1%})")
    if args.report:
        write_json(args.report, results)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
