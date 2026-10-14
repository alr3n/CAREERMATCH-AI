"""Parse job descriptions into structured, evidence-backed fields.

Job descriptions are untrusted text from third parties. They are converted
to plain text, split into sections by their headings, and then:

* skills under "Requirements / Qualifications / What you'll need" headings
  are tagged ``required``;
* skills under "Nice to have / Preferred / Bonus" headings, or on lines that
  say "preferred", "a plus", "bonus", are tagged ``preferred``;
* skills elsewhere (responsibilities, company blurb) are ``mentioned``.

Nothing is invented: salary, posting date and deadline come only from
provider fields; experience level and employment type are classified from
the title/structured fields/explicit phrases and fall back to ``unknown``.
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from app.ml.skill_extractor import clean_evidence, extract_skills

# --------------------------------------------------------------------------
# HTML → lines
# --------------------------------------------------------------------------

_BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "table"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[tuple[str, bool]] = []  # (text, is_heading)
        self._buf: list[str] = []
        self._heading_depth = 0
        self._strong_only = True
        self._in_strong = 0
        self._in_li = False
        self._skip = 0

    def _flush(self) -> None:
        text = " ".join("".join(self._buf).split())
        if text:
            is_heading = self._heading_depth > 0 or (self._strong_only and self._had_strong and len(text) < 80)
            prefix = "• " if self._in_li and not is_heading else ""
            self.lines.append((prefix + text, is_heading))
        self._buf = []
        self._strong_only = True
        self._had_strong = False

    _had_strong = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
            return
        if tag in _BLOCK_TAGS:
            self._flush()
        if tag in _HEADING_TAGS:
            self._heading_depth += 1
        if tag in {"strong", "b"}:
            self._in_strong += 1
            self._had_strong = True
        if tag == "li":
            self._in_li = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip = max(0, self._skip - 1)
            return
        if tag in _BLOCK_TAGS:
            self._flush()
        if tag in _HEADING_TAGS:
            self._heading_depth = max(0, self._heading_depth - 1)
        if tag in {"strong", "b"}:
            self._in_strong = max(0, self._in_strong - 1)
        if tag == "li":
            self._in_li = False

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if data.strip() and not self._in_strong and self._heading_depth == 0:
            self._strong_only = False
        self._buf.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def html_to_lines(content: str) -> list[tuple[str, bool]]:
    """Return ``(line, is_heading)`` pairs. Accepts HTML or HTML-escaped HTML."""
    if not content:
        return []
    if "&lt;" in content and "<" not in content:
        content = html.unescape(content)  # Greenhouse returns escaped HTML
    parser = _TextExtractor()
    parser.feed(content)
    parser.close()
    return parser.lines


def text_to_lines(text: str) -> list[tuple[str, bool]]:
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading = len(line) < 60 and (line.endswith(":") or (line.isupper() and len(line.split()) <= 6))
        out.append((line, heading))
    return out


# --------------------------------------------------------------------------
# Section classification
# --------------------------------------------------------------------------

_REQUIRED_HEADING = re.compile(
    r"(requirement|qualification|what you('|’)?ll need|what we('|’)?re looking for|who you are|must[- ]have|"
    r"you (should )?have|skills (and|&) experience|experience (and|&) skills|what you bring|you bring|"
    r"about you|minimum|basic qualifications|required|competenc|eligibility|ideal candidate)",
    re.I,
)
_PREFERRED_HEADING = re.compile(
    r"(nice[- ]to[- ]have|preferred|bonus|plus|desired|desirable|good to have|extra credit|advantage|"
    r"would be great|pluses)",
    re.I,
)
_RESPONSIBILITY_HEADING = re.compile(
    r"(responsibilit|what you('|’)?ll do|the role|your role|duties|day[- ]to[- ]day|about the (job|role|team)|"
    r"what we offer|benefits|perks|about us|who we are|our company|why join)",
    re.I,
)
_PREFERRED_LINE = re.compile(
    r"\b(preferred|is a plus|are a plus|a plus|nice to have|bonus|advantage|advantageous|desirable|ideally|"
    r"good to have|optional)\b",
    re.I,
)


def classify_heading(heading: str) -> str:
    if _PREFERRED_HEADING.search(heading):
        return "preferred"
    if _REQUIRED_HEADING.search(heading):
        return "required"
    if _RESPONSIBILITY_HEADING.search(heading):
        return "other"
    return "other"


# --------------------------------------------------------------------------
# Classification of level, type, arrangement and category
# --------------------------------------------------------------------------

_INTERN = re.compile(r"\b(intern|internship|ojt|on[- ]the[- ]job training|trainee|apprentice|practicum|co-?op)\b", re.I)
_ENTRY = re.compile(r"\b(junior|jr\.?|entry[- ]level|graduate|new grad|associate|fresh grad|fresher|level i)\b", re.I)
_SENIOR = re.compile(r"\b(senior|sr\.?|lead|principal|staff|head of|director|manager|vp|chief|architect)\b", re.I)
_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years?|yrs?)(?:'|’)?\s+(?:of\s+)?(?:\w+\s+){0,4}?experience", re.I)


def classify_experience_level(title: str, text: str) -> tuple[str, int | None]:
    years = [int(m.group(1)) for m in _YEARS.finditer(text) if int(m.group(1)) <= 20]
    min_years = min(years) if years else None
    if _INTERN.search(title):
        return "internship", min_years
    if _SENIOR.search(title):
        return "senior", min_years
    if _ENTRY.search(title):
        return "entry", min_years
    if min_years is not None:
        if min_years <= 1:
            return "entry", min_years
        if min_years <= 4:
            return "mid", min_years
        return "senior", min_years
    if re.search(r"\b(no experience required|fresh graduates? (are )?welcome)\b", text, re.I):
        return "entry", 0
    return "unknown", None


_COMMITMENT_MAP = (
    (re.compile(r"intern", re.I), "internship"),
    (re.compile(r"part[- ]?time", re.I), "part_time"),
    (re.compile(r"full[- ]?time|permanent|regular", re.I), "full_time"),
    (re.compile(r"contract|freelance|consultant|project[- ]based", re.I), "contract"),
    (re.compile(r"temporary|temp\b|seasonal|fixed[- ]term", re.I), "temporary"),
)


def classify_employment_type(commitment: str | None, title: str, text: str) -> str:
    for source in (commitment or "", title):
        for pattern, value in _COMMITMENT_MAP:
            if source and pattern.search(source):
                return value
    for pattern, value in _COMMITMENT_MAP[1:]:
        if re.search(rf"\b(this is an?|this|employment type:?|job type:?)\s+({pattern.pattern})", text, re.I):
            return value
    return "unknown"


def classify_work_arrangement(workplace_type: str | None, location: str | None, text: str) -> str:
    wt = (workplace_type or "").lower()
    if wt in {"remote", "hybrid"}:
        return wt
    if wt in {"on-site", "onsite"}:
        return "onsite"
    loc = (location or "").lower()
    if "hybrid" in loc:
        return "hybrid"
    if re.search(r"\bremote\b|work from home|wfh|anywhere", loc):
        return "remote"
    if re.search(r"\b(fully remote|100% remote|remote[- ]first|work from home|remote position|remote role)\b", text, re.I):
        return "remote"
    if re.search(r"\bhybrid (work|set-?up|arrangement|role|schedule)\b", text, re.I):
        return "hybrid"
    if re.search(r"\b(on-?site|office-based|onsite work|report to (the|our) office)\b", text, re.I):
        return "onsite"
    return "unknown"


_CATEGORIES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Data & Analytics", re.compile(r"\b(data|analytics|analyst|bi\b|business intelligence|machine learning|ml\b|ai\b|scientist|statistic)", re.I)),
    ("Software Engineering", re.compile(r"\b(software|developer|engineer|programmer|frontend|front-end|backend|back-end|full[- ]?stack|devops|sre|mobile|ios|android|web|qa|tester|quality assurance)\b", re.I)),
    ("Design", re.compile(r"\b(design|designer|ux|ui|graphic|creative|illustrat|video|multimedia)\b", re.I)),
    ("IT & Infrastructure", re.compile(r"\b(it support|helpdesk|help desk|technical support|system administrator|sysadmin|network|infrastructure|security|cyber)\b", re.I)),
    ("Product & Project Management", re.compile(r"\b(product manager|product owner|project manager|program manager|scrum master|project coordinator)\b", re.I)),
    ("Marketing & Content", re.compile(r"\b(marketing|seo|content|social media|copywriter|brand|communications|growth)\b", re.I)),
    ("Sales & Business Development", re.compile(r"\b(sales|account executive|business development|account manager|partnerships)\b", re.I)),
    ("Customer Support", re.compile(r"\b(customer|support|service|call center|call centre|csr|client success|customer success)\b", re.I)),
    ("Finance & Accounting", re.compile(r"\b(finance|financial|accountant|accounting|bookkeep|audit|tax|payroll|treasury)\b", re.I)),
    ("Human Resources", re.compile(r"\b(hr\b|human resources|recruit|talent|people operations|people partner)\b", re.I)),
    ("Operations & Administration", re.compile(r"\b(operations|admin|administrative|assistant|coordinator|office|logistics|supply chain)\b", re.I)),
)


def classify_category(title: str, department: str | None = None) -> str:
    for source in (title, department or ""):
        for name, pattern in _CATEGORIES:
            if source and pattern.search(source):
                return name
    return "Other"


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


@dataclass
class ParsedSkill:
    skill: str
    category: str
    requirement: str  # required | preferred | mentioned
    evidence: str


@dataclass
class ParsedJob:
    description: str
    required_qualifications: list[str] = field(default_factory=list)
    preferred_qualifications: list[str] = field(default_factory=list)
    skills: list[ParsedSkill] = field(default_factory=list)


_RANK = {"required": 3, "preferred": 2, "mentioned": 1}


def parse_description(
    lines: list[tuple[str, bool]],
    extra_sections: list[tuple[str, list[str]]] | None = None,
) -> ParsedJob:
    """``extra_sections`` carries structured lists (e.g. Lever ``lists``)."""
    tagged: list[tuple[str, str]] = []  # (line, section kind)
    current = "other"
    for text, is_heading in lines:
        if is_heading:
            current = classify_heading(text)
            tagged.append((text, "heading"))
            continue
        tagged.append((text, current))
    for heading, items in extra_sections or []:
        kind = classify_heading(heading)
        tagged.append((heading, "heading"))
        tagged.extend((item, kind) for item in items)

    description_lines = [t for t, _ in tagged]
    required_q: list[str] = []
    preferred_q: list[str] = []
    skills: dict[str, ParsedSkill] = {}
    for text, kind in tagged:
        if kind == "heading":
            continue
        clean = text.lstrip("•-* ").strip()
        level = kind
        if kind in {"required", "other"} and _PREFERRED_LINE.search(clean):
            level = "preferred"
        elif kind == "other":
            level = "mentioned"
        if kind == "required" and level == "required" and clean:
            required_q.append(clean_evidence(clean, 300))
        elif level == "preferred" and kind != "other" and clean:
            preferred_q.append(clean_evidence(clean, 300))
        for match in extract_skills([clean]):
            existing = skills.get(match.name)
            if existing is None or _RANK[level] > _RANK[existing.requirement]:
                skills[match.name] = ParsedSkill(match.name, match.category, level, clean_evidence(clean, 300))
    return ParsedJob(
        description="\n".join(description_lines)[:20000],
        required_qualifications=required_q[:40],
        preferred_qualifications=preferred_q[:40],
        skills=sorted(skills.values(), key=lambda s: (-_RANK[s.requirement], s.skill.lower())),
    )


def fingerprint(company: str, title: str, location: str | None, description: str) -> str:
    def norm(s: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

    basis = "|".join([norm(company), norm(title), norm(location), norm(description)[:2000]])
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()
