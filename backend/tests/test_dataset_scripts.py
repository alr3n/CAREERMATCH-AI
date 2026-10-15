"""Tests for scripts/ (dataset validation, preprocessing and evaluation) on tiny synthetic fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
PY = sys.executable


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(SCRIPTS / script), *args], capture_output=True, text=True, cwd=ROOT, timeout=300)


def make_raw(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    (raw / "hf_job_skill_set").mkdir(parents=True)
    pd.DataFrame({
        "job_id": [1, 2, 3, 4],
        "category": ["IT", "IT", "HR", "IT"],
        "job_title": ["Data Analyst", "Data Analyst", "HR Officer", "Broken"],
        "job_description": [
            "We need SQL and Python skills. Contact hr@example.com or +63 917 123 4567 for details please.",
            "We need SQL and Python skills. Contact hr@example.com or +63 917 123 4567 for details please.",
            "Recruitment and onboarding of new staff, strong communication skills are required here.",
            "",
        ],
        "job_skill_set": ["['SQL', 'Python']", "['SQL', 'Python']", "['Recruitment']", "[]"],
    }).to_csv(raw / "hf_job_skill_set" / "train.csv", index=False)
    (raw / "kaggle_resume").mkdir()
    pd.DataFrame({"ID": [1], "Resume_text_wrong_name": ["x"], "Category": ["HR"]}).to_csv(raw / "kaggle_resume" / "Resume.csv", index=False)
    return raw


def test_validate_reports_missing_columns(tmp_path):
    raw = make_raw(tmp_path)
    result = run("validate_datasets.py", "--raw-dir", str(raw), "--report", str(tmp_path / "v.json"))
    assert result.returncode == 1  # kaggle_resume lacks Resume_str
    report = json.loads((tmp_path / "v.json").read_text())
    assert report["kaggle_resume"]["files"]["Resume.csv"]["missing_required_columns"] == ["Resume_str"]
    hf = report["hf_job_skill_set"]["files"]["train.csv"]
    assert hf["duplicate_rows"] == 0 and hf["duplicate_text"] == 1 and hf["text_issues"]["job_description"]["missing_or_malformed"] == 1


def test_preprocess_counts_redacts_and_writes_manifest(tmp_path):
    raw = make_raw(tmp_path)
    out = tmp_path / "processed"
    result = run("preprocess_datasets.py", "hf_job_skill_set", "--raw-dir", str(raw), "--out-dir", str(out))
    assert result.returncode == 0, result.stderr
    manifest = json.loads((out / "manifest.json").read_text())
    entry = manifest["datasets"]["hf_job_skill_set"]
    assert entry["rows_loaded"] == 4
    assert entry["rows_removed"] == {"empty_or_malformed_text": 1, "duplicate_text": 1}
    assert entry["rows_retained"] == 2
    assert manifest["seed"] == 42 and entry["inputs"][0]["sha256"]
    data = pd.read_csv(out / "jobs__hf_job_skill_set.csv")
    text = " ".join(data["description"])
    assert "hr@example.com" not in text and "917 123" not in text
    assert set(data.columns) >= {"source", "source_id", "title", "description", "reference_skills", "extracted_skills"}
    assert "Python; SQL" in data["reference_skills"].tolist()


def test_inspect_handles_missing_datasets(tmp_path):
    result = run("inspect_datasets.py", "hf_candidate_matching_synthetic", "--raw-dir", str(tmp_path / "nothing"))
    assert result.returncode == 0 and "Not downloaded" in result.stdout


def test_evaluation_is_reproducible(tmp_path):
    out1, out2 = tmp_path / "a.json", tmp_path / "b.json"
    assert run("evaluate_matching.py", "--out", str(out1), "--bootstrap", "50").returncode == 0
    assert run("evaluate_matching.py", "--out", str(out2), "--bootstrap", "50").returncode == 0
    a, b = json.loads(out1.read_text()), json.loads(out2.read_text())
    for report in (a, b):
        report.pop("evaluated_at")
        report.pop("performance")
    assert a == b
    assert a["dataset"]["pairs"] == 360 and a["dataset"]["split"] == "test (100%)"
    models = {r["model"] for r in a["runs"]}
    assert {"keyword-overlap", "tfidf-cosine", "transparent-v1"} <= models
    for run_ in a["runs"]:
        assert 0 <= run_["metrics"]["ndcg@10"] <= 1
    assert a["limitations"]
