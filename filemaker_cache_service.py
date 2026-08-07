#!/usr/bin/env python3
"""
FileMaker API Cache Service using Redis
Optimizes slow FileMaker API calls with intelligent caching
"""

import redis
import json
import hashlib
from datetime import datetime, timedelta
from functools import wraps
import logging

class FileMakerCacheService:
    def __init__(self, redis_host=None, redis_port=None, redis_db=0):
        """
        Initialize FileMaker cache service
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port  
            redis_db: Redis database number
        """
        import os
        
        # Use environment variables or defaults
        if redis_host is None:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
        if redis_port is None:
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.cache_enabled = True
            print(f"[CACHE] Redis connected successfully")
        except Exception as e:
            print(f"[CACHE] Redis connection failed: {e}, caching disabled")
            self.redis_client = None
            self.cache_enabled = False
    
    def _generate_cache_key(self, prefix, *args, **kwargs):
        """Generate unique cache key from function arguments"""
        # Create a string from all arguments
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"fm_cache:{prefix}:{key_hash}"
    
    def cache_result(self, prefix="default", expire_seconds=300):
        """
        Decorator to cache function results
        
        Args:
            prefix: Cache key prefix
            expire_seconds: Cache expiration time (default 5 minutes)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # If cache disabled, call function directly
                if not self.cache_enabled:
                    return func(*args, **kwargs)
                
                # Generate cache key
                cache_key = self._generate_cache_key(prefix, *args, **kwargs)
                
                try:
                    # Try to get from cache
                    cached_result = self.redis_client.get(cache_key)
                    if cached_result:
                        print(f"[CACHE HIT] {prefix} - {cache_key[:20]}...")
                        return json.loads(cached_result)
                    
                    # Cache miss - call original function
                    print(f"[CACHE MISS] {prefix} - calling FileMaker API...")
                    result = func(*args, **kwargs)
                    
                    # Cache the result
                    if result is not None:
                        self.redis_client.setex(
                            cache_key, 
                            expire_seconds, 
                            json.dumps(result, default=str)
                        )
                        print(f"[CACHE STORE] {prefix} - cached for {expire_seconds}s")
                    
                    return result
                    
                except Exception as e:
                    print(f"[CACHE ERROR] {e} - falling back to direct call")
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def invalidate_pattern(self, pattern):
        """Invalidate cache entries matching pattern"""
        if not self.cache_enabled:
            return
        
        try:
            keys = self.redis_client.keys(f"fm_cache:{pattern}:*")
            if keys:
                self.redis_client.delete(*keys)
                print(f"[CACHE INVALIDATE] Deleted {len(keys)} entries for pattern: {pattern}")
        except Exception as e:
            print(f"[CACHE ERROR] Invalidation failed: {e}")
    
    def get_cache_stats(self):
        """Get cache statistics"""
        if not self.cache_enabled:
            return {"status": "disabled"}
        
        try:
            info = self.redis_client.info()
            keys = self.redis_client.keys("fm_cache:*")
            return {
                "status": "enabled",
                "total_keys": len(keys),
                "memory_used": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def clear_all_cache(self):
        """Clear all FileMaker cache"""
        if not self.cache_enabled:
            return
        
        try:
            keys = self.redis_client.keys("fm_cache:*")
            if keys:
                self.redis_client.delete(*keys)
                print(f"[CACHE CLEAR] Deleted {len(keys)} cache entries")
            return len(keys)
        except Exception as e:
            print(f"[CACHE ERROR] Clear failed: {e}")
            return 0

# Global cache service instance
cache_service = FileMakerCacheService()

# Convenience decorators with different expiration times
def cache_short(func):
    """Cache for 2 minutes - for frequently changing data"""
    return cache_service.cache_result("short", 120)(func)

def cache_medium(func):
    """Cache for 10 minutes - for moderately changing data"""
    return cache_service.cache_result("medium", 600)(func)

def cache_long(func):
    """Cache for 1 hour - for rarely changing data"""
    return cache_service.cache_result("long", 3600)(func)

def cache_search(func):
    """Cache for 24 hours - for search results (daily update system)"""
    return cache_service.cache_result("search", 86400)(func)

def cache_metadata(func):
    """Cache for 30 minutes - for metadata like categories, artists"""
    return cache_service.cache_result("metadata", 1800)(func)

# Example usage:
"""
from filemaker_cache_service import cache_search, cache_metadata

@cache_search
def search_artworks(query):
    # This will be cached for 5 minutes
    return filemaker_api.search(query)

@cache_metadata  
def get_all_artists():
    # This will be cached for 30 minutes
    return filemaker_api.get_artists()
"""