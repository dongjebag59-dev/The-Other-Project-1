"""간단한 인메모리 Rate Limiter (단일 프로세스 환경용)."""

import time
from collections import defaultdict

_store: dict[str, list[float]] = defaultdict(list)


def is_rate_limited(key: str, max_calls: int, window_seconds: int) -> bool:
    """주어진 key에 대해 window_seconds 내 max_calls 초과 시 True 반환."""
    now = time.time()
    cutoff = now - window_seconds
    timestamps = _store[key]
    _store[key] = [t for t in timestamps if t >= cutoff]
    if len(_store[key]) >= max_calls:
        return True
    _store[key].append(now)
    return False
