"""Speech-vs-junk filters — never treat API/URL noise as signature phrases."""

from studio.text_quality import (
    filter_expression,
    is_error_blob,
    is_speech_like,
    spoken_tokens,
    top_content_phrases,
)


def test_error_blob_quota_ibm():
    blob = (
        "Error: quota status failed https://cloud.ibm.com/api chat code "
        "request unauthorized token bearer"
    )
    assert is_error_blob(blob)
    assert not is_speech_like(blob)


def test_real_speech_ok():
    text = (
        "You need to build more muscle with progressive overload. "
        "This will target the legs slightly differently each week."
    )
    assert is_speech_like(text)
    assert not is_error_blob(text)
    toks = spoken_tokens(text)
    assert "muscle" in toks or "build" in toks
    assert "https" not in toks
    assert "ibm" not in toks


def test_filter_junk_phrases():
    assert not filter_expression("https")
    assert not filter_expression("ibm")
    assert not filter_expression("quota")
    assert not filter_expression("chat")
    assert filter_expression("build more muscle")
    assert filter_expression("progressive overload")


def test_top_phrases_ignore_error_text():
    phrases = top_content_phrases(
        [
            "quota status https://cloud.ibm.com chat code error",
            "You need heavier weights to build muscle over time with good form.",
        ]
    )
    joined = " ".join(phrases)
    assert "ibm" not in joined
    assert "quota" not in joined
    assert "https" not in joined
