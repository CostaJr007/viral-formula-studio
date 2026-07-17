"""Frame extraction — verifies the real ffmpeg pipeline end to end (no API keys needed)."""

from pathlib import Path

import pytest

from studio.frames import extract_frames, get_video_duration

SAMPLE_VIDEO = Path(__file__).resolve().parent.parent / "videos" / "jeffnippard" / "17842309335381738.mp4"

pytestmark = pytest.mark.skipif(not SAMPLE_VIDEO.exists(), reason="vídeo de exemplo ausente")


def test_get_video_duration():
    assert get_video_duration(SAMPLE_VIDEO) > 0


def test_extract_frames(tmp_path):
    frames = extract_frames(SAMPLE_VIDEO, tmp_path, max_frames=4)

    assert 0 < len(frames) <= 4
    for frame in frames:
        assert frame.suffix == ".jpg"
        assert frame.stat().st_size > 0
