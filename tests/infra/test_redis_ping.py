"""Component 02 - Redis answers PING."""
import os
import pytest
import redis


@pytest.mark.integration
def test_redis_ping():
    url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    r = redis.from_url(url)
    assert r.ping() is True
