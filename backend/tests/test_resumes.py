import pytest

from app.core.config import get_settings
from tests.conftest import register
from tests.factories import make_docx, make_image_only_pdf, make_pdf, resume_text

URL = "/api/v1/resumes/upload"


def _upload(client, headers, name, data, mime="application/octet-stream"):
    return client.post(URL, headers=headers, files={"file": (name, data, mime)})


def test_valid_pdf_extracts_structured_profile(uploaded_resume):
    skills = {s["skill"] for s in uploaded_resume["skills"]}
    assert {"Python", "SQL", "Pandas", "Tableau"} <= skills
    assert uploaded_resume["content_type"] == "pdf"
    assert uploaded_resume["education"][0]["field_of_study"] == "Computer Science"
    titles = [e["title"] for e in uploaded_resume["experience"]]
    assert "Data Analyst Intern" in titles
    intern = next(e for e in uploaded_resume["experience"] if e["title"] == "Data Analyst Intern")
    assert intern["is_internship"] is True and intern["duration_months"] == 3
    assert uploaded_resume["detected_preferences"]["employment_types"] == ["internship"]
    # Contact details are never stored and raw text is not kept without consent.
    assert uploaded_resume["raw_text_stored"] is False
    assert "example.com" not in str(uploaded_resume)


def test_valid_docx(client, auth_headers):
    response = _upload(client, auth_headers, "cv.docx", make_docx(resume_text()))
    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "docx"
    assert "Python" in {s["skill"] for s in body["skills"]}


def test_empty_file(client, auth_headers):
    response = _upload(client, auth_headers, "empty.pdf", b"")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_file"


def test_unsupported_type(client, auth_headers):
    response = _upload(client, auth_headers, "notes.txt", b"hello world")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_type"


def test_extension_mismatch(client, auth_headers):
    response = _upload(client, auth_headers, "fake.pdf", make_docx(resume_text()))
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "type_mismatch"


def test_malformed_pdf(client, auth_headers):
    response = _upload(client, auth_headers, "broken.pdf", b"%PDF-1.7\n this is not really a pdf")
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"malformed", "no_text"}


def test_malformed_docx(client, auth_headers):
    response = _upload(client, auth_headers, "broken.docx", b"PK\x03\x04garbage-bytes")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "malformed"


def test_scanned_pdf_explains_ocr_limitation(client, auth_headers):
    response = _upload(client, auth_headers, "scan.pdf", make_image_only_pdf())
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "no_text"
    assert "OCR" in body["message"]


def test_oversized_upload(client, auth_headers):
    big = b"%PDF-" + b"0" * (get_settings().max_upload_bytes + 10)
    response = _upload(client, auth_headers, "big.pdf", big)
    assert response.status_code == 413


def test_unsafe_filename_is_sanitised(client, auth_headers):
    response = _upload(client, auth_headers, "../../etc/pass<wd>.pdf", make_pdf(resume_text()))
    assert response.status_code == 201
    name = response.json()["original_filename"]
    assert "/" not in name and ".." not in name and "<" not in name


def test_upload_requires_auth(client):
    assert _upload(client, {}, "cv.pdf", make_pdf(resume_text())).status_code == 401


def test_user_can_correct_wrong_extraction(client, auth_headers, uploaded_resume):
    rid = uploaded_resume["id"]
    response = client.patch(
        f"/api/v1/resumes/{rid}/profile",
        headers=auth_headers,
        json={
            "skills": [{"skill": "python"}, {"skill": "SQL"}, {"skill": "power bi"}, {"skill": "Dashboard Storytelling"}],
            "education": [{"institution": "Test University", "degree": "BS Statistics", "field_of_study": "Statistics"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    skills = {s["skill"]: s for s in body["skills"]}
    assert set(skills) == {"Python", "SQL", "Power BI", "Dashboard Storytelling"}
    assert skills["Power BI"]["source"] == "user"
    assert skills["Python"]["source"] == "extracted"  # evidence preserved for kept skills
    assert body["education"][0]["field_of_study"] == "Statistics"
    assert body["status"] == "reviewed"
    # Other sections untouched
    assert body["experience"] == uploaded_resume["experience"]


def test_missing_optional_fields_are_allowed(client, auth_headers):
    minimal = "Skills\nPython, SQL, Excel\n\nI enjoy solving problems with data and building small tools for my classmates."
    response = _upload(client, auth_headers, "min.docx", make_docx(minimal))
    assert response.status_code == 201
    body = response.json()
    assert body["education"] == [] and body["experience"] == []
    assert any("education" in w.lower() for w in body["extraction_warnings"])


def test_cross_user_access_is_denied(client, uploaded_resume):
    other = register(client, "other@example.com")
    rid = uploaded_resume["id"]
    assert client.get(f"/api/v1/resumes/{rid}", headers=other).status_code == 404
    assert client.patch(f"/api/v1/resumes/{rid}/profile", headers=other, json={"summary": "x"}).status_code == 404
    assert client.delete(f"/api/v1/resumes/{rid}", headers=other).status_code == 404


def test_resume_deletion_removes_data(client, auth_headers, uploaded_resume):
    rid = uploaded_resume["id"]
    assert client.delete(f"/api/v1/resumes/{rid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/resumes/{rid}", headers=auth_headers).status_code == 404
    assert client.get("/api/v1/resumes", headers=auth_headers).json() == []


def test_raw_text_only_stored_with_consent(client, auth_headers):
    client.patch("/api/v1/profile", headers=auth_headers, json={"consent_store_resume_text": True})
    body = _upload(client, auth_headers, "cv.pdf", make_pdf(resume_text())).json()
    assert body["raw_text_stored"] is True
    # Withdrawing consent removes stored text.
    client.patch("/api/v1/profile", headers=auth_headers, json={"consent_store_resume_text": False})
    again = client.get(f"/api/v1/resumes/{body['id']}", headers=auth_headers).json()
    assert again["raw_text_stored"] is False


@pytest.fixture()
def retain_files(monkeypatch):
    monkeypatch.setattr(get_settings(), "retain_resume_files", True)


def test_retained_file_deleted_with_resume(client, auth_headers, retain_files, db):
    from pathlib import Path

    from app.models import Resume

    body = _upload(client, auth_headers, "cv.pdf", make_pdf(resume_text())).json()
    assert body["file_retained"] is True
    path = Path(db.get(Resume, __import__("uuid").UUID(body["id"])).storage_path)
    assert path.exists() and path.is_relative_to(get_settings().storage_dir.resolve())
    client.delete(f"/api/v1/resumes/{body['id']}", headers=auth_headers)
    assert not path.exists()
