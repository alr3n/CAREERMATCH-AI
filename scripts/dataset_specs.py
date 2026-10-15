"""Candidate datasets: provenance, expected schema and intended role.

Facts recorded here come from the dataset cards that could be inspected on
2026-10-14 (Hugging Face) — see docs/DATASET_CARD.md. Kaggle pages could not
be read without an account, so their schemas below are *expected* columns to
be confirmed by ``inspect_datasets.py`` once the files are downloaded.
Licences marked "unverified" must be checked before any use beyond local
experimentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    name: str
    url: str
    role: str  # resume_parsing | job_processing | matching_pairs
    required_columns: tuple[str, ...]
    text_columns: tuple[str, ...]
    id_column: str | None = None
    label_columns: tuple[str, ...] = ()
    language: str = "en"
    license: str = "unverified"
    provenance: str = ""
    cautions: tuple[str, ...] = field(default_factory=tuple)
    download: str = ""


SPECS: dict[str, DatasetSpec] = {
    "kaggle_resume": DatasetSpec(
        key="kaggle_resume",
        name="Kaggle Resume Dataset (snehaanbhawal)",
        url="https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset",
        role="resume_parsing",
        required_columns=("ID", "Resume_str", "Category"),
        text_columns=("Resume_str",),
        id_column="ID",
        label_columns=("Category",),
        license="unverified — check the Kaggle page before use",
        provenance="Described on Kaggle as resumes in PDF and string form for data extraction. Origin not confirmed.",
        cautions=(
            "Real resumes may contain personal data: keep local, redact before any display or logging.",
            "Category labels are job categories, not skill annotations; they cannot evaluate skill extraction alone.",
        ),
        download="kaggle datasets download -d snehaanbhawal/resume-dataset -p data/raw/kaggle_resume --unzip",
    ),
    "kaggle_job_descriptions": DatasetSpec(
        key="kaggle_job_descriptions",
        name="Kaggle Job Description Dataset (ravindrasinghrana)",
        url="https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset",
        role="job_processing",
        required_columns=("Job Id", "Job Title", "Job Description", "skills"),
        text_columns=("Job Description", "skills", "Responsibilities"),
        id_column="Job Id",
        license="unverified — check the Kaggle page before use",
        provenance="Kaggle page describes it as a comprehensive job dataset; whether postings are real or generated is not confirmed.",
        cautions=(
            "Historical/static postings: never shown as current vacancies.",
            "If the data is synthetic, it can test parsing robustness but not real-world matching quality.",
        ),
        download="kaggle datasets download -d ravindrasinghrana/job-description-dataset -p data/raw/kaggle_job_descriptions --unzip",
    ),
    "hf_job_skill_set": DatasetSpec(
        key="hf_job_skill_set",
        name="Hugging Face batuhanmtl/job-skill-set",
        url="https://huggingface.co/datasets/batuhanmtl/job-skill-set",
        role="job_processing",
        required_columns=("job_id", "category", "job_title", "job_description", "job_skill_set"),
        text_columns=("job_description", "job_skill_set"),
        id_column="job_id",
        label_columns=("category",),
        license="not stated on card; inherits terms of the source LinkedIn postings dataset on Kaggle (unverified)",
        provenance="1,167 English postings (5 categories) derived from a Kaggle LinkedIn job postings dataset; skill lists "
                   "were extracted automatically with an external API, not manually annotated.",
        cautions=(
            "Skill labels are machine-generated: usable as a weak reference, not as gold annotations.",
            "Some descriptions are upper-case or have merged words; normalisation is required.",
        ),
        download="huggingface-cli download batuhanmtl/job-skill-set --repo-type dataset --local-dir data/raw/hf_job_skill_set",
    ),
    "hf_resume_matching_v2": DatasetSpec(
        key="hf_resume_matching_v2",
        name="Hugging Face Divyanandh/resume-matching-dataset-v2",
        url="https://huggingface.co/datasets/Divyanandh/resume-matching-dataset-v2",
        role="matching_pairs",
        required_columns=("jobpost", "resume", "total_score"),
        text_columns=("jobpost", "resume", "selfintro"),
        label_columns=("resume_grade", "total_score"),
        language="ko",
        license="not stated on card",
        provenance="74,147 fully synthetic Korean job-post/resume pairs generated with GPT-4o-mini, including the scores.",
        cautions=(
            "Korean language — the English skill taxonomy does not apply.",
            "Scores are LLM-generated, so they are not ground-truth relevance labels.",
        ),
        download="huggingface-cli download Divyanandh/resume-matching-dataset-v2 --repo-type dataset --local-dir data/raw/hf_resume_matching_v2",
    ),
    "hf_candidate_matching_synthetic": DatasetSpec(
        key="hf_candidate_matching_synthetic",
        name="Hugging Face michaelozon/candidate-matching-synthetic",
        url="https://huggingface.co/datasets/michaelozon/candidate-matching-synthetic",
        role="matching_pairs",
        required_columns=("resume_id", "role", "seniority", "skills", "summary"),
        text_columns=("summary",),
        id_column="resume_id",
        label_columns=("role", "seniority"),
        license="MIT (per dataset card)",
        provenance="Synthetic English resumes generated with Qwen2.5-0.5B-Instruct (seed 42); match labels defined by a rule "
                   "(≥60% must-have skill overlap).",
        cautions=(
            "Match labels are rule-derived from skill overlap, so they would reward a skill-overlap ranker by construction.",
            "Sample rows show templated, repetitive text.",
        ),
        download="huggingface-cli download michaelozon/candidate-matching-synthetic --repo-type dataset --local-dir data/raw/hf_candidate_matching_synthetic",
    ),
}
