"""Rule-based structured profile extraction from resume text.

Design principles (see docs/ML_METHODOLOGY.md):

* Extract only what the text supports. Nothing is inferred from absence —
  a skill that is not detected is "not found in the resume", not "missing".
* Contact details (e-mail, phone, address) are deliberately *not* extracted;
  matching does not need them.
* Every structured value can be corrected by the user before matching.
* Resume text is untrusted input; it is parsed, never executed or obeyed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from app.core.logging import redact
from app.ml.skill_extractor import SkillMatch, clean_evidence, extract_skills

# --------------------------------------------------------------------------
# Section detection
# --------------------------------------------------------------------------

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": (
        "summary", "professional summary", "profile", "professional profile", "about me", "about",
        "objective", "career objective", "objectives", "career summary", "personal statement",
    ),
    "skills": (
        "skills", "technical skills", "core skills", "key skills", "core competencies", "competencies",
        "tools", "technologies", "tech stack", "skills and tools", "tools and technologies",
        "skills and technologies", "technical proficiencies", "skills summary", "hard skills", "soft skills",
        "programming languages", "languages and tools",
    ),
    "education": (
        "education", "academic background", "educational background", "academic qualifications",
        "educational attainment", "education and training",
    ),
    "experience": (
        "experience", "work experience", "professional experience", "employment history", "work history",
        "relevant experience", "employment", "career history", "professional background",
    ),
    "internships": (
        "internship", "internships", "internship experience", "ojt", "on-the-job training",
        "on the job training", "practicum", "work immersion",
    ),
    "projects": (
        "projects", "academic projects", "personal projects", "selected projects", "capstone project",
        "capstone projects", "project experience", "portfolio", "relevant projects", "thesis",
    ),
    "certifications": (
        "certifications", "certificates", "certification", "licenses", "licenses and certifications",
        "licenses & certifications", "certifications and trainings", "trainings", "training",
        "trainings and seminars", "seminars and trainings", "seminars attended", "courses",
    ),
    "achievements": (
        "achievements", "awards", "honors", "awards and honors", "honors and awards", "accomplishments",
        "awards and achievements", "recognition",
    ),
    "other": (
        "references", "character references", "interests", "hobbies", "languages", "contact",
        "contact information", "personal information", "personal details", "activities",
        "extracurricular activities", "affiliations", "organizations", "leadership", "volunteer experience",
        "volunteering",
    ),
}

_HEADING_LOOKUP = {alias: section for section, aliases in SECTION_ALIASES.items() for alias in aliases}
_INLINE_SKILLS = re.compile(r"^\s*(?:technical\s+|core\s+|key\s+)?(?:skills|tools|technologies|tech stack)\s*[:\-–]\s*\S", re.I)
_BULLET = re.compile(r"^\s*(?:[•●▪◦‣⁃∙·*➢➤►✓✔\-–—]|\d{1,2}[.)])\s+")


def _heading_key(line: str) -> str:
    key = line.strip().strip(":").strip()
    key = re.sub(r"[^\w&/ -]", "", key).lower().replace("&", "and")
    return " ".join(key.split())


def detect_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or len(stripped) > 45:
        return None
    return _HEADING_LOOKUP.get(_heading_key(stripped))


def split_sections(lines: list[str]) -> dict[str, list[int]]:
    """Map section name -> line indices (excluding the heading line itself)."""
    sections: dict[str, list[int]] = {"header": []}
    current = "header"
    for idx, line in enumerate(lines):
        heading = detect_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(idx)
    return sections


def is_bullet(line: str) -> bool:
    return bool(_BULLET.match(line)) or len(line) > 95


def strip_bullet(line: str) -> str:
    return _BULLET.sub("", line).strip()


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE_RE = rf"(?:{_MONTH_RE}\.?\s*,?\s*(?:19|20)\d{{2}}|\d{{1,2}}/(?:19|20)\d{{2}}|(?:19|20)\d{{2}})"
_RANGE = re.compile(
    rf"(?P<start>{_DATE_RE})\s*(?:-|–|—|to|until)\s*(?P<end>{_DATE_RE}|present|current|now|ongoing|to date)",
    re.I,
)
_SINGLE_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


@dataclass(frozen=True)
class ParsedDate:
    year: int
    month: int | None

    def label(self) -> str:
        return f"{self.year}-{self.month:02d}" if self.month else str(self.year)


def parse_date(text: str, today: date | None = None) -> ParsedDate | None:
    text = text.strip().lower().rstrip(".")
    today = today or date.today()
    if text in {"present", "current", "now", "ongoing", "to date"}:
        return ParsedDate(today.year, today.month)
    m = re.match(r"(\d{1,2})/((?:19|20)\d{2})", text)
    if m:
        month = int(m.group(1))
        return ParsedDate(int(m.group(2)), month if 1 <= month <= 12 else None)
    year_match = _SINGLE_YEAR.search(text)
    if not year_match:
        return None
    month = None
    month_match = re.match(r"([a-z]+)", text)
    if month_match:
        month = _MONTHS.get(month_match.group(1)[:3])
    return ParsedDate(int(year_match.group(1)), month)


def months_between(start: ParsedDate, end: ParsedDate) -> int | None:
    """Duration in months, only when both ends have a month (clearly supported)."""
    if start.month is None or end.month is None:
        return None
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return months if 0 < months <= 600 else None


# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------


@dataclass
class EducationItem:
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass
class ExperienceItem:
    title: str | None = None
    organization: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration_months: int | None = None
    is_internship: bool = False
    description: str | None = None
    _start: ParsedDate | None = None
    _end: ParsedDate | None = None


@dataclass
class ProjectItem:
    name: str
    description: str | None = None
    skills: list[str] = field(default_factory=list)


@dataclass
class ExtractedProfile:
    skills: list[SkillMatch]
    education: list[EducationItem]
    experience: list[ExperienceItem]
    projects: list[ProjectItem]
    certifications: list[str]
    achievements: list[str]
    summary: str | None
    total_experience_months: int | None
    detected_preferences: dict
    sections_found: list[str]
    warnings: list[str]


# --------------------------------------------------------------------------
# Block parsing helpers
# --------------------------------------------------------------------------

_ROLE_WORDS = re.compile(
    r"\b(intern|internship|trainee|engineer|developer|programmer|analyst|assistant|manager|specialist|associate|"
    r"officer|designer|consultant|representative|agent|coordinator|lead|head|staff|clerk|scientist|technician|"
    r"administrator|supervisor|tutor|teacher|instructor|volunteer|writer|researcher|architect|accountant|"
    r"bookkeeper|encoder|cashier|advisor|executive|director|president|member|ojt|fellow|apprentice)\b",
    re.I,
)
_SEPARATORS = re.compile(r"\s*(?:\||•|·|—|–|\s-\s|,|\bat\b|@)\s*", re.I)


def _blocks(lines: list[str], indices: list[int]) -> list[list[str]]:
    """Group a section's lines into entries."""
    blocks: list[list[str]] = []
    current: list[str] = []
    current_has_date = False
    prev_bullet = False
    for idx in indices:
        line = lines[idx]
        if not line.strip():
            if current:
                blocks.append(current)
            current, current_has_date, prev_bullet = [], False, False
            continue
        bullet = is_bullet(line)
        has_date = bool(_RANGE.search(line))
        starts_new = current and (
            (not bullet and prev_bullet) or (has_date and current_has_date and not bullet)
        )
        if starts_new:
            blocks.append(current)
            current, current_has_date = [], False
        current.append(line)
        current_has_date = current_has_date or has_date
        prev_bullet = bullet
    if current:
        blocks.append(current)
    return blocks


