import os
import redis

from datetime import timedelta


redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

# --- Constants ---
TOKEN_KEY = "hubspot:auth_token"
ID_MAP_PREFIX = "hubspot:map:"  # e.g., hubspot:map:customer:1 -> 12345 (hubspot_id)
RATE_LIMIT_PREFIX = "hubspot:ratelimit:"


def cache_id_mapping(local_type: str, local_id: str, hubspot_id: str):
    """
    Cache mapping between Local DB ID and HubSpot ID.
    local_type: 'customer' or 'ticket'
    """
    key = f"{ID_MAP_PREFIX}{local_type}:{local_id}"
    # Store indefinitely or for a long time since these don't usually change
    redis_client.set(key, hubspot_id)

    # Reverse mapping (Optional: useful if webhooks send data back from HubSpot)
    reverse_key = f"{ID_MAP_PREFIX}{local_type}:reverse:{hubspot_id}"
    redis_client.set(reverse_key, local_id)


def get_cached_hubspot_id(local_type: str, local_id: str):
    """Retrieve HubSpot ID from cache"""
    key = f"{ID_MAP_PREFIX}{local_type}:{local_id}"
    return redis_client.get(key)


def check_rate_limit(limit: int = 10, window_seconds: int = 10):
    """
    Simple sliding window rate limiter.
    Returns True if allowed, False if limit exceeded.
    """
    key = f"{RATE_LIMIT_PREFIX}global"
    current = redis_client.incr(key)

    if current == 1:
        redis_client.expire(key, window_seconds)

    if current > limit:
        return False
    return True


def get_crm_token():
    """Retrieve auth token from Redis or fallback to Env"""
    # Try to get dynamic token from Redis
    token = redis_client.get(TOKEN_KEY)
    if token:
        return token

    return os.getenv("HUBSPOT_API_KEY")


def set_crm_token(token: str, expiry_seconds: int = 1800):
    """Store auth token with expiration"""
    redis_client.setex(TOKEN_KEY, timedelta(seconds=expiry_seconds), token)

