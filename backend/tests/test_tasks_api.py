"""Tests for app.api.tasks — Task API endpoints."""
import pytest

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    from app.tasks.manager import TaskManager
    tm = TaskManager()
    app.state.task_manager = tm
    with TestClient(app) as c:
        yield c, tm


def test_create_task(client):
    c, tm = client
    resp = c.post("/api/tasks", json={
        "session_id": "sess-1",
        "message": "AI in healthcare",
        "fetch_urls": [],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "pending"


def test_create_task_first_turn_with_urls(client):
    """First turn (user_turns=0) with fetch_urls should still work."""
    c, tm = client
    resp = c.post("/api/tasks", json={
        "session_id": "sess-1",
        "message": "review these",
        "fetch_urls": ["https://arxiv.org/abs/2401.0001"],
    })
    assert resp.status_code == 201


def test_get_task_status(client):
    c, tm = client
    rec = tm.create("sess-1", "test", [])
    resp = c.get(f"/api/tasks/{rec.task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_get_task_not_found(client):
    c, tm = client
    resp = c.get("/api/tasks/nonexistent")
    assert resp.status_code == 404


def test_cancel_task(client):
    c, tm = client
    rec = tm.create("sess-1", "test", [])
    resp = c.delete(f"/api/tasks/{rec.task_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_cancel_not_found(client):
    c, tm = client
    resp = c.delete("/api/tasks/nonexistent")
    assert resp.status_code == 404


def test_stream_task(client):
    c, tm = client
    rec = tm.create("sess-1", "test", [])
    rec.status = "done"
    resp = c.get(f"/api/tasks/{rec.task_id}/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