def _split_header(lines: list[str]) -> tuple[list[str], list[str]]:
    header: list[str] = []
    body: list[str] = []
    for line in lines:
        if not body and not is_bullet(line) and len(header) < 3:
            header.append(line)
        else:
            body.append(line)
    return header, body


def _clean_part(part: str) -> str:
    return part.strip(" ,|-–—:()").strip()


# --------------------------------------------------------------------------
# Section parsers
# --------------------------------------------------------------------------


def parse_experience(lines: list[str], indices: list[int], internship_section: bool, today: date) -> list[ExperienceItem]:
    items: list[ExperienceItem] = []
    for block in _blocks(lines, indices):
        header, body = _split_header(block)
        item = ExperienceItem(is_internship=internship_section)
        parts: list[str] = []
        for line in header:
            m = _RANGE.search(line)
            if m and item._start is None:
                start = parse_date(m.group("start"), today)
                end = parse_date(m.group("end"), today)
                if start and end:
                    item._start, item._end = start, end
                    item.start_date = start.label()
                    item.end_date = "present" if m.group("end").lower() in {
                        "present", "current", "now", "ongoing", "to date"
                    } else end.label()
                    item.duration_months = months_between(start, end)
                line = line[: m.start()] + " " + line[m.end():]
            parts.extend(p for p in (_clean_part(x) for x in _SEPARATORS.split(line)) if p)
        if not parts and not body:
            continue
        title_idx = next((i for i, p in enumerate(parts) if _ROLE_WORDS.search(p)), 0 if parts else None)
        if title_idx is not None and parts:
            item.title = parts[title_idx][:200]
            others = [p for i, p in enumerate(parts) if i != title_idx]
            if others:
                item.organization = others[0][:200]
        if item.title and re.search(r"\b(intern|internship|ojt|trainee|practicum)\b", item.title, re.I):
            item.is_internship = True
        description = "\n".join(strip_bullet(b) for b in body).strip()
        item.description = redact(description)[:3000] or None
        if item.title or item.organization or item.start_date:
            items.append(item)
    return items


