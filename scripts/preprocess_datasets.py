#!/usr/bin/env python
"""Normalise downloaded datasets into role-specific, reproducible outputs.

Outputs (CSV) under data/processed/ plus a manifest recording, for every
dataset: input file hashes, rows loaded, rows removed per reason and rows
retained, the configuration and the random seed. Text is PII-redacted
(e-mail, phone) before it is written. Nothing is silently dropped.

Roles and output schemas:

* resume_parsing  -> resumes.csv : source, source_id, category, text, extracted_skills
* job_processing  -> jobs.csv    : source, source_id, title, category, description, reference_skills, extracted_skills
* matching_pairs  -> pairs.csv   : source, source_id, job_text, resume_text, reference_label, label_origin

    python scripts/preprocess_datasets.py [keys...] [--raw-dir data/raw] [--out-dir data/processed] [--sample N]
"""

from __future__ import annotations

import argparse
import ast
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from _common import DATA_PROCESSED, DATA_RAW, file_sha256, find_files, load_table, write_json
from dataset_specs import SPECS, DatasetSpec
from validate_datasets import malformed_mask

from app.core.logging import redact
from app.ml.document_text import normalize_text
from app.ml.skill_extractor import find_skills_in_text

SEED = 42
MAX_CHARS = 20_000


def _clean_text(value: object) -> str:
    return redact(normalize_text(str(value), MAX_CHARS)) if isinstance(value, str) else ""


def _skills_list(value: object) -> str:
    if isinstance(value, list | tuple):
        items = value
    elif isinstance(value, str):
        stripped = value.strip()
        parsed = None
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except ValueError:
                try:  # Python-literal lists such as "['SQL', 'Python']"
                    parsed = ast.literal_eval(stripped)
                except (ValueError, SyntaxError):
                    parsed = None
        items = parsed if isinstance(parsed, list) else [p for p in stripped.replace(";", ",").split(",")]
    else:
        items = []
    return "; ".join(sorted({str(i).strip() for i in items if str(i).strip()}, key=str.lower))


def normalise(df: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    if spec.key == "kaggle_resume":
        out = pd.DataFrame({"source_id": df["ID"].astype(str), "category": df["Category"], "text": df["Resume_str"]})
    elif spec.key == "kaggle_job_descriptions":
        description = df["Job Description"].fillna("").astype(str)
        if "Responsibilities" in df.columns:
            description = description + "\n" + df["Responsibilities"].fillna("").astype(str)
        out = pd.DataFrame({
            "source_id": df["Job Id"].astype(str), "title": df["Job Title"], "category": df.get("Role"),
            "description": description, "reference_skills": df["skills"].map(_skills_list),
        })
    elif spec.key == "hf_job_skill_set":
        out = pd.DataFrame({
            "source_id": df["job_id"].astype(str), "title": df["job_title"], "category": df["category"],
            "description": df["job_description"], "reference_skills": df["job_skill_set"].map(_skills_list),
        })
    elif spec.key == "hf_resume_matching_v2":
        out = pd.DataFrame({
            "source_id": df.index.astype(str), "job_text": df["jobpost"], "resume_text": df["resume"],
            "reference_label": df["total_score"], "label_origin": "llm_generated",
        })
    elif spec.key == "hf_candidate_matching_synthetic":
        bullets = df["experience_bullets"].map(lambda b: " ".join(b) if isinstance(b, list | tuple) else str(b or "")) \
            if "experience_bullets" in df.columns else ""
        out = pd.DataFrame({
            "source_id": df["resume_id"].astype(str), "category": df["role"],
            "text": df["summary"].fillna("").astype(str) + "\n" + bullets,
            "reference_skills": df["skills"].map(_skills_list),
        })
    else:  # pragma: no cover
        raise ValueError(spec.key)
    out.insert(0, "source", spec.key)
    return out


def process(key: str, raw_dir: Path, out_dir: Path, sample: int | None) -> dict:
    spec = SPECS[key]
    files = find_files(raw_dir / key)
    if not files:
        return {"present": False}
    frames, inputs = [], []
    for path in files:
        df = load_table(path)
        missing = [c for c in spec.required_columns if c not in df.columns]
        if missing:
            return {"present": True, "error": f"{path.name} is missing required columns: {missing}"}
        inputs.append({"file": path.name, "sha256": file_sha256(path), "rows": int(len(df))})
        frames.append(normalise(df, spec))
    data = pd.concat(frames, ignore_index=True)
    loaded = len(data)
    removed: dict[str, int] = {}

    text_cols = [c for c in ("text", "description", "job_text", "resume_text") if c in data.columns]
    bad = pd.Series(False, index=data.index)
    for col in text_cols:
        bad |= malformed_mask(data[col])
    removed["empty_or_malformed_text"] = int(bad.sum())
    data = data[~bad]

    dedupe_cols = text_cols + [c for c in ("title",) if c in data.columns]
    dup = data.duplicated(subset=dedupe_cols)
    removed["duplicate_text"] = int(dup.sum())
    data = data[~dup]

    if sample and len(data) > sample:
        removed["not_sampled"] = len(data) - sample
        data = data.sample(n=sample, random_state=SEED)

    for col in text_cols:
        data[col] = data[col].map(_clean_text)
    if spec.language == "en":
        source_col = "text" if "text" in data.columns else ("description" if "description" in data.columns else None)
        if source_col:
            data["extracted_skills"] = data[source_col].map(lambda t: "; ".join(find_skills_in_text(t)))

    role_file = {"resume_parsing": "resumes", "job_processing": "jobs", "matching_pairs": "pairs"}[spec.role]
    out_path = out_dir / f"{role_file}__{key}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(out_path, index=False)
    summary = {
        "present": True, "role": spec.role, "inputs": inputs, "rows_loaded": loaded, "rows_removed": removed,
        "rows_retained": int(len(data)), "output": out_path.name,
    }
    print(f"{key}: loaded {loaded:,}, removed {sum(removed.values()):,} {removed}, retained {len(data):,} -> {out_path.name}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("datasets", nargs="*", choices=list(SPECS))
    parser.add_argument("--raw-dir", type=Path, default=DATA_RAW)
    parser.add_argument("--out-dir", type=Path, default=DATA_PROCESSED)
    parser.add_argument("--sample", type=int, default=None, help="optional reproducible sample size per dataset")
    args = parser.parse_args()
    manifest = {
        "created_at": datetime.now(UTC).isoformat(), "seed": SEED, "max_chars": MAX_CHARS,
        "config": {"sample": args.sample, "min_text_chars": 30, "pii_redaction": "email, phone"},
        "datasets": {},
    }
    for key in args.datasets or SPECS:
        manifest["datasets"][key] = process(key, args.raw_dir, args.out_dir, args.sample)
        if not manifest["datasets"][key].get("present"):
            print(f"{key}: not downloaded (skipped)")
    write_json(args.out_dir / "manifest.json", manifest)


if __name__ == "__main__":
    main()
