"""Shared filters so we never treat error pages / URLs / API junk as spoken copy.

Signature n-grams and style fallbacks must come from speech-like text only.
Words like https, ibm, quota, cloud, status usually mean the "transcript"
was an error blob (watsonx/quota/HTML), not the creator talking.
"""

from __future__ import annotations

import re

# URL / infra / API / platform noise — never "signature phrases"
JUNK_TOKENS: set[str] = {
    "http",
    "https",
    "www",
    "com",
    "org",
    "net",
    "io",
    "html",
    "htm",
    "json",
    "xml",
    "api",
    "url",
    "uri",
    "ibm",
    "cloud",
    "watsonx",
    "granite",
    "quota",
    "status",
    "error",
    "errors",
    "token",
    "bearer",
    "null",
    "undefined",
    "true",
    "false",
    "chat",
    "code",
    "request",
    "response",
    "server",
    "client",
    "timeout",
    "unauthorized",
    "forbidden",
    "exception",
    "traceback",
    "stack",
    "debug",
    "info",
    "warn",
    "warning",
    "failed",
    "failure",
    "success",
    "localhost",
    "ffmpeg",
    "ytdlp",
    "whisper",
    "tavily",
    "openai",
    "groq",
    "mp4",
    "webm",
    "vtt",
    "srt",
    "app",
    "domain",
    "south",
    "engine",
    "container",
    "docker",
    "httpstatus",
}

_STOPWORDS_EN: set[str] = {
    "the",
    "and",
    "for",
    "you",
    "your",
    "with",
    "that",
    "this",
    "from",
    "have",
    "has",
    "was",
    "were",
    "are",
    "is",
    "been",
    "being",
    "will",
    "would",
    "could",
    "should",
    "can",
    "just",
    "like",
    "what",
    "when",
    "where",
    "which",
    "who",
    "how",
    "why",
    "not",
    "but",
    "all",
    "any",
    "out",
    "our",
    "they",
    "them",
    "their",
    "there",
    "here",
    "then",
    "than",
    "into",
    "also",
    "about",
    "more",
    "some",
    "very",
    "really",
    "get",
    "got",
    "dont",
    "does",
    "did",
    "its",
    "it's",
    "im",
    "ive",
    "youre",
    "we",
    "us",
    "my",
    "me",
    "he",
    "she",
    "his",
    "her",
    "him",
    "as",
    "at",
    "by",
    "of",
    "on",
    "in",
    "to",
    "a",
    "an",
    "or",
    "if",
    "so",
    "up",
    "no",
    "yes",
}

_STOPWORDS_PT: set[str] = {
    "a",
    "o",
    "e",
    "é",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "um",
    "uma",
    "que",
    "pra",
    "para",
    "com",
    "se",
    "eu",
    "você",
    "ele",
    "ela",
    "isso",
    "esse",
    "essa",
    "isto",
    "ao",
    "aos",
    "por",
    "mais",
    "muito",
    "como",
    "mas",
    "ou",
    "quando",
    "já",
    "também",
    "só",
    "tem",
    "ser",
    "estar",
    "foi",
    "são",
    "era",
    "vai",
    "vou",
    "meu",
    "minha",
    "seu",
    "sua",
    "não",
    "sim",
    "me",
    "te",
}

STOPWORDS: set[str] = _STOPWORDS_EN | _STOPWORDS_PT | JUNK_TOKENS

_ERROR_MARKERS = (
    "error message",
    "failed request",
    "request failed",
    "rate limit",
    "unauthorized",
    "traceback",
    "exception",
    "http error",
    "could not retrieve",
    "transcription unavailable",
    "access denied",
    "quota",
    "exceeded",
    "watsonx",
    "api key",
    "apikey",
    "status code",
    "cloud.ibm",
    "ml.cloud",
    "https://",
    "http://",
    "application/json",
    "bearer ",
)


def strip_urls(text: str) -> str:
    text = re.sub(r"https?://\S+", " ", text or "")
    text = re.sub(r"www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    return text


def is_error_blob(text: str) -> bool:
    """True when text looks like an API/HTML error, not spoken language."""
    raw = (text or "").strip()
    if not raw:
        return True
    lower = raw.lower()
    words = raw.split()
    marker_hits = sum(1 for m in _ERROR_MARKERS if m in lower)
    if marker_hits >= 1 and len(words) < 120:
        return True
    if marker_hits >= 2:
        return True
    # Heavy URL / domain density
    url_like = len(re.findall(r"https?://|www\.|\.com|\.cloud", lower))
    if url_like >= 2 and len(words) < 150:
        return True
    # Token junk ratio
    tokens = re.findall(r"[a-z0-9]+", lower)
    if not tokens:
        return True
    junk = sum(1 for t in tokens if t in JUNK_TOKENS or t.isdigit())
    if junk / max(len(tokens), 1) >= 0.35 and len(tokens) < 80:
        return True
    return False


def spoken_tokens(text: str, *, drop_stopwords: bool = True) -> list[str]:
    """Tokenize speech-like words (no URLs / infra junk).

    drop_stopwords=True → content terms only (style fallback unigrams).
    drop_stopwords=False → keep function words so n-grams like "final do dia" survive.
    """
    cleaned = strip_urls(text or "")
    words = re.findall(r"[a-záàâãéêíóôõúç']{2,}", cleaned.lower())
    out: list[str] = []
    for w in words:
        w = w.strip("'")
        if len(w) < 2:
            continue
        if w in JUNK_TOKENS:
            continue
        if drop_stopwords and w in STOPWORDS:
            continue
        if re.fullmatch(r"[0-9]+", w):
            continue
        out.append(w)
    return out


def is_speech_like(text: str, *, min_tokens: int = 8) -> bool:
    if is_error_blob(text):
        return False
    return len(spoken_tokens(text)) >= min_tokens


def filter_expression(expr: str) -> bool:
    """Keep multi-word human phrases; drop junk unigrams/ngrams."""
    if not expr or not str(expr).strip():
        return False
    raw = str(expr).strip().lower()
    if is_error_blob(raw):
        return False
    parts = re.findall(r"[a-záàâãéêíóôõúç']{2,}", raw)
    if not parts:
        return False
    if any(p in JUNK_TOKENS for p in parts):
        return False
    # Reject pure stopword phrases
    content = [p for p in parts if p not in STOPWORDS]
    if not content:
        return False
    # Single-token phrases must be somewhat meaningful length
    if len(content) == 1 and len(content[0]) < 5:
        return False
    return True


def top_content_phrases(texts: list[str], *, top_k: int = 8) -> list[str]:
    """Simple content unigrams from clean speech only (fallback expressions)."""
    from collections import Counter

    counter: Counter[str] = Counter()
    for t in texts:
        if not is_speech_like(t, min_tokens=4):
            # still try tokens if not full error blob
            if is_error_blob(t):
                continue
        for w in spoken_tokens(t):
            if len(w) >= 4:
                counter[w] += 1
    return [w for w, c in counter.most_common(top_k * 2) if c >= 1 and filter_expression(w)][:top_k]