_DEGREE = re.compile(
    r"\b(bachelor(?:'s)?(?:\s+of\s+[a-z]+)?|master(?:'s)?(?:\s+of\s+[a-z]+)?|doctor(?:ate)?(?:\s+of\s+[a-z]+)?|"
    r"ph\.?\s?d\.?|mba|b\.?\s?s\.?c?\.?|b\.?\s?a\.?|m\.?\s?s\.?c?\.?|associate(?:'s)?(?:\s+degree)?|diploma|"
    r"senior high school|junior high school|high school|bs[a-z]{1,5}|ab\s)",
    re.I,
)
_PH_DEGREE_ABBR = {
    "bsit": "Information Technology", "bscs": "Computer Science", "bsis": "Information Systems",
    "bscpe": "Computer Engineering", "bsece": "Electronics Engineering", "bsee": "Electrical Engineering",
    "bsce": "Civil Engineering", "bsme": "Mechanical Engineering", "bsie": "Industrial Engineering",
    "bsa": "Accountancy", "bsba": "Business Administration", "bsn": "Nursing", "bspsych": "Psychology",
    "bshm": "Hospitality Management", "bstm": "Tourism Management", "bsed": "Secondary Education",
    "beed": "Elementary Education", "bsemc": "Entertainment and Multimedia Computing",
    "bsma": "Management Accounting", "bsstat": "Statistics", "bsmath": "Mathematics",
}
_INSTITUTION = re.compile(r"\b(university|college|institute|school|academy|polytechnic|universidad|colegio)\b", re.I)


