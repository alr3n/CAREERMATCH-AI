from app.core.config import get_settings
from tests.conftest import register


def test_register_and_login(client):
    headers = register(client, "a@example.com")
    assert headers["Authorization"].startswith("Bearer ")
    response = client.post("/api/v1/auth/login", json={"email": "A@example.com", "password": "s3cure-pass!"})
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "a@example.com"


def test_duplicate_email_rejected(client):
    register(client, "dup@example.com")
    response = client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "an0ther-pass"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_weak_password_rejected(client):
    response = client.post("/api/v1/auth/register", json={"email": "w@example.com", "password": "password"})
    assert response.status_code == 422


def test_wrong_password_gives_generic_error(client):
    register(client, "b@example.com")
    wrong = client.post("/api/v1/auth/login", json={"email": "b@example.com", "password": "wrong-pass1"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-pass1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_missing_and_invalid_tokens(client):
    assert client.get("/api/v1/profile").status_code == 401
    bad = client.get("/api/v1/profile", headers={"Authorization": "Bearer not-a-token"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "unauthorized"


def test_token_signed_with_other_key_rejected(client):
    import jwt

    register(client, "c@example.com")
    forged = jwt.encode({"sub": "00000000-0000-0000-0000-000000000000", "exp": 9999999999, "iat": 1, "type": "access"},
                        "attacker-key", algorithm="HS256")
    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_login_is_rate_limited(client):
    limit = int(get_settings().rate_limit_auth.split("/")[0])
    codes = [
        client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-pass1"}).status_code
        for _ in range(limit + 1)
    ]
    assert codes[-1] == 429
    assert 429 not in codes[:limit]
