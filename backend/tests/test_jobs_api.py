def _jobs(client, headers, **params):
    response = client.get("/api/v1/jobs", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_listings_carry_source_and_original_links(client, auth_headers):
    body = _jobs(client, auth_headers, page_size=100)
    assert body["total"] == 20
    for item in body["items"]:
        assert "is_demo" not in item
        assert item["source_platform"] == "Test fixture"
        assert item["apply_url"].startswith("https://example.com/")
        assert item["posting_url"].startswith("https://example.com/")


def test_company_platform_and_salary_filters(client, auth_headers):
    kalye = _jobs(client, auth_headers, company="kalye", page_size=100)["items"]
    assert kalye and all(j["company"] == "Kalye Commerce" for j in kalye)
    by_platform = _jobs(client, auth_headers, platforms="Test fixture", page_size=100)
    assert by_platform["total"] == 20
    assert _jobs(client, auth_headers, platforms="LinkedIn")["total"] == 0
    paid = _jobs(client, auth_headers, has_salary=True, page_size=100)["items"]
    assert paid and all(j["salary_min"] is not None for j in paid)
    assert len(paid) < 20  # listings without salary are not given one


def test_filters_operate_on_stored_data(client, auth_headers):
    interns = _jobs(client, auth_headers, employment_types="internship", page_size=100)["items"]
    assert interns and all(j["employment_type"] == "internship" for j in interns)
    remote = _jobs(client, auth_headers, work_arrangements="remote", page_size=100)["items"]
    assert remote and all(j["work_arrangement"] == "remote" for j in remote)
    cebu = _jobs(client, auth_headers, location="cebu", page_size=100)["items"]
    assert cebu and all("Cebu" in j["location"] for j in cebu)
    sql = _jobs(client, auth_headers, skills="SQL", page_size=100)["items"]
    assert sql and all("Data" in j["title"] or "Business" in j["title"] or "Support" in j["title"] or "QA" in j["title"] for j in sql)
    keyword = _jobs(client, auth_headers, q="android")["items"]
    assert [j["title"] for j in keyword] == ["Junior Android Developer"]
    recent = _jobs(client, auth_headers, checked_within_days=1)
    assert recent["total"] == 20


def test_salary_filter_only_uses_listings_with_salary(client, auth_headers):
    response = client.post("/api/v1/jobs/search", headers=auth_headers,
                           json={"salary_min": 30000, "salary_currency": "PHP", "page_size": 100})
    items = response.json()["items"]
    assert items and all(float(j["salary_max"]) >= 30000 for j in items)


def test_job_detail_has_attribution_and_requirements(client, auth_headers):
    job = _jobs(client, auth_headers, q="Data Analyst Intern")["items"][0]
    detail = client.get(f"/api/v1/jobs/{job['id']}", headers=auth_headers).json()
    assert "Retrieved from" in detail["source_attribution"] and "Test fixture" in detail["source_attribution"]
    levels = {s["skill"]: s["requirement"] for s in detail["skills"]}
    assert levels["SQL"] == "required" and levels["Power BI"] == "preferred"
    assert detail["required_qualifications"]
    assert detail["freshness"] == "fresh"


def test_search_is_recorded_without_resume_data(client, auth_headers, db):
    from sqlalchemy import select

    from app.models import SearchHistory

    client.post("/api/v1/jobs/search", headers=auth_headers, json={"q": "analyst", "work_arrangements": ["remote"]})
    entry = db.scalar(select(SearchHistory))
    assert entry.kind == "search"
    assert entry.query == {"q": "analyst", "work_arrangements": ["remote"]}


def test_facets(client, auth_headers):
    body = client.get("/api/v1/jobs/facets", headers=auth_headers).json()
    assert body["total_active"] == 20 and "demo_active" not in body
    assert body["platforms"] == [{"value": "Test fixture", "count": 20}]
    assert 0 < body["with_salary"] < 20
    assert any(c["value"] == "Kalye Commerce" for c in body["companies"])
    assert any(c["value"] == "Data & Analytics" for c in body["categories"])


def test_unknown_job_404(client, auth_headers):
    assert client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000", headers=auth_headers).status_code == 404


def test_jobs_require_auth(client):
    assert client.get("/api/v1/jobs").status_code == 401
