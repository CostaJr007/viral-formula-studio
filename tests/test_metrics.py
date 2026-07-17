"""Deterministic metrics — no LLM involved, real ffmpeg/Python only."""

from pathlib import Path

import pytest

from studio import metrics

SAMPLE_VIDEO = Path(__file__).resolve().parent.parent / "videos" / "jeffnippard" / "17842309335381738.mp4"

pytestmark = pytest.mark.skipif(not SAMPLE_VIDEO.exists(), reason="vídeo de exemplo ausente")


def test_cut_metrics_real_video():
    m = metrics.cut_metrics(SAMPLE_VIDEO)
    assert m["duration_s"] > 0
    assert m["cuts"] >= 0
    assert m["cuts_per_min"] >= 0
    assert m["avg_shot_length_s"] > 0


def test_signature_ngrams_counts(monkeypatch):
    fake = [
        {"video": "a.mp4", "transcription": "no final do dia você precisa treinar. no final do dia importa dieta."},
        {"video": "b.mp4", "transcription": "treinar pesado sempre. no final do dia, descanso."},
    ]
    monkeypatch.setattr(metrics.store, "get_creator_transcriptions", lambda creator: fake)

    grams = metrics.signature_ngrams("qualquer", n=3)

    assert grams
    assert grams[0]["ngram"] == "final do dia"
    assert grams[0]["count"] == 3


def test_speech_metrics_real_video(monkeypatch):
    fake = [{"video": SAMPLE_VIDEO.name, "transcription": " ".join(["palavra"] * 200)}]
    monkeypatch.setattr(metrics.store, "get_creator_transcriptions", lambda creator: fake)

    result = metrics.speech_metrics("jeffnippard")

    assert result["avg_wpm"] > 0
    assert result["per_video"][0]["words"] == 200
