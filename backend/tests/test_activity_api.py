from tests.test_matches_api import _match, _prefs


def test_skill_gaps_and_recommendations(client, auth_headers, uploaded_resume):
    assert client.get("/api/v1/skills/gaps", headers=auth_headers).status_code == 400
    _prefs(client, auth_headers)
    _match(client, auth_headers)
    report = client.get("/api/v1/skills/gaps", headers=auth_headers, params={"top_k": 5}).json()
    assert report["jobs_analyzed"] == 5
    user_skills = {s["skill"] for s in uploaded_resume["skills"]}
    assert report["gaps"] and all(g["skill"] not in user_skills for g in report["gaps"])
    assert all(g["examples"] for g in report["gaps"])
    assert any(f["user_has"] for f in report["skill_frequency"])
    recs = client.get("/api/v1/skills/recommendations", headers=auth_headers).json()
    assert recs["recommendations"]
    for rec in recs["recommendations"]:
        assert rec["project_idea"] and rec["how_to_demonstrate"]
        assert all(r["cost"] == "free" and r["url"].startswith("https://") for r in rec["resources"])
        assert rec["resources"] or rec["resources_note"]


def test_saved_jobs_flow(client, auth_headers):
    jobs = client.get("/api/v1/jobs", headers=auth_headers).json()["items"]
    job_id = jobs[0]["id"]
    assert client.post("/api/v1/saved-jobs", headers=auth_headers, json={"job_id": job_id}).status_code == 201
    assert client.post("/api/v1/saved-jobs", headers=auth_headers, json={"job_id": job_id}).status_code == 201  # idempotent
    saved = client.get("/api/v1/saved-jobs", headers=auth_headers).json()
    assert saved["total"] == 1 and saved["items"][0]["job"]["is_saved"] is True
    assert client.get("/api/v1/jobs", headers=auth_headers, params={"saved_only": True}).json()["total"] == 1
    detail = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers).json()
    assert detail["is_saved"] is True
    assert client.delete(f"/api/v1/saved-jobs/{job_id}", headers=auth_headers).status_code == 204
    assert client.delete(f"/api/v1/saved-jobs/{job_id}", headers=auth_headers).status_code == 404
    assert client.get("/api/v1/saved-jobs", headers=auth_headers).json()["total"] == 0
    missing = client.post("/api/v1/saved-jobs", headers=auth_headers,
                          json={"job_id": "00000000-0000-0000-0000-000000000000"})
    assert missing.status_code == 404


def test_history_records_runs_without_resume_data(client, auth_headers, uploaded_resume):
    _match(client, auth_headers)
    client.post("/api/v1/jobs/search", headers=auth_headers, json={"q": "intern"})
    history = client.get("/api/v1/history", headers=auth_headers).json()
    assert [h["kind"] for h in history["items"]] == ["search", "match"]
    serialized = str(history)
    assert "Python" not in serialized and "Acme" not in serialized
    assert client.delete("/api/v1/history", headers=auth_headers).status_code == 204
    assert client.get("/api/v1/history", headers=auth_headers).json()["total"] == 0


def test_evaluation_summary_not_yet_evaluated(client, auth_headers, monkeypatch, tmp_path):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "evaluation_report_path", tmp_path / "missing.json")
    body = client.get("/api/v1/evaluation/summary", headers=auth_headers).json()
    assert body == {"status": "not_evaluated", "source": None, "report": None, "message": "Not yet evaluated."}