def parse_education(lines: list[str], indices: list[int], today: date) -> list[EducationItem]:
    items: list[EducationItem] = []
    for block in _blocks(lines, indices):
        item = EducationItem()
        years: list[str] = []
        for raw in block[:5]:
            line = strip_bullet(raw)
            m = _RANGE.search(line)
            if m:
                start, end = parse_date(m.group("start"), today), parse_date(m.group("end"), today)
                item.start_date = start.label() if start else None
                item.end_date = "present" if m.group("end").lower() in {"present", "current", "now", "ongoing"} else (
                    end.label() if end else None
                )
            else:
                years.extend(_SINGLE_YEAR.findall(line))
            if item.degree is None:
                dm = _DEGREE.search(line)
                if dm:
                    segment = _clean_part(_SEPARATORS.split(line[dm.start():])[0])
                    segment = _RANGE.sub("", segment).strip()
                    item.degree = segment[:200] or dm.group(0)
                    fm = re.search(r"\b(?:in|of)\s+([A-Z][A-Za-z&/ ]{2,80})", segment)
                    abbr = re.match(r"(bs[a-z]{1,5})\b", segment, re.I)
                    if fm and not re.match(r"(science|arts)\b", fm.group(1), re.I):
                        item.field_of_study = fm.group(1).strip()
                    elif abbr and abbr.group(1).lower() in _PH_DEGREE_ABBR:
                        item.field_of_study = _PH_DEGREE_ABBR[abbr.group(1).lower()]
                    elif fm:
                        inner = re.search(r"\b(?:science|arts)\s+in\s+([A-Za-z][A-Za-z&/ ]{2,80})", segment, re.I)
                        item.field_of_study = inner.group(1).strip() if inner else None
            if item.institution is None and _INSTITUTION.search(line):
                parts = [_clean_part(p) for p in _SEPARATORS.split(_RANGE.sub("", line))]
                inst = next((p for p in parts if _INSTITUTION.search(p)), None)
                item.institution = inst[:200] if inst else None
        if item.end_date is None and years:
            item.end_date = years[-1]
            if len(years) > 1:
                item.start_date = years[0]
        expected = any(re.search(r"\bexpected\b|\bcandidate\b|\bongoing\b", line, re.I) for line in block)
        if expected and item.end_date and item.end_date != "present":
            item.end_date = f"{item.end_date} (expected)"
        if item.degree or item.institution:
            items.append(item)
    return items


def parse_projects(lines: list[str], indices: list[int]) -> list[ProjectItem]:
    items: list[ProjectItem] = []
    for block in _blocks(lines, indices):
        header, body = _split_header(block)
        if not header:
            header, body = [block[0]], block[1:]
        first = strip_bullet(_RANGE.sub("", header[0]))
        pieces = re.split(r"\s[–—|-]\s|:\s", first, maxsplit=1)
        name = _clean_part(pieces[0])[:200]
        rest = pieces[1] if len(pieces) > 1 else ""
        if not name:
            continue
        description_lines = ([rest.strip()] if rest.strip() else []) + [strip_bullet(x) for x in header[1:] + body]
        description = redact("\n".join(d for d in description_lines if d))[:3000] or None
        skills = [m.name for m in extract_skills(block)]
        items.append(ProjectItem(name=name, description=description, skills=skills))
    return items


def parse_list_section(lines: list[str], indices: list[int], limit: int = 20) -> list[str]:
    out: list[str] = []
    for idx in indices:
        text = strip_bullet(lines[idx])
        if not text or len(text) < 3:
            continue
        out.append(clean_evidence(text, 200))
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------
# Preferences detected from the summary/objective only
# --------------------------------------------------------------------------

PH_LOCATIONS = (
    "Metro Manila", "Manila", "Makati", "Taguig", "BGC", "Bonifacio Global City", "Pasig", "Quezon City",
    "Mandaluyong", "Pasay", "Parañaque", "Paranaque", "Muntinlupa", "Alabang", "Ortigas", "Caloocan", "Marikina",
    "Cebu", "Cebu City", "Mandaue", "Davao", "Davao City", "Iloilo", "Iloilo City", "Bacolod", "Baguio",
    "Cagayan de Oro", "Laguna", "Santa Rosa", "Cavite", "Batangas", "Lipa", "Pampanga", "Clark", "Angeles",
    "Bulacan", "Rizal", "Calapan", "Oriental Mindoro", "Mindoro", "Naga", "Legazpi", "Tacloban", "Zamboanga",
    "General Santos", "Dumaguete", "Puerto Princesa", "Palawan", "Philippines",
)


