def create_user(client, nickname="student_a"):
    response = client.post(
        "/api/users/simple-login",
        json={"nickname": f"  {nickname}  ", "grade": "2024", "major": "IoT"},
    )
    assert response.status_code in {200, 201}
    return response.json()


def start_session(client, user_id, start_time="2026-05-25T12:30:00+08:00"):
    response = client.post("/api/sessions/start", json={"user_id": user_id, "start_time": start_time})
    assert response.status_code == 201
    return response.json()


def end_session(client, session_id, end_time="2026-05-25T13:50:00+08:00", score=4):
    response = client.post(
        "/api/sessions/end",
        json={
            "session_id": session_id,
            "end_time": end_time,
            "location": "library",
            "task_type": "coding",
            "goal_clarity": 4,
            "light_level": 4,
            "noise_level": 2,
            "fatigue_level": 3,
            "mood_stress": 2,
            "phone_distraction": 2,
            "efficiency_score": score,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_simple_login_creates_and_reuses_nickname(client):
    first = client.post(
        "/api/users/simple-login",
        json={"nickname": "  student_a  ", "grade": "2024", "major": "IoT"},
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["nickname"] == "student_a"

    second = client.post(
        "/api/users/simple-login",
        json={"nickname": "student_a", "grade": "2025", "major": "Other"},
    )
    assert second.status_code == 200
    assert second.json()["id"] == first_body["id"]


def test_start_success_and_duplicate_start_conflict(client):
    user = create_user(client)
    session = start_session(client, user["id"])
    assert session["status"] == "in_progress"
    assert session["user_id"] == user["id"]

    duplicate = client.post("/api/sessions/start", json={"user_id": user["id"]})
    assert duplicate.status_code == 409


def test_abandon_is_idempotent_hidden_from_list_and_allows_new_start(client):
    user = create_user(client)
    session = start_session(client, user["id"])

    abandoned = client.post(
        f"/api/sessions/{session['id']}/abandon",
        json={"reason": "user_requested"},
    )
    assert abandoned.status_code == 200
    body = abandoned.json()
    assert body["status"] == "abandoned"
    assert body["abandoned_at"] is not None
    assert body["abandon_reason"] == "user_requested"
    abandoned_at = body["abandoned_at"]

    again = client.post(f"/api/sessions/{session['id']}/abandon")
    assert again.status_code == 200
    assert again.json()["status"] == "abandoned"
    assert again.json()["abandoned_at"] == abandoned_at
    assert again.json()["abandon_reason"] == "user_requested"

    detail = client.get(f"/api/sessions/{session['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "abandoned"

    listed = client.get(f"/api/sessions/list?user_id={user['id']}")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0

    replacement = start_session(client, user["id"])
    assert replacement["id"] != session["id"]
    assert replacement["status"] == "in_progress"


def test_abandoned_session_cannot_be_completed_and_completed_session_cannot_be_abandoned(client):
    user = create_user(client)
    abandoned = start_session(client, user["id"])
    client.post(f"/api/sessions/{abandoned['id']}/abandon", json={"reason": "user_requested"})

    cannot_complete = client.post(
        "/api/sessions/end",
        json={
            "session_id": abandoned["id"],
            "location": "library",
            "task_type": "coding",
            "goal_clarity": 4,
            "light_level": 4,
            "noise_level": 2,
            "fatigue_level": 3,
            "mood_stress": 2,
            "phone_distraction": 2,
            "efficiency_score": 4,
        },
    )
    assert cannot_complete.status_code == 409

    replacement = start_session(client, user["id"])
    end_session(client, replacement["id"])
    cannot_abandon = client.post(f"/api/sessions/{replacement['id']}/abandon", json={"reason": "user_requested"})
    assert cannot_abandon.status_code == 409


def test_abandon_missing_session_returns_404(client):
    response = client.post("/api/sessions/99999/abandon")
    assert response.status_code == 404


def test_end_calculates_duration_time_period_and_label_then_duplicate_conflict(client):
    user = create_user(client)
    session = start_session(client, user["id"])

    ended = end_session(client, session["id"])
    assert ended["status"] == "completed"
    assert ended["duration_minutes"] == 80
    assert ended["time_period"] == "afternoon"
    assert ended["efficiency_label"] == "high"

    duplicate = client.post(
        "/api/sessions/end",
        json={
            "session_id": session["id"],
            "location": "library",
            "task_type": "coding",
            "goal_clarity": 4,
            "light_level": 4,
            "noise_level": 2,
            "fatigue_level": 3,
            "mood_stress": 2,
            "phone_distraction": 2,
            "efficiency_score": 3,
        },
    )
    assert duplicate.status_code == 409


def test_end_uses_at_least_one_minute_and_late_night_period(client):
    user = create_user(client)
    session = start_session(client, user["id"], start_time="2026-05-25T23:30:00+08:00")
    ended = end_session(client, session["id"], end_time="2026-05-25T23:30:10+08:00", score=2)

    assert ended["duration_minutes"] == 1
    assert ended["time_period"] == "late_night"
    assert ended["efficiency_label"] == "low"


def test_list_and_detail_include_nullable_motion_and_prediction(client):
    user = create_user(client)
    session = start_session(client, user["id"])
    end_session(client, session["id"])

    listed = client.get(f"/api/sessions/list?user_id={user['id']}")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == session["id"]

    detail = client.get(f"/api/sessions/{session['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == session["id"]
    assert body["status"] == "completed"
    assert body["motion_features"] is None
    assert body["latest_prediction"] is None


def test_motion_upload_create_update_and_get(client):
    user = create_user(client)
    session = start_session(client, user["id"])
    end_session(client, session["id"])

    created = client.post(
        "/api/motion/upload",
        json={
            "session_id": session["id"],
            "move_count": 12,
            "shake_count": 1,
            "still_ratio": 0.86,
            "avg_acceleration": 0.14,
            "max_acceleration": 1.92,
        },
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["move_count"] == 12

    updated = client.post(
        "/api/motion/upload",
        json={
            "session_id": session["id"],
            "move_count": 20,
            "shake_count": 2,
            "still_ratio": 0.75,
            "avg_acceleration": 0.2,
            "max_acceleration": 2.4,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == created_body["id"]
    assert updated.json()["move_count"] == 20

    fetched = client.get(f"/api/motion/{session['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["move_count"] == 20


def test_motion_get_missing_returns_404(client):
    user = create_user(client)
    session = start_session(client, user["id"])
    end_session(client, session["id"])

    response = client.get(f"/api/motion/{session['id']}")
    assert response.status_code == 404


def test_update_session_overwrites_existing_record(client):
    user = create_user(client)
    session = start_session(client, user["id"])
    end_session(client, session["id"])

    updated = client.put(
        f"/api/sessions/{session['id']}",
        json={
            "location": "study_room",
            "task_type": "exam_review",
            "goal_clarity": 5,
            "light_level": 5,
            "noise_level": 1,
            "fatigue_level": 2,
            "mood_stress": 2,
            "phone_distraction": 1,
            "efficiency_score": 2,
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["id"] == session["id"]
    assert body["location"] == "study_room"
    assert body["task_type"] == "exam_review"
    assert body["efficiency_score"] == 2
    assert body["efficiency_label"] == "low"

    listed = client.get(f"/api/sessions/list?user_id={user['id']}")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == session["id"]
    assert listed.json()["items"][0]["task_type"] == "exam_review"


def test_delete_session_archives_record_and_removes_from_history(client):
    from app.database import SessionLocal
    from app.models import DeletedStudySession

    user = create_user(client)
    session = start_session(client, user["id"])
    end_session(client, session["id"])
    client.post(
        "/api/motion/upload",
        json={
            "session_id": session["id"],
            "move_count": 12,
            "shake_count": 1,
            "still_ratio": 0.86,
            "avg_acceleration": 0.14,
            "max_acceleration": 1.92,
        },
    )

    deleted = client.delete(f"/api/sessions/{session['id']}")
    assert deleted.status_code == 200
    body = deleted.json()
    assert body["deleted_session_id"] == session["id"]
    assert body["archived_id"] > 0

    listed = client.get(f"/api/sessions/list?user_id={user['id']}")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0

    detail = client.get(f"/api/sessions/{session['id']}")
    assert detail.status_code == 404

    motion = client.get(f"/api/motion/{session['id']}")
    assert motion.status_code == 404

    db = SessionLocal()
    try:
        archived = db.query(DeletedStudySession).filter_by(original_session_id=session["id"]).one()
        assert archived.user_id == user["id"]
        assert archived.task_type == "coding"
        assert archived.efficiency_label == "high"
        assert archived.motion_available == 1
        assert archived.move_count == 12
    finally:
        db.close()
