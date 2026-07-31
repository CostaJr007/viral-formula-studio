"""Judge-path seed creators — profile shape must match frontend needs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api import app
from studio.create import _coerce_profile, slim_profile_for_prompt
from studio.store import list_creators, load_profile

# Keep in sync with frontend SEED_NAMES / DEMO_CREATORS in routes/index.tsx
SEED_NAMES = ("jeffnippard", "kallaway", "rourkeheath")


def test_seed_list_is_exactly_demo_creators():
    names = [n.lower() for n in list_creators()]
    assert set(names) == set(SEED_NAMES)
    for seed in SEED_NAMES:
        assert seed in names


def test_each_seed_profile_has_judge_ready_fields():
    for name in SEED_NAMES:
        profile = load_profile(name)
        assert profile is not None, name
        assert profile.metrics, f"{name}: metrics required (ffmpeg pre-measured)"
        editing = (profile.metrics or {}).get("editing") or {}
        speech = (profile.metrics or {}).get("speech") or {}
        assert editing.get("avg_cuts_per_min") is not None, name
        assert editing.get("avg_shot_length_s") is not None, name
        assert speech.get("avg_wpm") is not None, name
        assert profile.style is not None, f"{name}: style required for hooks"
        assert profile.editing is not None, f"{name}: editing required for script"
        assert profile.style.hook_patterns, f"{name}: hook patterns required"
        assert profile.audience, f"{name}: audience snapshot for UI"
        assert profile.audience.get("followers_display"), name
        # Client re-send path (frontend posts profile on /api/hooks and /api/copy)
        coerced = _coerce_profile(name, profile.model_dump())
        slim = slim_profile_for_prompt(coerced)
        assert slim["metrics"]["editing"]["avg_cuts_per_min"] is not None
        assert slim["style"]["tone"]


def test_api_creators_and_profile_endpoints():
    client = TestClient(app)
    r = client.get("/api/creators")
    assert r.status_code == 200
    body = r.json()
    names = {c["name"].lower() for c in body["creators"]}
    assert names == set(SEED_NAMES)
    for c in body["creators"]:
        assert c["has_profile"] is True
        assert c["has_metrics"] is True
        assert c.get("audience")

    for name in SEED_NAMES:
        pr = client.get(f"/api/profile/{name}")
        assert pr.status_code == 200, name
        data = pr.json()
        assert data["creator"].lower() == name
        assert data["metrics"]["editing"]["avg_cuts_per_min"] is not None
        assert data["style"]["tone"]
        assert data["editing"]["cut_cadence"]
        assert data.get("audience", {}).get("followers_display")

    # Bryan removed from demo seeds
    assert client.get("/api/profile/Bryan").status_code == 404
    assert client.get("/api/profile/bryan").status_code == 404


def test_hooks_copy_request_validation():
    client = TestClient(app)
    # topic too short
    assert (
        client.post("/api/hooks", json={"creator": "jeffnippard", "topic": "ab"}).status_code
        == 422
    )
    # hook too short
    assert (
        client.post(
            "/api/copy",
            json={"creator": "jeffnippard", "topic": "valid topic here", "hook": "hi"},
        ).status_code
        == 422
    )
