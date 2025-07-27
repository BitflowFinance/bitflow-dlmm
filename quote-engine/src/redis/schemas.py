"""
Data Schemas for Redis Integration
Defines the structure and validation for pool and bin data stored in Redis.
"""

import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PoolData:
    """Pool data structure for Redis storage - Updated Schema"""
    pool_id: str
    token0: str  # Changed from token_x
    token1: str  # Changed from token_y
    bin_step: float  # Changed from int to float
    active_bin: int  # Changed from active_bin_id
    active: bool  # Changed from status string
    x_protocol_fee: int  # New field
    x_provider_fee: int  # New field
    x_variable_fee: int  # New field
    y_protocol_fee: int  # New field
    y_provider_fee: int  # New field
    y_variable_fee: int  # New field
    
    def to_redis_hash(self) -> Dict[str, str]:
        """Convert to Redis hash format"""
        return {
            "pool_id": self.pool_id,
            "token0": self.token0,
            "token1": self.token1,
            "bin_step": str(self.bin_step),
            "active_bin": str(self.active_bin),
            "active": str(self.active).lower(),
            "x_protocol_fee": str(self.x_protocol_fee),
            "x_provider_fee": str(self.x_provider_fee),
            "x_variable_fee": str(self.x_variable_fee),
            "y_protocol_fee": str(self.y_protocol_fee),
            "y_provider_fee": str(self.y_provider_fee),
            "y_variable_fee": str(self.y_variable_fee)
        }
    
    @classmethod
    def from_redis_hash(cls, data: Dict[str, str]) -> 'PoolData':
        """Create PoolData from Redis hash"""
        return cls(
            pool_id=data["pool_id"],
            token0=data["token0"],
            token1=data["token1"],
            bin_step=float(data["bin_step"]),
            active_bin=int(data["active_bin"]),
            active=data["active"].lower() == "true",
            x_protocol_fee=int(data["x_protocol_fee"]),
            x_provider_fee=int(data["x_provider_fee"]),
            x_variable_fee=int(data["x_variable_fee"]),
            y_protocol_fee=int(data["y_protocol_fee"]),
            y_provider_fee=int(data["y_provider_fee"]),
            y_variable_fee=int(data["y_variable_fee"])
        )
    
    def validate(self) -> bool:
        """Validate pool data"""
        try:
            assert self.pool_id and len(self.pool_id) > 0
            assert self.token0 and len(self.token0) > 0
            assert self.token1 and len(self.token1) > 0
            assert self.bin_step > 0
            assert self.active_bin >= 0
            assert isinstance(self.active, bool)
            assert self.x_protocol_fee >= 0
            assert self.x_provider_fee >= 0
            assert self.x_variable_fee >= 0
            assert self.y_protocol_fee >= 0
            assert self.y_provider_fee >= 0
            assert self.y_variable_fee >= 0
            return True
        except Exception as e:
            logger.error(f"Pool data validation failed: {e}")
            return False


@dataclass
class BinData:
    """Bin data structure for Redis storage - Updated Schema"""
    pool_id: str
    bin_id: int
    reserve_x: int  # Changed from x_amount (float to int)
    reserve_y: int  # Changed from y_amount (float to int)
    liquidity: int  # Changed from total_liquidity (float to int)
    
    def to_redis_hash(self) -> Dict[str, str]:
        """Convert to Redis hash format"""
        return {
            "pool_id": self.pool_id,
            "bin_id": str(self.bin_id),
            "reserve_x": str(self.reserve_x),
            "reserve_y": str(self.reserve_y),
            "liquidity": str(self.liquidity)
        }
    
    @classmethod
    def from_redis_hash(cls, data: Dict[str, str]) -> 'BinData':
        """Create BinData from Redis hash"""
        return cls(
            pool_id=data["pool_id"],
            bin_id=int(data["bin_id"]),
            reserve_x=int(data["reserve_x"]),
            reserve_y=int(data["reserve_y"]),
            liquidity=int(data["liquidity"])
        )
    
    def validate(self) -> bool:
        """Validate bin data"""
        try:
            assert self.pool_id and len(self.pool_id) > 0
            assert self.bin_id >= 0
            assert self.reserve_x >= 0
            assert self.reserve_y >= 0
            assert self.liquidity >= 0
            return True
        except Exception as e:
            logger.error(f"Bin data validation failed: {e}")
            return False


@dataclass
class TokenGraphData:
    """Token graph data structure for Redis storage"""
    version: str
    token_pairs: Dict[str, List[str]]  # "tokenA->tokenB" -> ["pool_id1", "pool_id2"]
    
    def to_redis_hash(self) -> Dict[str, str]:
        """Convert to Redis hash format"""
        result = {}
        for pair, pools in self.token_pairs.items():
            result[pair] = json.dumps(pools)
        return result
    
    @classmethod
    def from_redis_hash(cls, data: Dict[str, str], version: str) -> 'TokenGraphData':
        """Create TokenGraphData from Redis hash"""
        token_pairs = {}
        for key, value in data.items():
            if key != "version":
                token_pairs[key] = json.loads(value)
        return cls(version=version, token_pairs=token_pairs)
    
    def validate(self) -> bool:
        """Validate token graph data"""
        try:
            assert self.version and len(self.version) > 0
            assert isinstance(self.token_pairs, dict)
            for pair, pools in self.token_pairs.items():
                assert "->" in pair, f"Invalid pair format: {pair}"
                assert isinstance(pools, list)
                for pool_id in pools:
                    assert isinstance(pool_id, str) and len(pool_id) > 0
            return True
        except Exception as e:
            logger.error(f"Token graph data validation failed: {e}")
            return False


class RedisSchema:
    """Redis schema definitions and key patterns - Updated Schema"""
    
    # Key patterns
    POOL_KEY_PATTERN = "pool:{pool_id}"
    BIN_KEY_PATTERN = "bin:{pool_id}:{bin_id}"
    BIN_PRICE_ZSET_PATTERN = "pool:{pool_id}:bins"  # New ZSET for bin prices
    TOKEN_GRAPH_KEY_PATTERN = "token_graph:{version}"  # New token graph key
    
    @staticmethod
    def get_pool_key(pool_id: str) -> str:
        """Get Redis key for pool data"""
        return f"pool:{pool_id}"
    
    @staticmethod
    def get_bin_key(pool_id: str, bin_id: int) -> str:
        """Get Redis key for individual bin data"""
        return f"bin:{pool_id}:{bin_id}"
    
    @staticmethod
    def get_bin_price_zset_key(pool_id: str) -> str:
        """Get Redis key for bin price ZSET"""
        return f"pool:{pool_id}:bins"
    
    @staticmethod
    def get_token_graph_key(version: str = "1") -> str:
        """Get Redis key for token graph"""
        return f"token_graph:{version}" 