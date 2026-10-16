"""Plain data representations used by the matcher, baselines and evaluation.

They decouple the ML code from the ORM so that the same scoring code runs in
the API and in offline evaluation scripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ExperienceEntry:
    title: str | None
    organization: str | None
    description: str | None
    is_internship: bool = False


@dataclass
class ProjectEntry:
    name: str
    description: str | None
    skills: list[str] = field(default_factory=list)


@dataclass
class CandidateProfile:
    skills: set[str]
    skill_evidence: dict[str, str] = field(default_factory=dict)
    experiences: list[ExperienceEntry] = field(default_factory=list)
    projects: list[ProjectEntry] = field(default_factory=list)
    education_fields: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    summary: str | None = None
    total_experience_months: int | None = None
    career_stage: str | None = None
    preferred_titles: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    work_arrangements: list[str] = field(default_factory=list)
    employment_types: list[str] = field(default_factory=list)
    min_salary: Decimal | None = None
    salary_currency: str | None = None

    def document(self) -> str:
        """Text used for semantic similarity — built from the (user-correctable)
        structured profile, not the raw resume text."""
        parts: list[str] = []
        if self.preferred_titles:
            parts.append("Target roles: " + ", ".join(self.preferred_titles))
        if self.summary:
            parts.append(self.summary)
        if self.skills:
            parts.append("Skills: " + ", ".join(sorted(self.skills)))
        for exp in self.experiences:
            parts.append(" ".join(x for x in (exp.title, exp.organization, exp.description) if x))
        for proj in self.projects:
            parts.append(" ".join(x for x in (proj.name, proj.description, ", ".join(proj.skills)) if x))
        if self.education_fields:
            parts.append("Education: " + ", ".join(self.education_fields))
        if self.certifications:
            parts.append("Certifications: " + ", ".join(self.certifications))
        return "\n".join(parts)


@dataclass
class JobSkillRef:
    skill: str
    evidence: str | None = None


@dataclass
class JobRecord:
    id: str
    title: str
    company: str
    description: str
    category: str | None = None
    location: str | None = None
    work_arrangement: str = "unknown"
    employment_type: str = "unknown"
    experience_level: str = "unknown"
    min_years_experience: int | None = None
    required_skills: list[JobSkillRef] = field(default_factory=list)
    preferred_skills: list[JobSkillRef] = field(default_factory=list)
    mentioned_skills: list[JobSkillRef] = field(default_factory=list)
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    salary_interval: str | None = None
    department: str | None = None
    freshness: str = "fresh"

    def document(self) -> str:
        return f"{self.title}\n{self.description[:6000]}"
