import json
import redis
from typing import Any, Optional
from app.core.config import settings


class CacheManager:
    """Redis cache manager for storing scraping results."""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data by key."""
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                result = json.loads(cached_data)
                # Mark as cached
                if isinstance(result, dict) and 'metadata' in result:
                    result['metadata']['cached'] = True
                return result
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cached data with TTL."""
        try:
            serialized_value = json.dumps(value, default=str)
            return self.redis_client.setex(key, ttl, serialized_value)
        except (redis.RedisError, TypeError) as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cached data by key."""
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError as e:
            print(f"Cache delete error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except redis.RedisError as e:
            print(f"Cache invalidate error: {e}")
            return 0
    
    def invalidate_user_cache(self, username: str) -> int:
        """Invalidate all cached data for a specific user."""
        patterns = [
            f"cache:following_user:*{username}*",
            f"cache:followers_user:*{username}*",
            f"cache:timeline_tweet:*{username}*"
        ]
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.invalidate_pattern(pattern)
        return total_deleted
    
    def health_check(self) -> bool:
        """Check if Redis is accessible."""
        try:
            self.redis_client.ping()
            return True
        except redis.RedisError:
            return False


# Create singleton instance
cache_manager = CacheManager()
