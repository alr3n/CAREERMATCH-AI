from tests.factories import make_pdf, resume_text


def test_profile_defaults_and_update(client, auth_headers):
    body = client.get("/api/v1/profile", headers=auth_headers).json()
    assert body["completeness"] == 0
    assert body["has_resume"] is False
    assert body["profile"]["min_salary"] is None  # salary is optional

    response = client.patch(
        "/api/v1/profile",
        headers=auth_headers,
        json={
            "career_stage": "student",
            "goal": "internship",
            "preferred_titles": ["Data Analyst", "data analyst", " BI Intern "],
            "work_arrangements": ["remote", "hybrid"],
            "employment_types": ["internship"],
            "preferred_locations": ["Makati"],
        },
    )
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["preferred_titles"] == ["Data Analyst", "BI Intern"]
    assert response.json()["completeness"] == 50


def test_invalid_enum_rejected(client, auth_headers):
    response = client.patch("/api/v1/profile", headers=auth_headers, json={"work_arrangements": ["moon"]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_negative_salary_rejected(client, auth_headers):
    assert client.patch("/api/v1/profile", headers=auth_headers, json={"min_salary": -5}).status_code == 422


def test_delete_account_removes_everything(client, auth_headers, db):
    from sqlalchemy import func, select

    from app.models import ExtractedSkill, Resume, User

    client.post("/api/v1/resumes/upload", headers=auth_headers,
                files={"file": ("cv.pdf", make_pdf(resume_text()), "application/pdf")})
    assert db.scalar(select(func.count(ExtractedSkill.id))) > 0
    assert client.delete("/api/v1/profile", headers=auth_headers).status_code == 204
    db.expire_all()
    assert db.scalar(select(func.count(User.id))) == 0
    assert db.scalar(select(func.count(Resume.id))) == 0
    assert db.scalar(select(func.count(ExtractedSkill.id))) == 0
    # The token no longer works.
    assert client.get("/api/v1/profile", headers=auth_headers).status_code == 401
