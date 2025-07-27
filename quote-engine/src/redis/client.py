"""
Redis client wrapper for the quote engine.
Handles connection management and provides a clean interface for Redis operations.
"""

import redis
import logging
from typing import Dict, List, Optional, Any, Tuple
from .schemas import RedisSchema, PoolData, BinData, TokenGraphData
from ..utils.config import Config

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for quote engine operations"""
    
    def __init__(self, environment: str = "local"):
        """Initialize Redis client"""
        self.environment = environment
        self.redis_config = Config.get_redis_dict(environment)
        self.client = redis.Redis(**self.redis_config)
        self._test_connection()
    
    def _test_connection(self):
        """Test Redis connection"""
        try:
            self.client.ping()
            logger.info(f"✅ Redis connection established ({self.environment})")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def get_pool_data(self, pool_id: str) -> Optional[PoolData]:
        """Get pool data from Redis"""
        try:
            key = RedisSchema.get_pool_key(pool_id)
            data = self.client.hgetall(key)
            if data:
                return PoolData.from_redis_hash(data)
            return None
        except Exception as e:
            logger.error(f"Error getting pool data for {pool_id}: {e}")
            return None
    
    def get_bin_data(self, pool_id: str, bin_id: int) -> Optional[BinData]:
        """Get bin data from Redis"""
        try:
            key = RedisSchema.get_bin_key(pool_id, bin_id)
            data = self.client.hgetall(key)
            if data:
                return BinData.from_redis_hash(data)
            return None
        except Exception as e:
            logger.error(f"Error getting bin data for {pool_id}:{bin_id}: {e}")
            return None
    
    def get_bin_price(self, pool_id: str, bin_id: int) -> Optional[float]:
        """Get bin price from Redis ZSET"""
        try:
            key = RedisSchema.get_bin_price_zset_key(pool_id)
            price = self.client.zscore(key, bin_id)
            return float(price) if price is not None else None
        except Exception as e:
            logger.error(f"Error getting bin price for {pool_id}:{bin_id}: {e}")
            return None
    
    def get_bin_prices_in_range(self, pool_id: str, min_price: float, max_price: float) -> List[Tuple[int, float]]:
        """Get bin prices within a range from Redis ZSET"""
        try:
            key = RedisSchema.get_bin_price_zset_key(pool_id)
            bins = self.client.zrangebyscore(key, min_price, max_price, withscores=True)
            return [(int(bin_id), float(price)) for bin_id, price in bins]
        except Exception as e:
            logger.error(f"Error getting bin prices in range for {pool_id}: {e}")
            return []
    
    def get_bin_prices_reverse_range(self, pool_id: str, max_price: float, min_price: float) -> List[Tuple[int, float]]:
        """Get bin prices in reverse range from Redis ZSET"""
        try:
            key = RedisSchema.get_bin_price_zset_key(pool_id)
            bins = self.client.zrevrangebyscore(key, max_price, min_price, withscores=True)
            return [(int(bin_id), float(price)) for bin_id, price in bins]
        except Exception as e:
            logger.error(f"Error getting bin prices in reverse range for {pool_id}: {e}")
            return []
    
    def get_token_graph(self, version: str = "1") -> Optional[TokenGraphData]:
        """Get token graph from Redis"""
        try:
            key = RedisSchema.get_token_graph_key(version)
            data = self.client.hgetall(key)
            if data:
                return TokenGraphData.from_redis_hash(data, version)
            return None
        except Exception as e:
            logger.error(f"Error getting token graph: {e}")
            return None
    
    def get_all_pool_ids(self) -> List[str]:
        """Get all pool IDs from Redis"""
        try:
            pattern = "pool:*"
            keys = self.client.keys(pattern)
            pool_ids = []
            for key in keys:
                if isinstance(key, bytes):
                    key_str = key.decode('utf-8')
                else:
                    key_str = str(key)
                pool_id = key_str.split(':')[1]
                pool_ids.append(pool_id)
            return pool_ids
        except Exception as e:
            logger.error(f"Error getting pool IDs: {e}")
            return []
    
    def pipeline(self):
        """Get Redis pipeline for batch operations"""
        return self.client.pipeline()
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for Redis connection"""
        try:
            self.client.ping()
            
            info = self.client.info()
            
            return {
                "connected": True,
                "environment": self.environment,
                "ping_time_ms": 0,  # Simplified for now
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {
                "connected": False,
                "environment": self.environment,
                "error": str(e)
            } 