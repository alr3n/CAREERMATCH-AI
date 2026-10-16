"""Skill-gap analysis grounded in actual job requirements."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.ml.learning_resources import demonstration_tip, project_idea_for, resources_for
from app.ml.taxonomy import category_of
from app.models import JobListing, MatchResult, User
from app.repositories import job_repository as repo
from app.schemas.activity import (
    GapExample,
    IdentifiedSkill,
    RecommendationsOut,
    ResourceOut,
    SkillFrequency,
    SkillGap,
    SkillGapReport,
    SkillRecommendation,
)
from app.services.match_service import latest_run_id
from app.services.profile_service import active_resume, get_profile

NOTE = (
    "Skills listed here appear in the selected job descriptions but were not found in your resume. That does not "
    "mean you lack them — if you have a skill, add it to your profile with evidence (a project or experience)."
)


def _target_jobs(db: Session, user: User, run_id: uuid.UUID | None, top_k: int) -> tuple[list[JobListing], str]:
    run_id = run_id or latest_run_id(db, user)
    if run_id is not None:
        jobs = db.scalars(
            select(JobListing)
            .join(MatchResult, MatchResult.job_id == JobListing.id)
            .where(MatchResult.user_id == user.id, MatchResult.run_id == run_id)
            .options(selectinload(JobListing.skills))
            .order_by(MatchResult.rank)
            .limit(top_k)
        ).all()
        if jobs:
            return list(jobs), f"Top {len(jobs)} recommended jobs from your latest matching run"
    raise AppError(400, "matches_required", "Generate job matches first so the gap analysis has target jobs.")


def gap_report(db: Session, user: User, run_id: uuid.UUID | None = None, top_k: int = 20) -> SkillGapReport:
    resume = active_resume(db, user)
    if resume is None:
        raise AppError(400, "resume_required", "Upload a resume first.")
    profile = get_profile(db, user)
    user_skills = {s.skill.lower() for s in resume.skills}
    developing = {s.lower() for s in profile.skills_to_develop or []}
    jobs, basis = _target_jobs(db, user, run_id, top_k)

    required = Counter()
    preferred = Counter()
    examples: dict[str, list[GapExample]] = defaultdict(list)
    requested = Counter()
    for job in jobs:
        for s in job.skills:
            if s.requirement not in {"required", "preferred"}:
                continue
            key = s.skill
            if key.lower() in user_skills:
                requested[key] += 1
                continue
            (required if s.requirement == "required" else preferred)[key] += 1
            if len(examples[key]) < 3:
                examples[key].append(GapExample(
                    job_id=job.id, title=job.title, company=job.company, requirement=s.requirement,
                    evidence=s.evidence,
                ))
    gaps = [
        SkillGap(
            skill=skill,
            category=category_of(skill),
            required_count=required[skill],
            preferred_count=preferred[skill],
            priority=2 * required[skill] + preferred[skill],
            in_development_list=skill.lower() in developing,
            examples=examples[skill],
        )
        for skill in set(required) | set(preferred)
    ]
    gaps.sort(key=lambda g: (-g.priority, g.skill.lower()))

    identified = sorted(
        (IdentifiedSkill(skill=s.skill, category=s.category, jobs_requesting=requested.get(s.skill, 0)) for s in resume.skills),
        key=lambda x: (-x.jobs_requesting, x.skill.lower()),
    )

    # Frequency across every visible listing (not just the user's matches).
    stmt = repo.visible_listings()
    all_jobs = db.scalars(stmt.options(selectinload(JobListing.skills))).all()
    freq = Counter()
    for job in all_jobs:
        for skill in {s.skill for s in job.skills if s.requirement in {"required", "preferred"}}:
            freq[skill] += 1
    total = len(all_jobs) or 1
    frequency = [
        SkillFrequency(skill=k, jobs=v, share=round(v / total, 3), user_has=k.lower() in user_skills)
        for k, v in freq.most_common(20)
    ]
    return SkillGapReport(
        basis=basis,
        jobs_analyzed=len(jobs),
        target_titles=list(dict.fromkeys(j.title for j in jobs))[:10],
        identified_skills=identified,
        gaps=gaps[:30],
        skill_frequency=frequency,
        total_listings=len(all_jobs),
        note=NOTE,
    )


def recommendations(db: Session, user: User, run_id: uuid.UUID | None = None, limit: int = 8) -> RecommendationsOut:
    report = gap_report(db, user, run_id)
    recs = []
    for gap in report.gaps[:limit]:
        parts = []
        if gap.required_count:
            parts.append(f"required in {gap.required_count} of your top jobs")
        if gap.preferred_count:
            parts.append(f"preferred in {gap.preferred_count}")
        resources = resources_for(gap.skill)
        recs.append(SkillRecommendation(
            skill=gap.skill,
            why=f"{gap.skill} is " + " and ".join(parts) + ".",
            project_idea=project_idea_for(gap.skill),
            how_to_demonstrate=demonstration_tip(gap.skill),
            resources=[ResourceOut(title=r.title, url=r.url, provider=r.provider, cost=r.cost) for r in resources],
            resources_note=None if resources else
            "No curated resource yet — the official documentation for this tool is usually the best free starting point.",
        ))
    return RecommendationsOut(
        basis=report.basis,
        recommendations=recs,
        note="All linked resources are free. Recommendations are suggestions; you decide what to learn.",
    )
