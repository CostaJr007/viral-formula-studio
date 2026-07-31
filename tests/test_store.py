"""Store persistence — profiles roundtrip and creator listing."""

import json

from studio import store
from studio.schemas import CreatorProfile


def test_profile_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(store.get_settings(), "profiles_dir", tmp_path)

    profile = CreatorProfile(creator="teste", videos_analyzed=3)
    path = store.save_profile(profile)

    assert path.exists()
    loaded = store.load_profile("teste")
    assert loaded is not None
    assert loaded.creator == "teste"
    assert loaded.videos_analyzed == 3


def test_load_profile_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(store.get_settings(), "profiles_dir", tmp_path)
    assert store.load_profile("inexistente") is None


def test_list_creators_only_profiles_with_metrics(tmp_path, monkeypatch):
    """Demo/list shows only click-ready profiles (metrics already measured)."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    # Complete seed-style profile
    ready = CreatorProfile(
        creator="Bryan",
        videos_analyzed=1,
        metrics={
            "editing": {"avg_cuts_per_min": 6.1, "avg_shot_length_s": 8.4},
            "speech": {"avg_wpm": 202.2},
        },
    )
    (profiles_dir / "bryan.json").write_text(ready.model_dump_json(), encoding="utf-8")

    # Stub without metrics — must not appear
    (profiles_dir / "empty.json").write_text(
        CreatorProfile(creator="empty", videos_analyzed=0).model_dump_json(), encoding="utf-8"
    )
    # Test junk name — must not appear
    (profiles_dir / "test_junk.json").write_text(
        CreatorProfile(
            creator="test_junk",
            videos_analyzed=1,
            metrics={"editing": {"avg_cuts_per_min": 1.0}},
        ).model_dump_json(),
        encoding="utf-8",
    )

    # Videos / transcriptions alone must not pollute the list
    videos_dir = tmp_path / "videos"
    (videos_dir / "rourkeheath").mkdir(parents=True)
    transcriptions_file = tmp_path / "transcriptions.json"
    transcriptions_file.write_text(json.dumps({"rourkeheath": []}), encoding="utf-8")

    monkeypatch.setattr(store.get_settings(), "profiles_dir", profiles_dir)
    monkeypatch.setattr(store.get_settings(), "videos_dir", videos_dir)
    monkeypatch.setattr(store.get_settings(), "transcriptions_file", transcriptions_file)

    assert store.list_creators() == ["Bryan"]
