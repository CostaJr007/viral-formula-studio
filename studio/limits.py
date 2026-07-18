"""In-memory rate limiter — lightweight, no external dependencies.

Two limits per IP (rolling 1-hour window):
  1. Max 3 distinct creator analyses  (POST /api/ingest)
  2. Max 3 dossier/PDF exports per creator  (POST /api/dossier)

Hooks and copy endpoints are unconstrained — they're transient steps
within the flow and don't hit external LLMs independently in practice.
"""

from __future__ import annotations

import time
from collections import defaultdict

WINDOW_S = 3600  # 1 hour
MAX_CREATORS = 3
MAX_DOSSIERS_PER_CREATOR = 3


class RateLimiter:
    def __init__(self) -> None:
        # ip -> set of creator names analyzed
        self._creators: dict[str, set[str]] = defaultdict(set)
        # ip -> {creator -> [timestamps]}
        self._dossiers: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    def _purge_dossiers(self, ip: str, creator: str) -> None:
        cutoff = time.time() - WINDOW_S
        self._dossiers[ip][creator] = [
            t for t in self._dossiers[ip][creator] if t > cutoff
        ]

    # --- ingest ---

    def check_ingest(self, ip: str, creator: str) -> bool:
        """Return True if this creator can be analyzed (≤3 unique creators per IP)."""
        creator = creator.lower()
        if creator in self._creators[ip]:
            return True  # already analyzed — re-ingest same creator is fine
        if len(self._creators[ip]) >= MAX_CREATORS:
            return False
        self._creators[ip].add(creator)
        return True

    def remaining_creators(self, ip: str) -> int:
        return max(0, MAX_CREATORS - len(self._creators[ip]))

    # --- dossier ---

    def check_dossier(self, ip: str, creator: str) -> bool:
        """Return True if a dossier can be exported for this creator (≤3 per creator)."""
        creator = creator.lower()
        self._purge_dossiers(ip, creator)
        if len(self._dossiers[ip][creator]) >= MAX_DOSSIERS_PER_CREATOR:
            return False
        self._dossiers[ip][creator].append(time.time())
        return True

    def remaining_dossiers(self, ip: str, creator: str) -> int:
        creator = creator.lower()
        self._purge_dossiers(ip, creator)
        return max(0, MAX_DOSSIERS_PER_CREATOR - len(self._dossiers[ip][creator]))


# Singleton
limiter = RateLimiter()
