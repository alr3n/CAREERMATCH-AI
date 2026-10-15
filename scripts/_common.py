"""Shared helpers for the dataset and evaluation scripts.

Scripts are run from the repository root, e.g. ``python scripts/inspect_datasets.py``.
They import the backend package so that skill extraction, redaction and
scoring are exactly the code the API uses.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
BENCHMARK = ROOT / "ml" / "benchmark"
ARTIFACTS = ROOT / "ml" / "artifacts"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import pandas as pd  # noqa: E402

SUPPORTED = {".csv", ".json", ".jsonl", ".parquet"}


def load_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    if suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)
    if suffix == ".parquet":
        try:
            return pd.read_parquet(path)
        except ImportError as exc:  # pragma: no cover - depends on optional dependency
            raise SystemExit("Reading Parquet needs pyarrow: pip install -r backend/requirements-ml.txt") from exc
    raise ValueError(f"Unsupported file type: {path.name}")


def find_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
