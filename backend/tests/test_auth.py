def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_and_me(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "username": "newbie", "password": "secret123"},
    )
    assert r.status_code == 201, r.text
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["role"] == "student"


def test_register_duplicate(client):
    body = {"email": "dup@example.com", "username": "dupuser", "password": "secret123"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409
    body2 = {"email": "other@example.com", "username": "dupuser", "password": "secret123"}
    assert client.post("/api/auth/register", json=body2).status_code == 409


def test_login_by_email_and_username(client):
    assert client.post(
        "/api/auth/login", json={"login": "stud@example.com", "password": "studentpass1"}
    ).status_code == 200
    assert client.post(
        "/api/auth/login", json={"login": "student1", "password": "studentpass1"}
    ).status_code == 200


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"login": "student1", "password": "wrong"})
    assert r.status_code == 401


def test_refresh_flow(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "ref@example.com", "username": "reffan", "password": "secret123"},
    )
    tokens = r.json()
    rr = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rr.status_code == 200
    # access-токен вместо refresh не принимается
    bad = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_blocked_user_cannot_login(client, admin_headers):
    from app.db import SessionLocal
    from app.models import User

    db = SessionLocal()
    uid = db.query(User).filter_by(username="student1").first().id
    db.close()
    assert client.patch(f"/api/admin/users/{uid}", json={"is_active": False}, headers=admin_headers).status_code == 200
    assert client.post("/api/auth/login", json={"login": "student1", "password": "studentpass1"}).status_code == 403
    # разблокировка через прямой доступ к БД (fixture-состояние для других тестов)
    db = SessionLocal()
    db.query(User).filter_by(id=uid).first().is_active = True
    db.commit()
    db.close()
