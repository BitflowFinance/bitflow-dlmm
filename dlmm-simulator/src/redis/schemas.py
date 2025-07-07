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
    """Pool data structure for Redis storage"""
    pool_id: str
    token_x: str
    token_y: str
    bin_step: int
    initial_active_bin_id: int
    active_bin_id: int
    active_bin_price: float
    status: str
    total_tvl: float
    created_at: str
    last_updated: str
    
    def to_redis_hash(self) -> Dict[str, str]:
        """Convert to Redis hash format"""
        return {
            "pool_id": self.pool_id,
            "token_x": self.token_x,
            "token_y": self.token_y,
            "bin_step": str(self.bin_step),
            "initial_active_bin_id": str(self.initial_active_bin_id),
            "active_bin_id": str(self.active_bin_id),
            "active_bin_price": str(self.active_bin_price),
            "status": self.status,
            "total_tvl": str(self.total_tvl),
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_redis_hash(cls, data: Dict[str, str]) -> 'PoolData':
        """Create PoolData from Redis hash"""
        return cls(
            pool_id=data["pool_id"],
            token_x=data["token_x"],
            token_y=data["token_y"],
            bin_step=int(data["bin_step"]),
            initial_active_bin_id=int(data["initial_active_bin_id"]),
            active_bin_id=int(data["active_bin_id"]),
            active_bin_price=float(data["active_bin_price"]),
            status=data["status"],
            total_tvl=float(data["total_tvl"]),
            created_at=data["created_at"],
            last_updated=data["last_updated"]
        )
    
    def validate(self) -> bool:
        """Validate pool data"""
        try:
            assert self.pool_id and len(self.pool_id) > 0
            assert self.token_x and len(self.token_x) > 0
            assert self.token_y and len(self.token_y) > 0
            assert self.bin_step > 0
            assert self.initial_active_bin_id >= 0
            assert self.active_bin_id >= 0
            assert self.active_bin_price > 0
            assert self.status in ["active", "inactive", "paused"]
            assert self.total_tvl >= 0
            return True
        except Exception as e:
            logger.error(f"Pool data validation failed: {e}")
            return False


@dataclass
class BinData:
    """Bin data structure for Redis storage"""
    pool_id: str
    bin_id: int
    x_amount: float
    y_amount: float
    price: float
    total_liquidity: float
    is_active: bool
    last_updated: str
    
    def to_redis_hash(self) -> Dict[str, str]:
        """Convert to Redis hash format"""
        return {
            "pool_id": self.pool_id,
            "bin_id": str(self.bin_id),
            "x_amount": str(self.x_amount),
            "y_amount": str(self.y_amount),
            "price": str(self.price),
            "total_liquidity": str(self.total_liquidity),
            "is_active": str(self.is_active).lower(),
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_redis_hash(cls, data: Dict[str, str]) -> 'BinData':
        """Create BinData from Redis hash"""
        return cls(
            pool_id=data["pool_id"],
            bin_id=int(data["bin_id"]),
            x_amount=float(data["x_amount"]),
            y_amount=float(data["y_amount"]),
            price=float(data["price"]),
            total_liquidity=float(data["total_liquidity"]),
            is_active=data["is_active"].lower() == "true",
            last_updated=data["last_updated"]
        )
    
    def validate(self) -> bool:
        """Validate bin data"""
        try:
            assert self.pool_id and len(self.pool_id) > 0
            assert self.bin_id >= 0
            assert self.x_amount >= 0
            assert self.y_amount >= 0
            assert self.price > 0
            assert self.total_liquidity >= 0
            assert isinstance(self.is_active, bool)
            return True
        except Exception as e:
            logger.error(f"Bin data validation failed: {e}")
            return False


@dataclass
class Metadata:
    """Metadata for Redis data"""
    total_pools: int
    total_tokens: int
    last_update: str
    data_version: str
    total_bins: int
    
    def to_redis_hash(self) -> Dict[str, str]:
        """Convert to Redis hash format"""
        return {
            "total_pools": str(self.total_pools),
            "total_tokens": str(self.total_tokens),
            "last_update": self.last_update,
            "data_version": self.data_version,
            "total_bins": str(self.total_bins)
        }
    
    @classmethod
    def from_redis_hash(cls, data: Dict[str, str]) -> 'Metadata':
        """Create Metadata from Redis hash"""
        return cls(
            total_pools=int(data["total_pools"]),
            total_tokens=int(data["total_tokens"]),
            last_update=data["last_update"],
            data_version=data["data_version"],
            total_bins=int(data["total_bins"])
        )


class RedisSchema:
    """Redis schema definitions and key patterns"""
    
    # Key patterns
    POOL_KEY_PATTERN = "pool:{pool_id}"
    BIN_KEY_PATTERN = "bin:{pool_id}:{bin_id}"
    BINS_HASH_PATTERN = "bins:{pool_id}"
    METADATA_KEY = "metadata"
    TOKEN_INDEX_PATTERN = "tokens:{token}"
    PAIR_INDEX_PATTERN = "pairs:{token_x}:{token_y}"
    
    @staticmethod
    def get_pool_key(pool_id: str) -> str:
        """Get Redis key for pool data"""
        return f"pool:{pool_id}"
    
    @staticmethod
    def get_bin_key(pool_id: str, bin_id: int) -> str:
        """Get Redis key for individual bin data"""
        return f"bin:{pool_id}:{bin_id}"
    
    @staticmethod
    def get_bins_hash_key(pool_id: str) -> str:
        """Get Redis key for bins hash"""
        return f"bins:{pool_id}"
    
    @staticmethod
    def get_token_index_key(token: str) -> str:
        """Get Redis key for token index"""
        return f"tokens:{token}"
    
    @staticmethod
    def get_pair_index_key(token_x: str, token_y: str) -> str:
        """Get Redis key for pair index"""
        return f"pairs:{token_x}:{token_y}"
    
    @staticmethod
    def get_metadata_key() -> str:
        """Get Redis key for metadata"""
        return "metadata"


class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_pool_data(data: Dict[str, Any]) -> bool:
        """Validate pool data structure"""
        try:
            required_fields = [
                "pool_id", "token_x", "token_y", "bin_step",
                "initial_active_bin_id", "active_bin_id", "active_bin_price",
                "status", "total_tvl"
            ]
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Type validation
            if not isinstance(data["pool_id"], str) or len(data["pool_id"]) == 0:
                return False
            
            if not isinstance(data["bin_step"], int) or data["bin_step"] <= 0:
                return False
            
            if not isinstance(data["active_bin_price"], (int, float)) or data["active_bin_price"] <= 0:
                return False
            
            if data["status"] not in ["active", "inactive", "paused"]:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Pool data validation error: {e}")
            return False
    
    @staticmethod
    def validate_bin_data(data: Dict[str, Any]) -> bool:
        """Validate bin data structure"""
        try:
            required_fields = [
                "pool_id", "bin_id", "x_amount", "y_amount",
                "price", "total_liquidity", "is_active"
            ]
            
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Type validation
            if not isinstance(data["pool_id"], str) or len(data["pool_id"]) == 0:
                return False
            
            if not isinstance(data["bin_id"], int) or data["bin_id"] < 0:
                return False
            
            if not isinstance(data["x_amount"], (int, float)) or data["x_amount"] < 0:
                return False
            
            if not isinstance(data["y_amount"], (int, float)) or data["y_amount"] < 0:
                return False
            
            if not isinstance(data["price"], (int, float)) or data["price"] <= 0:
                return False
            
            if not isinstance(data["is_active"], bool):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Bin data validation error: {e}")
            return False
    
    @staticmethod
    def sanitize_pool_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize pool data for Redis storage"""
        sanitized = {}
        
        # Convert numeric fields
        numeric_fields = ["bin_step", "initial_active_bin_id", "active_bin_id", "active_bin_price", "total_tvl"]
        for field in numeric_fields:
            if field in data:
                try:
                    if field in ["bin_step", "initial_active_bin_id", "active_bin_id"]:
                        sanitized[field] = int(data[field])
                    else:
                        sanitized[field] = float(data[field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid numeric value for {field}: {data[field]}")
                    continue
        
        # Copy string fields
        string_fields = ["pool_id", "token_x", "token_y", "status", "created_at", "last_updated"]
        for field in string_fields:
            if field in data:
                sanitized[field] = str(data[field])
        
        return sanitized
    
    @staticmethod
    def sanitize_bin_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize bin data for Redis storage"""
        sanitized = {}
        
        # Convert numeric fields
        numeric_fields = ["bin_id", "x_amount", "y_amount", "price", "total_liquidity"]
        for field in numeric_fields:
            if field in data:
                try:
                    if field == "bin_id":
                        sanitized[field] = int(data[field])
                    else:
                        sanitized[field] = float(data[field])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid numeric value for {field}: {data[field]}")
                    continue
        
        # Copy string fields
        string_fields = ["pool_id", "last_updated"]
        for field in string_fields:
            if field in data:
                sanitized[field] = str(data[field])
        
        # Handle boolean field
        if "is_active" in data:
            sanitized["is_active"] = bool(data["is_active"])
        
        return sanitized


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.utcnow().isoformat() + "Z"


def create_metadata(total_pools: int, total_tokens: int, total_bins: int) -> Metadata:
    """Create metadata object"""
    return Metadata(
        total_pools=total_pools,
        total_tokens=total_tokens,
        last_update=get_current_timestamp(),
        data_version="1.0",
        total_bins=total_bins
    ) 