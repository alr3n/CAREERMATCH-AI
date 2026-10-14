"""Dictionary-based skill extraction with evidence.

Skills are found by matching the curated taxonomy against text line by line.
Every match keeps the line it came from as evidence so that users (and the
explanation layer) can see *why* a skill was detected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.logging import redact
from app.ml.taxonomy import SKILLS, SkillDef

_LIST_SEPARATORS = re.compile(r"[,;|•·/]")


@dataclass(frozen=True)
class SkillMatch:
    name: str
    category: str
    evidence: str
    line_index: int
    in_skill_context: bool


def _term_pattern(term: str, case_sensitive: bool) -> re.Pattern[str]:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(rf"(?<![\w+#.\-]){escaped}(?![\w+#])", flags)


@lru_cache(maxsize=1)
def _compiled() -> tuple[tuple[SkillDef, tuple[re.Pattern[str], ...]], ...]:
    compiled = []
    for skill in SKILLS:
        patterns = [_term_pattern(skill.name, skill.case_sensitive or skill.strict)]
        for alias in skill.aliases:
            if alias.startswith("="):
                patterns.append(_term_pattern(alias[1:], True))
            else:
                patterns.append(_term_pattern(alias, skill.strict))
        compiled.append((skill, tuple(patterns)))
    return tuple(compiled)


def looks_like_list(line: str) -> bool:
    """A line such as 'Python, SQL, Go, Docker' or 'Languages: C | R | Go'."""
    body = line.split(":", 1)[1] if ":" in line[:40] else line
    parts = [p.strip() for p in _LIST_SEPARATORS.split(body) if p.strip()]
    if len(parts) < 3:
        return False
    if body.rstrip().endswith(".") and len(parts) < 4:
        return False  # most likely a sentence with commas
    short = sum(1 for p in parts if len(p.split()) <= 3)
    return short / len(parts) >= 0.8


def clean_evidence(line: str, limit: int = 200) -> str:
    text = redact(" ".join(line.split()))
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def extract_skills(lines: list[str], skill_context: set[int] | None = None) -> list[SkillMatch]:
    """Return one match per canonical skill (first, most contextual occurrence).

    ``skill_context`` holds indices of lines inside a "Skills" section. Lines
    that look like comma-separated lists are also treated as skill context.
    """
    skill_context = skill_context or set()
    found: dict[str, SkillMatch] = {}
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        in_context = idx in skill_context or looks_like_list(line)
        for skill, patterns in _compiled():
            if skill.strict and not in_context:
                continue
            if any(p.search(line) for p in patterns):
                existing = found.get(skill.name)
                if existing is None or (in_context and not existing.in_skill_context):
                    found[skill.name] = SkillMatch(
                        name=skill.name,
                        category=skill.category,
                        evidence=clean_evidence(line),
                        line_index=idx,
                        in_skill_context=in_context,
                    )
    return sorted(found.values(), key=lambda m: m.name.lower())


def find_skills_in_text(text: str) -> list[str]:
    """Convenience: canonical skill names mentioned anywhere in ``text``."""
    return [m.name for m in extract_skills(text.splitlines())]
