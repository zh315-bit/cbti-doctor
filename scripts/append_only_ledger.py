"""Byte-exact prefix pin validation for append-only ledgers."""
from __future__ import annotations

import hashlib


def prefix_matches(current_bytes: bytes, prefix_length: int, prefix_sha256: str) -> bool:
    return (isinstance(current_bytes, bytes) and isinstance(prefix_length, int)
            and 0 <= prefix_length <= len(current_bytes)
            and isinstance(prefix_sha256, str) and len(prefix_sha256) == 64
            and hashlib.sha256(current_bytes[:prefix_length]).hexdigest() == prefix_sha256)
