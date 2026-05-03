CLASSROOM = {
    "number": "101",
    "building": "A",
    "capacity": 30,
    "has_projector": True,
    "has_virtual_board": False,
    "has_camera": False,
    "has_ac": True,
}


def test_list_classrooms_is_public(client):
    resp = client.get("/classrooms")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_classroom_requires_admin(client):
    resp = client.post("/classrooms", json=CLASSROOM)
    assert resp.status_code in (401, 403)


def test_create_classroom_as_admin(client, admin_token):
    resp = client.post(
        "/classrooms", json=CLASSROOM, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"] == "101"
    assert data["has_projector"] is True
    assert "id" in data


def test_get_classroom(client, admin_token, classroom_id):
    resp = client.get(f"/classrooms/{classroom_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == classroom_id


def test_get_classroom_not_found(client):
    resp = client.get("/classrooms/9999")
    assert resp.status_code == 404


def test_update_classroom_capacity(client, admin_token, classroom_id):
    resp = client.patch(
        f"/classrooms/{classroom_id}",
        json={"capacity": 60},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["capacity"] == 60


def test_delete_classroom(client, admin_token, classroom_id):
    resp = client.delete(
        f"/classrooms/{classroom_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204
    assert client.get(f"/classrooms/{classroom_id}").status_code == 404


def test_editor_cannot_create_classroom(client, admin_token, editor_token):
    resp = client.post(
        "/classrooms", json=CLASSROOM, headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert resp.status_code == 403
