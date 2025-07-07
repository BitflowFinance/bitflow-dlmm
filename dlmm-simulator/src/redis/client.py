"""
Redis Client Wrapper for DLMM Quote Engine
Implements the same interface as MockRedisClient but connects to real Redis.
"""

import json
import time
import redis
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
from functools import wraps
import threading

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Redis connection configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30


def retry_on_failure(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator to retry Redis operations on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (redis.ConnectionError, redis.TimeoutError, redis.RedisError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        sleep_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Redis operation failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"Redis operation failed after {max_retries} attempts: {e}")
                        raise last_exception
            return None
        return wrapper
    return decorator


class RedisClient:
    """
    Redis client wrapper that implements the same interface as MockRedisClient
    but connects to a real Redis instance.
    """
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis = None
        self.connection_pool = None
        self.cache_lock = threading.Lock()
        self.bin_cache = {}  # Cache for bin data
        self.pool_cache = {}  # Cache for pool data
        self._connect()
        
    def _connect(self):
        """Establish connection to Redis"""
        try:
            # Create connection parameters without SSL first
            connection_params = {
                'host': self.config.host,
                'port': self.config.port,
                'db': self.config.db,
                'password': self.config.password,
                'max_connections': self.config.max_connections,
                'socket_timeout': self.config.socket_timeout,
                'socket_connect_timeout': self.config.socket_connect_timeout,
                'retry_on_timeout': self.config.retry_on_timeout,
                'health_check_interval': self.config.health_check_interval
            }
            
            # Only add SSL if explicitly enabled and supported
            if self.config.ssl:
                try:
                    connection_params['ssl'] = True
                    connection_params['ssl_cert_reqs'] = None  # Disable certificate verification for development
                except Exception as ssl_error:
                    logger.warning(f"SSL not supported, falling back to non-SSL: {ssl_error}")
            
            self.connection_pool = redis.ConnectionPool(**connection_params)
            
            self.redis = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            self.redis.ping()
            logger.info(f"Successfully connected to Redis at {self.config.host}:{self.config.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    @retry_on_failure()
    def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis
        
        Args:
            key: Redis key
            
        Returns:
            JSON string value or None if key doesn't exist
        """
        try:
            value = self.redis.get(key)
            if value is not None:
                # Redis returns bytes, decode to string
                return value.decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            raise
    
    @retry_on_failure()
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set value in Redis
        
        Args:
            key: Redis key
            value: JSON string value
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful
        """
        try:
            if ttl:
                return self.redis.setex(key, ttl, value)
            else:
                return self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            raise
    
    @retry_on_failure()
    def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Redis key
            
        Returns:
            True if key exists
        """
        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            logger.error(f"Error checking existence of key {key}: {e}")
            raise
    
    @retry_on_failure()
    def keys(self, pattern: str) -> List[str]:
        """
        Get keys matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., "pool:*")
            
        Returns:
            List of matching keys
        """
        try:
            keys = self.redis.keys(pattern)
            # Decode bytes to strings
            return [key.decode('utf-8') for key in keys]
        except Exception as e:
            logger.error(f"Error getting keys with pattern {pattern}: {e}")
            raise
    
    @retry_on_failure()
    def hget(self, key: str, field: str) -> Optional[str]:
        """
        Get field from Redis hash
        
        Args:
            key: Redis hash key
            field: Hash field name
            
        Returns:
            Field value as string or None
        """
        try:
            value = self.redis.hget(key, field)
            if value is not None:
                return value.decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Error getting hash field {field} from {key}: {e}")
            raise
    
    @retry_on_failure()
    def hgetall(self, key: str) -> Dict[str, str]:
        """
        Get all fields from Redis hash
        
        Args:
            key: Redis hash key
            
        Returns:
            Dictionary of field-value pairs
        """
        try:
            hash_data = self.redis.hgetall(key)
            # Decode bytes to strings
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in hash_data.items()}
        except Exception as e:
            logger.error(f"Error getting all hash fields from {key}: {e}")
            raise
    
    @retry_on_failure()
    def hset(self, key: str, field: str, value: str) -> bool:
        """
        Set field in Redis hash
        
        Args:
            key: Redis hash key
            field: Hash field name
            value: Field value
            
        Returns:
            True if successful
        """
        try:
            return bool(self.redis.hset(key, field, value))
        except Exception as e:
            logger.error(f"Error setting hash field {field} in {key}: {e}")
            raise
    
    @retry_on_failure()
    def hmset(self, key: str, mapping: Dict[str, str]) -> bool:
        """
        Set multiple fields in Redis hash
        
        Args:
            key: Redis hash key
            mapping: Dictionary of field-value pairs
            
        Returns:
            True if successful
        """
        try:
            return self.redis.hmset(key, mapping)
        except Exception as e:
            logger.error(f"Error setting multiple hash fields in {key}: {e}")
            raise
    
    @retry_on_failure()
    def delete(self, key: str) -> bool:
        """
        Delete key from Redis
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted
        """
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            raise
    
    @retry_on_failure()
    def ping(self) -> bool:
        """
        Ping Redis server
        
        Returns:
            True if Redis is responding
        """
        try:
            return self.redis.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connection
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            start_time = time.time()
            ping_success = self.ping()
            ping_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Get basic Redis info
            info = self.redis.info()
            
            health_status = {
                "connected": ping_success,
                "ping_time_ms": ping_time,
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                "last_check": time.time()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "connected": False,
                "error": str(e),
                "last_check": time.time()
            }
    
    def close(self):
        """Close Redis connection"""
        if self.redis:
            self.redis.close()
        if self.connection_pool:
            self.connection_pool.disconnect()
        logger.info("Redis connection closed")


class MockRedisClientFallback:
    """
    Fallback to MockRedisClient when Redis is unavailable
    """
    
    def __init__(self):
        from ..quote_engine import MockRedisClient
        self.mock_client = MockRedisClient()
        logger.warning("Using MockRedisClient fallback - Redis connection failed")
    
    def get(self, key: str) -> Optional[str]:
        return self.mock_client.get(key)
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        return self.mock_client.set(key, value) if hasattr(self.mock_client, 'set') else True
    
    def exists(self, key: str) -> bool:
        return self.mock_client.exists(key) if hasattr(self.mock_client, 'exists') else True
    
    def keys(self, pattern: str) -> List[str]:
        return self.mock_client.keys(pattern)
    
    def hget(self, key: str, field: str) -> Optional[str]:
        # Mock implementation for hash operations
        data = self.mock_client.get(key)
        if data:
            try:
                parsed = json.loads(data)
                return str(parsed.get(field, ""))
            except:
                return None
        return None
    
    def hgetall(self, key: str) -> Dict[str, str]:
        # Mock implementation for hash operations
        data = self.mock_client.get(key)
        if data:
            try:
                parsed = json.loads(data)
                return {str(k): str(v) for k, v in parsed.items()}
            except:
                return {}
        return {}
    
    def hset(self, key: str, field: str, value: str) -> bool:
        return True  # Mock implementation
    
    def hmset(self, key: str, mapping: Dict[str, str]) -> bool:
        return True  # Mock implementation
    
    def delete(self, key: str) -> bool:
        return True  # Mock implementation
    
    def ping(self) -> bool:
        return True  # Mock implementation
    
    def health_check(self) -> Dict[str, Any]:
        return {
            "connected": True,
            "fallback": True,
            "mock_client": True,
            "last_check": time.time()
        }
    
    def close(self):
        pass  # No cleanup needed for mock client


def create_redis_client(config: RedisConfig, fallback_to_mock: bool = True):
    """
    Create Redis client with optional fallback to mock client
    
    Args:
        config: Redis configuration
        fallback_to_mock: Whether to fallback to MockRedisClient if Redis is unavailable
        
    Returns:
        RedisClient or MockRedisClientFallback
    """
    try:
        return RedisClient(config)
    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        if fallback_to_mock:
            logger.info("Falling back to MockRedisClient")
            return MockRedisClientFallback()
        else:
            raise 