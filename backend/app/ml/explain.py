"""Turn a score breakdown into evidence-based, human-readable explanations.

Explanations are generated only from structured evidence — matched skills,
skills not found, the user's own experience entries and preference checks.
They never claim the user has a skill that is not in their profile, and they
describe absent skills as "not found in your resume", not as deficiencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ml.features import CandidateProfile, JobRecord
from app.ml.scoring import ScoreBreakdown

COMPONENT_LABELS = {
    "semantic_similarity": "Overall similarity between your profile and the description",
    "required_skill_coverage": "Required skills found in your resume",
    "preferred_skill_coverage": "Preferred skills found in your resume",
    "experience_compatibility": "Experience-level fit",
    "preference_compatibility": "Fit with your stated preferences",
    "profile_relevance": "Relevance to your target roles",
}


@dataclass
class Evidence:
    kind: str
    label: str
    detail: str | None = None
    requirement: str | None = None


def _relevant_experience(profile: CandidateProfile, skills: list[str]) -> list[Evidence]:
    wanted = {s.lower() for s in skills}
    found: list[tuple[int, Evidence]] = []
    for exp in profile.experiences:
        text = " ".join(x for x in (exp.title, exp.description) if x).lower()
        hits = sorted({s for s in skills if s.lower() in text})
        if hits:
            label = " at ".join(x for x in (exp.title, exp.organization) if x) or "Experience entry"
            if exp.is_internship and "intern" not in label.lower():
                label += " (internship)"
            found.append((len(hits), Evidence("relevant_experience", label, "Mentions " + ", ".join(hits))))
    for proj in profile.projects:
        proj_skills = {s.lower() for s in proj.skills}
        text = (proj.description or "").lower()
        hits = sorted({s for s in skills if s.lower() in proj_skills or s.lower() in text})
        if hits and wanted:
            found.append((len(hits), Evidence("relevant_experience", f"Project: {proj.name}", "Uses " + ", ".join(hits))))
    found.sort(key=lambda x: -x[0])
    return [e for _, e in found[:3]]


def build_evidence(profile: CandidateProfile, job: JobRecord, b: ScoreBreakdown, semantic_backend: str) -> list[Evidence]:
    ev: list[Evidence] = []
    req, pref = b.required, b.preferred

    # Reasons: strongest weighted contributions first.
    contributions = sorted(
        ((k, v * b.weights[k]) for k, v in b.components.items() if v is not None),
        key=lambda kv: -kv[1],
    )
    for key, _ in contributions[:3]:
        value = b.components[key]
        if key == "required_skill_coverage" and req.score is not None:
            total = len(req.matched) + len(req.related) + len(req.missing)
            noun = "skills mentioned in the posting" if req.used_mentioned_proxy else "required skills"
            text = f"{len(req.matched)} of {total} {noun} found in your resume"
            if req.related:
                text += f", plus {len(req.related)} related"
        elif key == "preferred_skill_coverage" and pref.score is not None:
            total = len(pref.matched) + len(pref.related) + len(pref.missing)
            text = f"{len(pref.matched)} of {total} preferred skills found in your resume"
        elif key == "semantic_similarity":
            text = f"Text similarity {value:.2f} between your profile and the description ({semantic_backend})"
        elif key == "experience_compatibility":
            text = f"Experience fit {value:.0%}: {b.experience_note}"
        elif key == "preference_compatibility":
            met = sum(1 for c in b.preference_checks if c.satisfied)
            text = f"{met} of {len(b.preference_checks)} of your preferences met"
        else:
            text = f"Role relevance: {b.relevance_note}"
        ev.append(Evidence("reason", COMPONENT_LABELS[key], text))

    for ref in req.matched:
        ev.append(Evidence("matched_skill", ref.skill, ref.evidence,
                           "mentioned" if req.used_mentioned_proxy else "required"))
    for ref in pref.matched:
        ev.append(Evidence("matched_skill", ref.skill, ref.evidence, "preferred"))
    for ref, mine in req.related + pref.related:
        level = "preferred" if any(ref is r for r, _ in pref.related) else "required"
        ev.append(Evidence(
            "related_skill",
            ref.skill,
            f"You list {mine}, which is related. Partial credit only — related skills are not treated as the same skill.",
            level,
        ))
    # Labels hold the skill name; the UI renders them as "not found in your resume".
    for ref in req.missing:
        ev.append(Evidence("missing_required", ref.skill, ref.evidence,
                           "mentioned" if req.used_mentioned_proxy else "required"))
    for ref in pref.missing:
        ev.append(Evidence("missing_preferred", ref.skill, ref.evidence, "preferred"))

    matched_names = [r.skill for r in req.matched + pref.matched]
    ev.extend(_relevant_experience(profile, matched_names))

    if b.experience_note:
        ev.append(Evidence("experience_level", f"Experience fit: {b.components['experience_compatibility']:.0%}",
                           b.experience_note))
    for check in b.preference_checks:
        ev.append(Evidence("preference", ("✓ " if check.satisfied else "✗ ") + check.name.replace("_", " ").capitalize(),
                           check.detail))

    # Caveats about the evidence itself.
    if req.used_mentioned_proxy:
        ev.append(Evidence("caveat", "Requirements not separated in posting",
                           "The posting does not list required skills separately, so skills mentioned anywhere "
                           "in the description were used instead."))
    if b.evidence_coverage < 0.75:
        missing = [COMPONENT_LABELS[k].lower() for k, v in b.components.items() if v is None]
        ev.append(Evidence("caveat", f"Score based on {b.evidence_coverage:.0%} of the scoring weight",
                           "Not enough information for: " + "; ".join(missing)
                           + ". Completing your profile preferences can make the score more informative."))
    if job.freshness == "stale":
        ev.append(Evidence("caveat", "Listing not recently verified",
                           "This listing has not been re-checked recently and may have closed."))
    if job.is_demo:
        ev.append(Evidence("caveat", "DEMO DATA", "This is a fictional listing used for demonstration."))
    if (
        not req.missing and not pref.missing and not req.related and not pref.related
        and (req.score is not None or pref.score is not None)
    ):
        ev.append(Evidence("caveat", "All listed skills found",
                           "All skills detected in this posting were found in your resume. Read the full "
                           "description — not every requirement can be detected automatically."))
    return ev
