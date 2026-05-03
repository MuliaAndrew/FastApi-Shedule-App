def test_first_registered_user_becomes_admin(client):
    resp = client.post("/auth/register", json={"username": "first", "password": "pass"})
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"


def test_subsequent_users_become_readers(client):
    client.post("/auth/register", json={"username": "first", "password": "pass"})
    resp = client.post("/auth/register", json={"username": "second", "password": "pass"})
    assert resp.status_code == 201
    assert resp.json()["role"] == "reader"


def test_register_duplicate_username_rejected(client):
    client.post("/auth/register", json={"username": "user", "password": "pass"})
    resp = client.post("/auth/register", json={"username": "user", "password": "pass"})
    assert resp.status_code == 400


def test_login_returns_token(client):
    client.post("/auth/register", json={"username": "user", "password": "pass"})
    resp = client.post("/auth/login", json={"username": "user", "password": "pass"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "user", "password": "pass"})
    resp = client.post("/auth/login", json={"username": "user", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/auth/login", json={"username": "ghost", "password": "pass"})
    assert resp.status_code == 401
