"""Rate Limiter — Redis(prod) / in-memory(dev) 자동 전환."""

import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

_store: dict[str, list[float]] = defaultdict(list)

_redis_client = None
_redis_initialized = False

_LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_calls = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= max_calls then
    return 1
end
redis.call('ZADD', key, now, tostring(now))
redis.call('EXPIRE', key, window * 2)
return 0
"""


def _get_redis_client():
    global _redis_client, _redis_initialized
    if _redis_initialized:
        return _redis_client

    _redis_initialized = True
    from app.config import settings

    if not settings.REDIS_URL:
        return None

    try:
        import redis.asyncio as aioredis

        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        logger.info("Redis rate limiter 활성화: %s", settings.REDIS_URL)
    except ImportError:
        logger.warning("redis 패키지 미설치 — in-memory rate limiter 사용")

    return _redis_client


async def is_rate_limited(key: str, max_calls: int, window_seconds: int) -> bool:
    """window_seconds 내 max_calls 초과 시 True를 반환합니다."""
    client = _get_redis_client()
    if client is not None:
        try:
            return await _redis_is_rate_limited(client, key, max_calls, window_seconds)
        except Exception:
            logger.warning("Redis rate limit 오류, in-memory로 대체합니다.", exc_info=True)
    return _memory_is_rate_limited(key, max_calls, window_seconds)


async def _redis_is_rate_limited(client, key: str, max_calls: int, window_seconds: int) -> bool:
    now = time.time()
    script = client.register_script(_LUA_SLIDING_WINDOW)
    result = await script(keys=[f"rl:{key}"], args=[now, window_seconds, max_calls])
    return bool(result)


def _memory_is_rate_limited(key: str, max_calls: int, window_seconds: int) -> bool:
    now = time.time()
    cutoff = now - window_seconds
    _store[key] = [t for t in _store[key] if t >= cutoff]
    if len(_store[key]) >= max_calls:
        return True
    _store[key].append(now)
    return False
