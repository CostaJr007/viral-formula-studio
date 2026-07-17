"""Link ingestion helpers — VTT parsing and URL handling (no network needed)."""

from studio.ingest import parse_vtt

SAMPLE_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:02.000
this is the first line

00:00:02.000 --> 00:00:04.000
this is the first line

00:00:04.000 --> 00:00:06.500
and here comes <b>the second</b> one

00:00:06.500 --> 00:00:08.000
and a third
"""


def test_parse_vtt_dedupes_and_strips_tags():
    text = parse_vtt(SAMPLE_VTT)

    assert "-->" not in text
    assert "<b>" not in text
    # duplicate caption line appears only once
    assert text.count("this is the first line") == 1
    assert "the second one" in text
    assert "and a third" in text


def test_parse_vtt_empty():
    assert parse_vtt("WEBVTT\n\n") == ""
