"""
Cache abstraction for persistent state management.

This module provides a simple interface for storing review state across
PR cycles. Currently supports in-memory and file-based storage, with
Redis support planned for future releases.
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import json
from pathlib import Path
from datetime import datetime
import os
import hashlib


def compute_cache_key(pr_number: int, file_path: str = None) -> str:
    """Compute a unique cache key for storing PR analysis results."""
    if file_path:
        key_data = f"pr_{pr_number}_file_{file_path}"
    else:
        key_data = f"pr_{pr_number}"
    return hashlib.md5(key_data.encode()).hexdigest()


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a value in the cache with optional expiration."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass


class InMemoryCache(CacheBackend):
    """Simple in-memory cache for development and testing."""
    
    def __init__(self):
        """Initialize the in-memory cache."""
        self.store: Dict[str, Any] = {}
        self.expiry: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value, checking expiration first."""
        if key not in self.store:
            return None
        
        # Check expiration
        if key in self.expiry:
            if datetime.utcnow() > self.expiry[key]:
                del self.store[key]
                del self.expiry[key]
                return None
        
        return self.store[key]
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a value with optional TTL (in seconds)."""
        self.store[key] = value
        
        if ex:
            from datetime import timedelta
            self.expiry[key] = datetime.utcnow() + timedelta(seconds=ex)
        
        return True
    
    def delete(self, key: str) -> bool:
        """Delete a key."""
        if key in self.store:
            del self.store[key]
            if key in self.expiry:
                del self.expiry[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        return self.get(key) is not None


class FileCache(CacheBackend):
    """File-based cache for persistence across restarts."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize file cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_filepath(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Sanitize the key to create a valid filename
        safe_key = key.replace(":", "_").replace("/", "_")
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from file."""
        filepath = self._get_filepath(key)
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check expiration
            if 'expiry' in data:
                expiry = datetime.fromisoformat(data['expiry'])
                if datetime.utcnow() > expiry:
                    filepath.unlink()
                    return None
            
            return data['value']
        except Exception as e:
            print(f"Error reading cache file {filepath}: {e}")
            return None
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a value in a file."""
        filepath = self._get_filepath(key)
        
        try:
            data = {'value': value}
            
            if ex:
                from datetime import timedelta
                expiry = datetime.utcnow() + timedelta(seconds=ex)
                data['expiry'] = expiry.isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(data, f, default=str)
            
            return True
        except Exception as e:
            print(f"Error writing cache file {filepath}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a cache file."""
        filepath = self._get_filepath(key)
        
        if filepath.exists():
            try:
                filepath.unlink()
                return True
            except Exception as e:
                print(f"Error deleting cache file {filepath}: {e}")
                return False
        
        return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        return self.get(key) is not None


class RedisCache(CacheBackend):
    """Redis-based cache for production deployments (requires redis package)."""
    
    def __init__(self, redis_client=None, host: str = "localhost", port: int = 6379):
        """
        Initialize Redis cache.
        
        Args:
            redis_client: Existing redis.Redis client (optional)
            host: Redis server host
            port: Redis server port
        """
        if redis_client:
            self.client = redis_client
        else:
            try:
                import redis
                self.client = redis.Redis(host=host, port=port, decode_responses=True)
                # Test connection
                self.client.ping()
            except ImportError:
                raise ImportError("redis package required for RedisCache")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Redis: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a value in Redis with optional TTL."""
        try:
            # Serialize value
            if isinstance(value, str):
                serialized = value
            else:
                serialized = json.dumps(value, default=str)
            
            self.client.set(key, serialized, ex=ex)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False


def get_cache_backend(backend_type: str = None) -> CacheBackend:
    """
    Factory function to get the appropriate cache backend.
    
    Args:
        backend_type: Type of backend ('memory', 'file', 'redis', or None for auto)
    
    Returns:
        Configured cache backend instance
    """
    if backend_type is None:
        # Auto-detect based on environment
        backend_type = os.getenv("CACHE_BACKEND", "memory")
    
    backend_type = backend_type.lower()
    
    if backend_type == "redis":
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        return RedisCache(host=redis_host, port=redis_port)
    elif backend_type == "file":
        cache_dir = os.getenv("CACHE_DIR", ".cache")
        return FileCache(cache_dir=cache_dir)
    else:  # memory (default)
        return InMemoryCache()
