from tests.conftest import register


def _match(client, headers, **body):
    response = client.post("/api/v1/matches", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _prefs(client, headers):
    client.patch("/api/v1/profile", headers=headers, json={
        "career_stage": "student", "preferred_titles": ["Data Analyst"],
        "work_arrangements": ["remote", "hybrid"], "employment_types": ["internship"],
    })


def test_matching_requires_resume(client, auth_headers):
    response = client.post("/api/v1/matches", headers=auth_headers, json={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "resume_required"

def test_matching_ranks_relevant_jobs_first(client, auth_headers, uploaded_resume):
    _prefs(client, auth_headers)
    run = _match(client, auth_headers, limit=20)
    assert run["total_considered"] == 20
    assert run["model_version"] == "transparent-v1"
    assert "lsa" in run["semantic_backend"]
    assert "not a probability" in run["disclaimer"]
    top_titles = [r["job"]["title"] for r in run["results"][:3]]
    assert any("Data" in t or "Business Intelligence" in t for t in top_titles)
    scores = [r["score"] for r in run["results"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 100 for s in scores)
    first = run["results"][0]
    assert first["matched_skills"] and first["top_reason"]

def test_matching_is_deterministic(client, auth_headers, uploaded_resume):
    a = [(r["job"]["id"], r["score"]) for r in _match(client, auth_headers)["results"]]
    b = [(r["job"]["id"], r["score"]) for r in _match(client, auth_headers)["results"]]
    assert a == b

def test_custom_weights_and_filters(client, auth_headers, uploaded_resume):
    run = _match(client, auth_headers, weights={"required_skill_coverage": 1, "semantic_similarity": 0,
                                                "preferred_skill_coverage": 0, "experience_compatibility": 0,
                                                "preference_compatibility": 0, "profile_relevance": 0},
                 filters={"employment_types": ["internship"]})
    assert all(r["job"]["employment_type"] == "internship" for r in run["results"])
    assert run["weights"]["required_skill_coverage"] == 1.0
    bad = client.post("/api/v1/matches", headers=auth_headers, json={"weights": {"luck": 1}})
    assert bad.status_code == 422

def test_match_detail_explains_recommendation(client, auth_headers, uploaded_resume):
    run = _match(client, auth_headers)
    match_id = run["results"][0]["id"]
    detail = client.get(f"/api/v1/matches/{match_id}", headers=auth_headers).json()
    kinds = {e["kind"] for e in detail["evidence"]}
    assert {"reason", "matched_skill"} <= kinds
    assert "caveat" in kinds  # demo data is always flagged
    assert detail["job"]["apply_url"] and detail["job"]["last_checked_at"]
    assert set(detail["component_labels"]) == set(detail["components"])

    listing = client.get("/api/v1/matches", headers=auth_headers).json()
    assert listing["run_id"] == run["run_id"] and listing["total"] == len(run["results"])

def test_matches_are_private(client, auth_headers, uploaded_resume):
    match_id = _match(client, auth_headers)["results"][0]["id"]
    other = register(client, "intruder@example.com")
    assert client.get(f"/api/v1/matches/{match_id}", headers=other).status_code == 404
    assert client.get("/api/v1/matches", headers=other).json()["items"] == []

def test_feedback(client, auth_headers, uploaded_resume, db):
    from sqlalchemy import select

    from app.models import UserFeedback

    match_id = _match(client, auth_headers)["results"][0]["id"]
    assert client.post(f"/api/v1/matches/{match_id}/feedback", headers=auth_headers,
                       json={"rating": "relevant"}).status_code == 204
    assert db.scalar(select(UserFeedback)).rating == "relevant"
    detail = client.get(f"/api/v1/matches/{match_id}", headers=auth_headers).json()
    assert detail["feedback"] == "relevant"

def test_resume_deletion_cascades_to_matches(client, auth_headers, uploaded_resume, db):
    from sqlalchemy import func, select

    from app.models import MatchResult

    _match(client, auth_headers)
    assert db.scalar(select(func.count(MatchResult.id))) > 0
    client.delete(f"/api/v1/resumes/{uploaded_resume['id']}", headers=auth_headers)
    db.expire_all()
    assert db.scalar(select(func.count(MatchResult.id))) == 0
