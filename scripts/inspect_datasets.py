#!/usr/bin/env python
"""Inspect downloaded datasets: files, schema, size, nulls, text lengths, label
distribution and language. Personal data in samples is redacted.

    python scripts/inspect_datasets.py                 # all datasets
    python scripts/inspect_datasets.py hf_job_skill_set --raw-dir data/raw
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import DATA_RAW, find_files, load_table
from dataset_specs import SPECS

from app.core.logging import redact

_HANGUL = re.compile(r"[가-힣]")


def guess_language(texts: list[str]) -> str:
    sample = " ".join(texts)[:20000]
    if not sample:
        return "unknown"
    if len(_HANGUL.findall(sample)) / max(1, len(sample)) > 0.05:
        return "ko"
    ascii_ratio = sum(1 for ch in sample if ord(ch) < 128) / len(sample)
    return "en (likely)" if ascii_ratio > 0.95 else "mixed/unknown"


def inspect(key: str, raw_dir: Path) -> dict:
    spec = SPECS[key]
    files = find_files(raw_dir / key)
    print(f"\n=== {spec.name} [{key}] ===")
    print(f"Role: {spec.role} | Licence: {spec.license}")
    if not files:
        print(f"Not downloaded. Expected under {raw_dir / key}/")
        print(f"Download: {spec.download}")
        return {"key": key, "present": False}
    summary: dict = {"key": key, "present": True, "files": []}
    for path in files:
        df = load_table(path)
        print(f"\n-- {path.relative_to(raw_dir.parent) if raw_dir.parent in path.parents else path} --")
        print(f"rows={len(df):,} columns={len(df.columns)}")
        missing = [c for c in spec.required_columns if c not in df.columns]
        print("columns:", ", ".join(map(str, df.columns)))
        if missing:
            print("MISSING expected columns:", ", ".join(missing))
        nulls = (df.isna().mean() * 100).round(1)
        print("null %:", ", ".join(f"{c}={v}" for c, v in nulls.items() if v > 0) or "none")
        print(f"duplicate rows: {int(df.duplicated().sum()):,}")
        for col in spec.text_columns:
            if col in df.columns:
                lengths = df[col].dropna().astype(str).str.len()
                if len(lengths):
                    print(f"{col}: chars min={lengths.min()} median={int(lengths.median())} max={lengths.max()}")
        for col in spec.label_columns:
            if col in df.columns:
                counts = df[col].astype(str).value_counts().head(15)
                print(f"{col} distribution (top 15):", dict(counts))
        texts = [str(t) for col in spec.text_columns if col in df.columns for t in df[col].dropna().head(200)]
        print("language:", guess_language(texts), f"(card says {spec.language})")
        if texts:
            print("sample (redacted, 200 chars):", redact(texts[0][:200]).replace("\n", " "))
        summary["files"].append({"file": path.name, "rows": len(df), "missing_columns": missing})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("datasets", nargs="*", choices=list(SPECS), help="dataset keys (default: all)")
    parser.add_argument("--raw-dir", type=Path, default=DATA_RAW)
    args = parser.parse_args()
    for key in args.datasets or SPECS:
        inspect(key, args.raw_dir)


if __name__ == "__main__":
    main()
