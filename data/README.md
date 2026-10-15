# data/

Local working directory for external datasets. **Downloaded data is never committed.** `data/raw/`, `data/processed/` and `data/interim/` are git-ignored.

```
data/
  raw/<dataset_key>/        files exactly as downloaded
  processed/                outputs of scripts/preprocess_datasets.py + manifest.json
```

## Getting the data

1. Check each dataset's licence on its page first (see `docs/DATASET_CARD.md`). Several are **unverified**.
2. Download into `data/raw/<dataset_key>/`. `python scripts/inspect_datasets.py` prints the exact command for each dataset key:

| Key | Source |
|---|---|
| `kaggle_resume` | https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset (needs a Kaggle account / API token) |
| `kaggle_job_descriptions` | https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset |
| `hf_job_skill_set` | https://huggingface.co/datasets/batuhanmtl/job-skill-set |
| `hf_resume_matching_v2` | https://huggingface.co/datasets/Divyanandh/resume-matching-dataset-v2 |
| `hf_candidate_matching_synthetic` | https://huggingface.co/datasets/michaelozon/candidate-matching-synthetic |

3. Run the pipeline from the repository root:

```bash
pip install -r backend/requirements-ml.txt      # adds pyarrow for Parquet files
python scripts/inspect_datasets.py               # schema, size, language, label distribution
python scripts/validate_datasets.py --report data/processed/validation.json
python scripts/preprocess_datasets.py            # writes data/processed/*.csv + manifest.json
```

## Privacy

Resume datasets may contain real personal information. Keep them on your machine, don't upload them to external AI services, and don't paste samples into issues or reports. The scripts redact e-mail addresses and phone numbers in their output and printed samples, but redaction isn't anonymisation: names and addresses may remain in free text.

## Not live data

Nothing in this folder is a current job vacancy. Live listings come only from the configured job-board providers.
