from datetime import date

from app.ml.profile_extractor import detect_heading, extract_profile, months_between, parse_date
from app.ml.skill_extractor import extract_skills, looks_like_list
from app.ml.taxonomy import canonicalize, related_skills


def names(lines, context=None):
    return {m.name for m in extract_skills(lines, context)}


def test_ambiguous_words_are_not_skills_in_prose():
    prose = [
        "I react quickly to customer issues and excel in a fast-paced team.",
        "We go to the office and rest on weekends.",
    ]
    assert names(prose) == set()


def test_strict_skills_only_in_list_context():
    assert "Go" not in names(["Go to the main menu"])
    assert {"Go", "R", "C"} <= names(["Languages: Go, R, C, Python"])


def test_case_sensitive_product_names():
    assert "React" in names(["Built a dashboard with React and TypeScript"])
    assert "Microsoft Excel" in names(["Advanced Excel (pivot tables)"])


def test_java_is_not_javascript():
    assert names(["JavaScript developer"]) == {"JavaScript"}


def test_aliases_map_to_canonical_names():
    assert canonicalize("postgres") == "PostgreSQL"
    assert canonicalize("powerbi") == "Power BI"
    assert canonicalize("My Custom Skill") == "My Custom Skill"


def test_related_skills_are_symmetric():
    assert "MySQL" in related_skills("PostgreSQL")
    assert "PostgreSQL" in related_skills("MySQL")
    assert "PostgreSQL" not in related_skills("PostgreSQL")


def test_list_detection():
    assert looks_like_list("Python, SQL, Docker, Git")
    assert not looks_like_list("I built a tool, which helped my team, a lot.")


def test_heading_detection():
    assert detect_heading("WORK EXPERIENCE") == "experience"
    assert detect_heading("Licenses & Certifications:") == "certifications"
    assert detect_heading("I have a lot of work experience in many fields") is None


def test_date_parsing_and_duration():
    today = date(2026, 10, 1)
    assert parse_date("Sept 2023", today).month == 9
    assert parse_date("Present", today).year == 2026
    assert months_between(parse_date("Jun 2024", today), parse_date("Aug 2024", today)) == 3
    # Year-only ranges are not "clearly supported" durations.
    assert months_between(parse_date("2022", today), parse_date("2024", today)) is None


def test_no_qualifications_invented_from_missing_sections():
    profile = extract_profile("Skills\nPython, SQL, Excel\n\nEager learner who enjoys data work and teamwork.")
    assert profile.experience == [] and profile.education == []
    assert profile.total_experience_months is None


def test_ph_degree_abbreviation():
    text = "EDUCATION\nBSIT, Test State University\n2021 - 2025\n\nSKILLS\nJava, MySQL, Linux"
    profile = extract_profile(text, date(2026, 1, 1))
    assert profile.education[0].field_of_study == "Information Technology"
