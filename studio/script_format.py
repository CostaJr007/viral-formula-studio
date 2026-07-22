"""Normalize shooting-script text returned by LLMs into stable blocks.

Models often drift from the ideal pipe format:
  [TIMESTAMP] | [SHOT] | [TEXT] | [EDITING] | [WHY]

This module recovers as much structure as possible so the frontend can always
render a complete spoken copy + shooting board, even when Granite/OpenAI
returns newlines inside fields, mashed blocks, or partial pipes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Block start: "0:00-0:05" or "0:00 - 0:05"
_TS_BLOCK = re.compile(r"(?P<ts>\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})")
_QUOTED = re.compile(r'"([^"]{3,})"|“([^”]{3,})”')
_AUDIO_ONLY = re.compile(r"no speech|music only|^\(.*\)$", re.IGNORECASE)


@dataclass
class ScriptBlock:
    timestamp: str
    shot: str
    text: str
    editing: str
    why: str

    def to_pipe_line(self) -> str:
        return " | ".join(
            [
                self.timestamp or "0:00-0:00",
                self.shot or "MEDIUM shot",
                self.text or "(no speech — music only)",
                self.editing or "Match creator cut cadence",
                self.why or "Retention pacing",
            ]
        )

    def spoken(self) -> str | None:
        t = (self.text or "").strip()
        if not t:
            return None
        if _AUDIO_ONLY.search(t):
            return None
        # Strip surrounding quotes for the clean copy panel
        if (t.startswith('"') and t.endswith('"')) or (t.startswith("“") and t.endswith("”")):
            t = t[1:-1].strip()
        return t or None


@dataclass
class NormalizedScript:
    blocks: list[ScriptBlock] = field(default_factory=list)
    script: str = ""
    spoken_copy: str = ""
    spoken_word_count: int = 0
    was_repaired: bool = False
    raw_preview: str = ""


def _clean_field(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _parts_to_block(parts: list[str]) -> ScriptBlock | None:
    parts = [_clean_field(p) for p in parts if _clean_field(p) or p == ""]
    if not parts:
        return None
    # Pad / merge so we always get 5 logical fields
    if len(parts) == 1:
        # Single blob — try to peel a leading timestamp
        m = _TS_BLOCK.match(parts[0])
        if m:
            rest = parts[0][m.end() :].strip(" |:-")
            return ScriptBlock(timestamp=_clean_field(m.group("ts")), shot="MEDIUM shot", text=rest, editing="", why="")
        return ScriptBlock(timestamp="", shot="", text=parts[0], editing="", why="")
    if len(parts) == 2:
        return ScriptBlock(timestamp=parts[0], shot=parts[1], text="", editing="", why="")
    if len(parts) == 3:
        return ScriptBlock(timestamp=parts[0], shot=parts[1], text=parts[2], editing="", why="")
    if len(parts) == 4:
        return ScriptBlock(timestamp=parts[0], shot=parts[1], text=parts[2], editing=parts[3], why="")
    # 5+ — extra pipes usually belong to the psychology field
    return ScriptBlock(
        timestamp=parts[0],
        shot=parts[1],
        text=parts[2],
        editing=parts[3],
        why=" | ".join(parts[4:]),
    )


def _parse_pipe_lines(script: str) -> list[ScriptBlock]:
    blocks: list[ScriptBlock] = []
    for raw in script.splitlines():
        line = raw.strip().strip("`")
        if not line or line.lower().startswith("timestamp"):
            continue
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        block = _parts_to_block(parts)
        if block:
            blocks.append(block)
    return blocks


def _split_on_timestamps(script: str) -> list[str]:
    """Split a mashed script into chunks that each start with a timestamp range."""
    text = script.strip()
    if not text:
        return []
    # Normalize newlines to spaces for mashed one-liners, but keep structure via timestamps
    collapsed = re.sub(r"[ \t]+", " ", text)
    collapsed = re.sub(r"\n{2,}", "\n", collapsed)
    # Prefer splitting on timestamp ranges even mid-line
    matches = list(_TS_BLOCK.finditer(collapsed))
    if len(matches) < 2:
        # Fall back to line chunks
        return [ln.strip() for ln in collapsed.splitlines() if ln.strip()]

    chunks: list[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(collapsed)
        chunk = collapsed[start:end].strip(" \n|;,-")
        if chunk:
            chunks.append(chunk)
    return chunks


def _chunk_to_block(chunk: str) -> ScriptBlock | None:
    chunk = chunk.strip()
    if not chunk:
        return None
    if "|" in chunk:
        return _parts_to_block([p.strip() for p in chunk.split("|")])

    # No pipes: timestamp + free text. Pull first timestamp, quoted speech, remainder as editing/why.
    m = _TS_BLOCK.match(chunk)
    ts = _clean_field(m.group("ts")) if m else ""
    rest = chunk[m.end() :].strip(" |:-") if m else chunk

    quoted = _QUOTED.findall(rest)
    if quoted:
        # findall returns tuples for alternation groups
        speech_parts = [a or b for a, b in quoted]
        speech = " ".join(speech_parts)
        # Remove quotes from rest for leftover directions
        leftover = _QUOTED.sub(" ", rest)
        leftover = _clean_field(leftover)
        shot = "MEDIUM shot"
        # Heuristic shot keywords at start of leftover
        for kw in ("CLOSE-UP", "MEDIUM", "WIDE", "B-ROLL", "SPLIT", "TEXT OVERLAY", "POV"):
            if leftover.upper().startswith(kw) or kw in leftover.upper()[:40]:
                shot = leftover.split(",")[0].split(".")[0].strip()[:48] or shot
                break
        return ScriptBlock(timestamp=ts, shot=shot, text=f'"{speech}"', editing=leftover[:160], why="")

    return ScriptBlock(timestamp=ts, shot="MEDIUM shot", text=rest, editing="", why="")


def _repair_swallowed_timestamps(blocks: list[ScriptBlock]) -> list[ScriptBlock]:
    """If a WHY/editing field embeds the next '0:12-0:20', split into new blocks."""
    repaired: list[ScriptBlock] = []
    for block in blocks:
        host_fields = [block.why, block.editing, block.text]
        combined = " ".join(f for f in host_fields if f)
        matches = list(_TS_BLOCK.finditer(combined))
        # Only split when a *second* timestamp appears (first may be this block's own ts)
        extra = [m for m in matches if _clean_field(m.group("ts")) != _clean_field(block.timestamp)]
        if not extra:
            repaired.append(block)
            continue

        # Truncate fields at first foreign timestamp
        first_extra_ts = extra[0].group("ts")

        def _cut(val: str, marker: str = first_extra_ts) -> str:
            if not val:
                return val
            idx = val.find(marker)
            if idx == -1:
                return val
            return val[:idx].strip(" |;,-")

        head = ScriptBlock(
            timestamp=block.timestamp,
            shot=block.shot,
            text=_cut(block.text),
            editing=_cut(block.editing),
            why=_cut(block.why),
        )
        repaired.append(head)

        # Remainder starting at first extra timestamp → re-parse as more blocks
        rem_start = combined.find(first_extra_ts)
        remainder = combined[rem_start:].strip()
        for chunk in _split_on_timestamps(remainder):
            b = _chunk_to_block(chunk)
            if b:
                repaired.append(b)
    return repaired


def _extract_spoken_fallback(script: str) -> list[str]:
    """Last resort: pull quoted phrases or non-meta lines as spoken copy."""
    quotes = [a or b for a, b in _QUOTED.findall(script)]
    if quotes:
        return quotes
    lines: list[str] = []
    for ln in script.splitlines():
        t = ln.strip()
        if not t or "|" in t:
            continue
        if _TS_BLOCK.match(t):
            continue
        if t.lower().startswith(("shot", "edit", "cut", "timestamp", "b-roll")):
            continue
        if len(t.split()) >= 4:
            lines.append(t)
    return lines


def normalize_script(script: str) -> NormalizedScript:
    """Return cleaned blocks + spoken narration from a raw LLM script string."""
    raw = (script or "").strip()
    out = NormalizedScript(raw_preview=raw[:240].replace("\n", " "))
    if not raw:
        return out

    blocks = _parse_pipe_lines(raw)
    repaired = False

    # Too few pipe lines for a long script → timestamp-chunk recovery
    if len(blocks) <= 1 and len(raw.split()) > 30:
        chunks = _split_on_timestamps(raw)
        recovered = [b for c in chunks if (b := _chunk_to_block(c))]
        if len(recovered) > len(blocks):
            blocks = recovered
            repaired = True

    # Split blocks that swallowed the next timestamp into the why/editing field
    before = len(blocks)
    blocks = _repair_swallowed_timestamps(blocks)
    if len(blocks) != before:
        repaired = True

    # Drop empty junk blocks
    blocks = [b for b in blocks if any([b.timestamp, b.text, b.editing, b.why])]

    spoken_lines: list[str] = []
    for b in blocks:
        s = b.spoken()
        if s:
            spoken_lines.append(s)

    if not spoken_lines:
        spoken_lines = _extract_spoken_fallback(raw)
        if spoken_lines:
            repaired = True
            if not blocks:
                # Synthesize minimal blocks so the shooting board isn't empty
                for i, line in enumerate(spoken_lines):
                    blocks.append(
                        ScriptBlock(
                            timestamp=f"0:{i * 8:02d}-0:{i * 8 + 7:02d}",
                            shot="MEDIUM shot",
                            text=f'"{line}"',
                            editing="Match creator cadence",
                            why="Recovered narration from unstructured model output",
                        )
                    )

    pipe_script = "\n".join(b.to_pipe_line() for b in blocks) if blocks else raw
    if pipe_script.strip() != raw.strip():
        repaired = True

    spoken = "\n\n".join(spoken_lines).strip()
    # Prefer spoken word count; fall back to raw if still empty
    wc = len(spoken.split()) if spoken else len(raw.split())

    out.blocks = blocks
    out.script = pipe_script
    out.spoken_copy = spoken
    out.spoken_word_count = wc
    out.was_repaired = repaired
    return out
