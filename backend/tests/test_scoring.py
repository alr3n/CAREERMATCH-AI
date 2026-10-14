from decimal import Decimal

import pytest

from app.ml.baselines import keyword_overlap_scores, tfidf_cosine_scores
from app.ml.embeddings import LSABackend
from app.ml.explain import build_evidence
from app.ml.features import CandidateProfile, JobRecord, JobSkillRef
from app.ml.scoring import DEFAULT_WEIGHTS, normalise_weights, rank, score_job


def refs(*names):
    return [JobSkillRef(n, f"Requirement mentioning {n}") for n in names]


def job(**kw):
    defaults = dict(id="j1", title="Data Analyst Intern", company="Co", description="Analyse data with SQL and Python.",
                    experience_level="internship", employment_type="internship", work_arrangement="remote",
                    location="Remote", required_skills=refs("SQL", "Python"), preferred_skills=refs("Power BI"))
    defaults.update(kw)
    return JobRecord(**defaults)


def profile(**kw):
    defaults = dict(skills={"SQL", "Python"}, career_stage="student", work_arrangements=["remote"],
                    employment_types=["internship"], preferred_titles=["Data Analyst"])
    defaults.update(kw)
    return CandidateProfile(**defaults)


def test_exact_skill_matches():
    b = score_job(profile(), job(), semantic=0.5)
    assert b.components["required_skill_coverage"] == 1.0
    assert [r.skill for r in b.required.matched] == ["SQL", "Python"]


def test_related_skill_gets_partial_credit_but_is_not_a_match():
    b = score_job(profile(skills={"MySQL", "Python"}), job(required_skills=refs("PostgreSQL", "Python")), 0.5)
    assert b.components["required_skill_coverage"] == pytest.approx(0.75)
    assert [r.skill for r in b.required.matched] == ["Python"]
    assert b.required.related[0][0].skill == "PostgreSQL" and b.required.related[0][1] == "MySQL"


def test_missing_required_and_preferred():
    b = score_job(profile(skills={"Excel"}), job(), 0.2)
    assert b.components["required_skill_coverage"] == 0.0
    assert {r.skill for r in b.required.missing} == {"SQL", "Python"}
    assert {r.skill for r in b.preferred.missing} == {"Power BI"}


def test_empty_job_description_and_skills():
    b = score_job(profile(), job(description="", required_skills=[], preferred_skills=[]), semantic=0.0)
    assert b.components["required_skill_coverage"] is None
    assert b.components["preferred_skill_coverage"] is None
    assert 0 <= b.score <= 100
    assert b.evidence_coverage < 1


def test_mentioned_skills_used_as_explicit_proxy():
    b = score_job(profile(), job(required_skills=[], mentioned_skills=refs("SQL")), 0.3)
    assert b.required.used_mentioned_proxy is True
    evidence = build_evidence(profile(), job(required_skills=[], mentioned_skills=refs("SQL")), b, "lsa")
    assert any(e.kind == "caveat" and "not list required skills" in e.detail for e in evidence)


def test_empty_profile_is_handled():
    empty = CandidateProfile(skills=set())
    b = score_job(empty, job(), semantic=0.1)
    assert b.components["preference_compatibility"] is None
    assert b.components["profile_relevance"] is None
    assert b.components["experience_compatibility"] is None
    assert b.score == pytest.approx(100 * (0.35 * 0.1) / (0.35 + 0.30 + 0.10), abs=0.01)


def test_conflicting_preferences_lower_preference_score():
    onsite_job = job(work_arrangement="onsite", location="Cebu City", employment_type="full_time")
    b = score_job(profile(preferred_locations=["Makati"]), onsite_job, 0.5)
    assert b.components["preference_compatibility"] == 0.0
    assert all(not c.satisfied for c in b.preference_checks)


def test_remote_job_satisfies_location_preference():
    b = score_job(profile(preferred_locations=["Davao"]), job(), 0.5)
    loc = next(c for c in b.preference_checks if c.name == "location")
    assert loc.satisfied


def test_metro_manila_preference_covers_ncr_cities():
    b = score_job(profile(preferred_locations=["Metro Manila"], work_arrangements=["hybrid"]),
                  job(work_arrangement="hybrid", location="Taguig, Metro Manila"), 0.5)
    assert next(c for c in b.preference_checks if c.name == "location").satisfied


def test_salary_only_compared_with_same_currency():
    p = profile(min_salary=Decimal("20000"), salary_currency="PHP")
    same = score_job(p, job(salary_max=Decimal("15000"), salary_currency="PHP", salary_interval="per-month-salary"), 0.5)
    other = score_job(p, job(salary_max=Decimal("15000"), salary_currency="USD"), 0.5)
    assert any(c.name == "salary" and not c.satisfied for c in same.preference_checks)
    assert not any(c.name == "salary" for c in other.preference_checks)


def test_score_normalisation_and_weights():
    w = normalise_weights({"semantic_similarity": 2, "required_skill_coverage": 2})
    assert sum(w.values()) == pytest.approx(1.0)
    assert normalise_weights({"semantic_similarity": 0, "required_skill_coverage": 0, "preferred_skill_coverage": 0,
                              "experience_compatibility": 0, "preference_compatibility": 0,
                              "profile_relevance": 0}) == DEFAULT_WEIGHTS
    perfect = score_job(profile(skills={"SQL", "Python", "Power BI"}), job(), semantic=1.0)
    assert perfect.score == pytest.approx(100.0)
    zero = score_job(CandidateProfile(skills=set(), work_arrangements=["onsite"]), job(), semantic=0.0)
    assert zero.score == 0.0


def test_semantic_score_is_clipped():
    assert score_job(profile(), job(), semantic=1.7).components["semantic_similarity"] == 1.0
    assert score_job(profile(), job(), semantic=-0.3).components["semantic_similarity"] == 0.0


def test_ranking_is_deterministic():
    jobs = [job(id=f"j{i}", title=t) for i, t in enumerate(["Data Analyst Intern", "Data Analyst Intern", "HR Intern"])]
    first = [j.id for j, _ in rank(profile(), jobs, [0.5, 0.5, 0.5])]
    second = [j.id for j, _ in rank(profile(), list(reversed(jobs)), [0.5, 0.5, 0.5])]
    assert first == second
    assert first[:2] == ["j0", "j1"]  # ties broken by id


def test_explanations_never_claim_deficiency():
    b = score_job(profile(skills={"Excel"}), job(), 0.2)
    evidence = build_evidence(profile(skills={"Excel"}), job(), b, "lsa")
    text = " ".join(f"{e.label} {e.detail or ''}" for e in evidence).lower()
    assert "lack" not in text and "you don't have" not in text
    assert {e.label for e in evidence if e.kind == "missing_required"} == {"SQL", "Python"}


def test_semantically_related_text_scores_higher():
    backend = LSABackend()
    sims = backend.similarities(
        "Python SQL pandas data cleaning dashboards analysis",
        ["Data analyst: SQL, Python, pandas, dashboards and data analysis",
         "Graphic designer: Photoshop, Illustrator, branding and print layouts"],
    )
    assert sims[0] > sims[1]


def test_baselines():
    jobs = [job(id="a"), job(id="b", required_skills=refs("Figma"), preferred_skills=[], description="Design with Figma")]
    kw = keyword_overlap_scores(profile(), jobs)
    tf = tfidf_cosine_scores(profile(), jobs)
    assert kw[0] > kw[1] and len(tf) == 2
