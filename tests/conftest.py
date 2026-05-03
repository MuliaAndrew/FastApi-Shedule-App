import os

# Set before any app.* import so app.database uses SQLite, not PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_schedule.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///./test_schedule.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_token(client):
    client.post("/auth/register", json={"username": "admin", "password": "adminpass"})
    resp = client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    return resp.json()["access_token"]


@pytest.fixture()
def editor_token(client, admin_token):
    client.post(
        "/users/editors",
        json={"username": "editor", "password": "editorpass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = client.post("/auth/login", json={"username": "editor", "password": "editorpass"})
    return resp.json()["access_token"]


@pytest.fixture()
def classroom_id(client, admin_token):
    resp = client.post(
        "/classrooms",
        json={
            "number": "101",
            "building": "A",
            "capacity": 30,
            "has_projector": True,
            "has_virtual_board": False,
            "has_camera": False,
            "has_ac": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return resp.json()["id"]
