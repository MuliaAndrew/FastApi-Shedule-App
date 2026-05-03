BOOKING = {
    "title": "Math Lecture",
    "description": "Calculus 101",
    "start_time": "2024-09-01T10:00:00",
    "end_time": "2024-09-01T11:30:00",
    "booking_type": "regular",
}


def _make_booking(client, classroom_id, token, overrides=None):
    data = {**BOOKING, "classroom_id": classroom_id, **(overrides or {})}
    return client.post("/bookings", json=data, headers={"Authorization": f"Bearer {token}"})


# ── Creation ──────────────────────────────────────────────────────────────────

def test_create_booking_as_editor(client, editor_token, classroom_id):
    resp = _make_booking(client, classroom_id, editor_token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Math Lecture"
    assert data["classroom_id"] == classroom_id


def test_create_booking_unauthenticated_rejected(client, classroom_id):
    resp = client.post("/bookings", json={**BOOKING, "classroom_id": classroom_id})
    assert resp.status_code in (401, 403)


def test_booking_uid_increases_monotonically(client, editor_token, classroom_id):
    r1 = _make_booking(client, classroom_id, editor_token, {
        "start_time": "2024-09-01T08:00:00",
        "end_time": "2024-09-01T09:00:00",
    })
    r2 = _make_booking(client, classroom_id, editor_token, {
        "start_time": "2024-09-01T09:00:00",
        "end_time": "2024-09-01T10:00:00",
    })
    assert r1.json()["id"] < r2.json()["id"]


# ── Overlap detection ─────────────────────────────────────────────────────────

def test_overlapping_booking_rejected(client, editor_token, classroom_id):
    _make_booking(client, classroom_id, editor_token)
    # overlaps: starts during first booking
    resp = _make_booking(client, classroom_id, editor_token, {
        "start_time": "2024-09-01T11:00:00",
        "end_time": "2024-09-01T12:00:00",
    })
    assert resp.status_code == 409


def test_adjacent_bookings_allowed(client, editor_token, classroom_id):
    _make_booking(client, classroom_id, editor_token)  # ends at 11:30
    resp = _make_booking(client, classroom_id, editor_token, {
        "start_time": "2024-09-01T11:30:00",
        "end_time": "2024-09-01T13:00:00",
    })
    assert resp.status_code == 201


# ── Time granularity ──────────────────────────────────────────────────────────

def test_non_5min_boundary_rejected(client, editor_token, classroom_id):
    resp = _make_booking(client, classroom_id, editor_token, {
        "start_time": "2024-09-01T10:03:00",  # 3 minutes — invalid
        "end_time": "2024-09-01T11:00:00",
    })
    assert resp.status_code == 422


def test_seconds_nonzero_rejected(client, editor_token, classroom_id):
    resp = _make_booking(client, classroom_id, editor_token, {
        "start_time": "2024-09-01T10:00:30",  # 30 seconds — invalid
        "end_time": "2024-09-01T11:00:00",
    })
    assert resp.status_code == 422


# ── Public read ───────────────────────────────────────────────────────────────

def test_list_classroom_bookings_is_public(client, editor_token, classroom_id):
    _make_booking(client, classroom_id, editor_token)
    resp = client.get(f"/bookings/classroom/{classroom_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_editor_bookings_is_public(client, admin_token, editor_token, classroom_id):
    _make_booking(client, classroom_id, editor_token)
    # figure out editor's user id from the editors list
    editors = client.get("/users/editors").json()
    editor_id = editors[0]["id"]
    resp = client.get(f"/bookings/editor/{editor_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── Update & delete ───────────────────────────────────────────────────────────

def test_editor_can_update_own_booking(client, editor_token, classroom_id):
    booking_id = _make_booking(client, classroom_id, editor_token).json()["id"]
    resp = client.patch(
        f"/bookings/{booking_id}",
        json={"title": "Updated"},
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"


def test_editor_cannot_update_others_booking(client, admin_token, editor_token, classroom_id):
    client.post(
        "/users/editors",
        json={"username": "editor2", "password": "pass2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    token2 = client.post("/auth/login", json={"username": "editor2", "password": "pass2"}).json()[
        "access_token"
    ]
    booking_id = _make_booking(client, classroom_id, editor_token).json()["id"]
    resp = client.patch(
        f"/bookings/{booking_id}",
        json={"title": "Hijack"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403


def test_editor_cannot_delete_others_booking(client, admin_token, editor_token, classroom_id):
    client.post(
        "/users/editors",
        json={"username": "editor2", "password": "pass2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    token2 = client.post("/auth/login", json={"username": "editor2", "password": "pass2"}).json()[
        "access_token"
    ]
    booking_id = _make_booking(client, classroom_id, editor_token).json()["id"]
    resp = client.delete(
        f"/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403


def test_admin_can_delete_any_booking(client, admin_token, editor_token, classroom_id):
    booking_id = _make_booking(client, classroom_id, editor_token).json()["id"]
    resp = client.delete(
        f"/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


def test_update_to_overlapping_time_rejected(client, editor_token, classroom_id):
    _make_booking(client, classroom_id, editor_token)
    b2_id = _make_booking(client, classroom_id, editor_token, {
        "start_time": "2024-09-01T12:00:00",
        "end_time": "2024-09-01T13:00:00",
    }).json()["id"]
    resp = client.patch(
        f"/bookings/{b2_id}",
        json={"start_time": "2024-09-01T11:00:00"},  # overlaps first booking
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 409


# ── Smart suggestion ──────────────────────────────────────────────────────────

def test_suggest_full_match(client, admin_token, editor_token):
    # Classroom A: capacity 30, projector + AC
    ca = client.post(
        "/classrooms",
        json={
            "number": "A1", "building": "A", "capacity": 30,
            "has_projector": True, "has_virtual_board": False,
            "has_camera": False, "has_ac": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()
    # Classroom B: capacity 30, no features
    client.post(
        "/classrooms",
        json={
            "number": "B1", "building": "B", "capacity": 30,
            "has_projector": False, "has_virtual_board": False,
            "has_camera": False, "has_ac": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = client.post(
        "/bookings/suggest",
        json={
            "min_capacity": 20,
            "start_time": "2024-09-01T10:00:00",
            "end_time": "2024-09-01T12:00:00",
            "requires_projector": True,
            "requires_ac": True,
        },
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["full_matches"]) == 1
    assert data["full_matches"][0]["id"] == ca["id"]
    assert data["partial_matches"] == []


def test_suggest_partial_match_when_no_full(client, admin_token, editor_token):
    # Only classroom without the required feature
    client.post(
        "/classrooms",
        json={
            "number": "C1", "building": "C", "capacity": 30,
            "has_projector": False, "has_virtual_board": False,
            "has_camera": False, "has_ac": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = client.post(
        "/bookings/suggest",
        json={
            "min_capacity": 20,
            "start_time": "2024-09-01T10:00:00",
            "end_time": "2024-09-01T12:00:00",
            "requires_projector": True,
        },
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_matches"] == []
    assert len(data["partial_matches"]) == 1


def test_suggest_excludes_booked_classrooms(client, admin_token, editor_token, classroom_id):
    # classroom_id fixture already has projector + AC, capacity 30
    # Book it so it's unavailable
    _make_booking(client, classroom_id, editor_token)

    resp = client.post(
        "/bookings/suggest",
        json={
            "min_capacity": 10,
            "start_time": "2024-09-01T10:00:00",
            "end_time": "2024-09-01T11:00:00",
        },
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    ids = [c["id"] for c in data["full_matches"] + data["partial_matches"]]
    assert classroom_id not in ids


def test_suggest_requires_auth(client):
    resp = client.post(
        "/bookings/suggest",
        json={
            "min_capacity": 10,
            "start_time": "2024-09-01T10:00:00",
            "end_time": "2024-09-01T11:00:00",
        },
    )
    assert resp.status_code in (401, 403)
