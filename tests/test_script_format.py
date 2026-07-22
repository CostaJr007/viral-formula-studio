"""Script normalization — recovers full spoken copy from messy LLM output."""

from studio.script_format import normalize_script


def test_clean_pipe_format():
    raw = "\n".join(
        [
            '0:00-0:05 | CLOSE-UP face | "Hook line here right now." | Jump cut | Curiosity gap',
            '0:05-0:12 | MEDIUM shot | "Here is the second spoken sentence with more detail." | Slow zoom | Proof',
            '0:12-0:20 | B-ROLL | "Third line continues the full narration for the viewer." | Cut every 2s | Pace',
        ]
    )
    n = normalize_script(raw)
    assert len(n.blocks) == 3
    assert "Hook line" in n.spoken_copy
    assert "second spoken" in n.spoken_copy
    assert "Third line" in n.spoken_copy
    assert n.spoken_word_count >= 20


def test_mashed_timestamps_in_why_field():
    """Classic Granite failure: next timestamp swallowed into the first WHY field."""
    raw = (
        '0:00-0:05 | CLOSE-UP face | "I\'ve discovered the key to a 100-year life in my mornings." | '
        "Jump cut, text pop-in | Bold claim hooks viewer instantly. "
        '0:05-0:12 | MEDIUM shot | "It starts with light, movement, and a quiet mind." | Slow zoom | Authority'
    )
    n = normalize_script(raw)
    assert len(n.blocks) >= 2
    assert "100-year life" in n.spoken_copy
    assert "light, movement" in n.spoken_copy or "quiet mind" in n.spoken_copy


def test_multiline_without_enough_pipes_recovers_quotes():
    raw = """
0:00-0:05 CLOSE-UP face
"I've discovered the key to a 100-year life in my mornings."
Jump cut, text pop-in
0:05-0:15 MEDIUM
"Next I stretch for two minutes and drink water slowly."
0:15-0:30 B-ROLL
"Then breakfast with protein keeps energy steady all morning."
"""
    n = normalize_script(raw)
    assert n.spoken_word_count >= 15
    assert "100-year life" in n.spoken_copy
    assert "stretch" in n.spoken_copy or "breakfast" in n.spoken_copy


def test_word_count_is_spoken_not_metadata():
    raw = (
        '0:00-0:05 | CLOSE-UP | "One two three four five six seven eight." | Jump cut every 1.1s measured | Psychology note here\n'
        '0:05-0:10 | MEDIUM | "Nine ten eleven twelve thirteen fourteen." | Zoom in | Payoff'
    )
    n = normalize_script(raw)
    # Spoken only — not timestamps/shot labels
    assert n.spoken_word_count == 14