def detect_preferences(summary_text: str) -> dict:
    prefs: dict = {}
    text = summary_text.lower()
    if not text:
        return prefs
    employment = []
    if re.search(r"\b(internship|intern|ojt|on-the-job training|practicum)\b", text):
        employment.append("internship")
    if re.search(r"\bpart[- ]time\b", text):
        employment.append("part_time")
    if re.search(r"\bfull[- ]time\b", text):
        employment.append("full_time")
    if employment:
        prefs["employment_types"] = employment
    arrangements = []
    if re.search(r"\b(remote|work from home|wfh|home-based|home based)\b", text):
        arrangements.append("remote")
    if re.search(r"\bhybrid\b", text):
        arrangements.append("hybrid")
    if re.search(r"\b(on-site|onsite|on site|office-based|office based)\b", text):
        arrangements.append("onsite")
    if arrangements:
        prefs["work_arrangements"] = arrangements
    locations: list[str] = []
    for loc in sorted(PH_LOCATIONS, key=len, reverse=True):
        if re.search(rf"(?<!\w){re.escape(loc.lower())}(?!\w)", text) and not any(
            loc.lower() in found.lower() for found in locations
        ):
            locations.append(loc)
    if locations:
        prefs["locations"] = locations[:5]
    titles = re.findall(
        r"(?:seeking|looking for|pursuing|aiming for|applying for)\s+(?:an?\s+)?(?:entry[- ]level\s+|junior\s+)?"
        r"((?:[a-z/&+]+\s+){1,4}?)(?:intern(?:ship)?|position|role|job|opportunit|career)\b",
        text,
    )
    generic = {"challenging", "rewarding", "new", "full-time", "part-time", "remote", "an", "a", "the"}
    cleaned = []
    for title in titles:
        words = [w for w in title.split() if w not in generic]
        if words:
            cleaned.append(" ".join(words).title())
    if cleaned:
        prefs["titles"] = cleaned[:3]
    return prefs


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def _merge_intervals_months(items: list[ExperienceItem]) -> int | None:
    intervals = []
    for item in items:
        if item._start and item._end and item.duration_months:
            start = item._start.year * 12 + (item._start.month or 1) - 1
            end = item._end.year * 12 + (item._end.month or 12) - 1
            if end >= start:
                intervals.append((start, end))
    if not intervals:
        return None
    intervals.sort()
    total = 0
    cur_start, cur_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= cur_end + 1:
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start + 1
            cur_start, cur_end = start, end
    total += cur_end - cur_start + 1
    return total


def extract_profile(text: str, today: date | None = None) -> ExtractedProfile:
    today = today or date.today()
    lines = text.split("\n")
    sections = split_sections(lines)
    warnings: list[str] = []

    skill_context = set(sections.get("skills", []))
    skill_context |= {i for i, line in enumerate(lines) if _INLINE_SKILLS.match(line)}
    skills = extract_skills(lines, skill_context)

    education = parse_education(lines, sections.get("education", []), today)
    experience = parse_experience(lines, sections.get("experience", []), False, today)
    experience += parse_experience(lines, sections.get("internships", []), True, today)
    projects = parse_projects(lines, sections.get("projects", []))
    certifications = parse_list_section(lines, sections.get("certifications", []))
    achievements = parse_list_section(lines, sections.get("achievements", []))

    summary_lines = [strip_bullet(lines[i]) for i in sections.get("summary", []) if lines[i].strip()]
    summary = redact(" ".join(summary_lines))[:1000] or None
    prefs = detect_preferences(summary or "")

    found = [s for s, idx in sections.items() if idx and s not in {"header", "other"}]
    if "skills" not in found:
        warnings.append("No dedicated skills section was found; skills were detected from the full text.")
    if not education:
        warnings.append("No education entries were recognised. Please add them manually if relevant.")
    if not experience and not projects:
        warnings.append("No experience or project entries were recognised. Please review and add them manually.")
    if any(e.duration_months is None and e.start_date for e in experience):
        warnings.append("Some experience durations could not be calculated because exact months were not given.")

    return ExtractedProfile(
        skills=skills,
        education=education,
        experience=experience,
        projects=projects,
        certifications=certifications,
        achievements=achievements,
        summary=summary,
        total_experience_months=_merge_intervals_months(experience),
        detected_preferences=prefs,
        sections_found=found,
        warnings=warnings,
    )
