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


def test_list_creators_merges_sources(tmp_path, monkeypatch):
    transcriptions_file = tmp_path / "transcriptions.json"
    transcriptions_file.write_text(json.dumps({"alpha": []}), encoding="utf-8")

    videos_dir = tmp_path / "videos"
    (videos_dir / "beta").mkdir(parents=True)
    (videos_dir / "__MACOSX").mkdir()

    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "gamma.json").write_text(
        CreatorProfile(creator="gamma", videos_analyzed=1).model_dump_json(), encoding="utf-8"
    )

    monkeypatch.setattr(store.get_settings(), "transcriptions_file", transcriptions_file)
    monkeypatch.setattr(store.get_settings(), "videos_dir", videos_dir)
    monkeypatch.setattr(store.get_settings(), "profiles_dir", profiles_dir)

    assert store.list_creators() == ["alpha", "beta", "gamma"]
