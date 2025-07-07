"""
Redis Configuration for DLMM Quote Engine
Centralized configuration for Redis connection and settings.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class RedisSettings:
    """Redis connection and operation settings"""
    
    # Connection settings
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    
    # Connection pool settings
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # Data update settings
    update_interval: int = 5  # seconds
    fallback_to_mock: bool = True
    
    # Cache settings
    graph_cache_ttl: int = 300  # 5 minutes
    pool_config_cache_ttl: int = 2  # 2 seconds
    max_graph_cache_size: int = 1000
    
    # Performance settings
    pipeline_batch_size: int = 100
    max_retries: int = 3
    backoff_factor: float = 1.0
    
    @classmethod
    def from_env(cls) -> 'RedisSettings':
        """Create settings from environment variables"""
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
            max_connections=int(os.getenv('REDIS_MAX_CONNECTIONS', '10')),
            socket_timeout=float(os.getenv('REDIS_SOCKET_TIMEOUT', '5.0')),
            socket_connect_timeout=float(os.getenv('REDIS_SOCKET_CONNECT_TIMEOUT', '5.0')),
            update_interval=int(os.getenv('REDIS_UPDATE_INTERVAL', '5')),
            fallback_to_mock=os.getenv('REDIS_FALLBACK_TO_MOCK', 'true').lower() == 'true',
            graph_cache_ttl=int(os.getenv('REDIS_GRAPH_CACHE_TTL', '300')),
            pool_config_cache_ttl=int(os.getenv('REDIS_POOL_CONFIG_CACHE_TTL', '2')),
            max_graph_cache_size=int(os.getenv('REDIS_MAX_GRAPH_CACHE_SIZE', '1000')),
            pipeline_batch_size=int(os.getenv('REDIS_PIPELINE_BATCH_SIZE', '100')),
            max_retries=int(os.getenv('REDIS_MAX_RETRIES', '3')),
            backoff_factor=float(os.getenv('REDIS_BACKOFF_FACTOR', '1.0'))
        )
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return {
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'password': self.password,
            'ssl': self.ssl,
            'max_connections': self.max_connections,
            'socket_timeout': self.socket_timeout,
            'socket_connect_timeout': self.socket_connect_timeout,
            'retry_on_timeout': self.retry_on_timeout,
            'health_check_interval': self.health_check_interval,
            'update_interval': self.update_interval,
            'fallback_to_mock': self.fallback_to_mock,
            'graph_cache_ttl': self.graph_cache_ttl,
            'pool_config_cache_ttl': self.pool_config_cache_ttl,
            'max_graph_cache_size': self.max_graph_cache_size,
            'pipeline_batch_size': self.pipeline_batch_size,
            'max_retries': self.max_retries,
            'backoff_factor': self.backoff_factor
        }


# Default settings
DEFAULT_REDIS_SETTINGS = RedisSettings()

# Environment-specific settings
def get_redis_settings(environment: str = None) -> RedisSettings:
    """
    Get Redis settings for specific environment
    
    Args:
        environment: Environment name ('development', 'staging', 'production')
        
    Returns:
        RedisSettings for the environment
    """
    
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development')
    
    if environment == 'production':
        return RedisSettings(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD'),
            ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true',
            max_connections=20,
            socket_timeout=10.0,
            socket_connect_timeout=10.0,
            update_interval=5,
            fallback_to_mock=False,  # No fallback in production
            graph_cache_ttl=300,
            pool_config_cache_ttl=2,
            max_graph_cache_size=2000,
            pipeline_batch_size=200,
            max_retries=5,
            backoff_factor=2.0
        )
    
    elif environment == 'staging':
        return RedisSettings(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '1')),  # Use different DB for staging
            password=os.getenv('REDIS_PASSWORD'),
            ssl=False,
            max_connections=15,
            socket_timeout=8.0,
            socket_connect_timeout=8.0,
            update_interval=5,
            fallback_to_mock=True,
            graph_cache_ttl=300,
            pool_config_cache_ttl=2,
            max_graph_cache_size=1500,
            pipeline_batch_size=150,
            max_retries=4,
            backoff_factor=1.5
        )
    
    else:  # development
        return RedisSettings.from_env()


# Cache invalidation events
CACHE_INVALIDATION_EVENTS = {
    "pool_added": "Clear all graph cache, rebuild paths",
    "pool_removed": "Clear all graph cache, rebuild paths", 
    "pool_status_changed": "Clear all graph cache, rebuild paths",
    "new_token_pair": "Clear all graph cache, rebuild paths",
    "bin_data_updated": "No cache invalidation needed (always fetch from Redis)",
    "pool_config_changed": "Clear pool config cache only"
}

# Redis key patterns
REDIS_KEY_PATTERNS = {
    "pool": "pool:{pool_id}",
    "bin": "bin:{pool_id}:{bin_id}",
    "bins_hash": "bins:{pool_id}",
    "metadata": "metadata",
    "token_index": "tokens:{token}",
    "pair_index": "pairs:{token_x}:{token_y}"
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "max_quote_latency_ms": 100,
    "max_redis_latency_ms": 10,
    "max_cache_invalidation_time_ms": 50,
    "min_cache_hit_rate_percent": 80,
    "max_memory_usage_mb": 1024
} 