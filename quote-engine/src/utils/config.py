"""
Configuration management for the quote engine.
Handles local and production Redis settings.
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis configuration settings"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = None
    ssl: bool = False
    decode_responses: bool = True


@dataclass
class AppConfig:
    """Application configuration settings"""
    debug: bool = False
    max_hops: int = 3
    max_bin_traversal: int = 1000
    default_fee_rate: float = 0.001  # 10 basis points


class Config:
    """Configuration management class"""
    
    # Redis configurations
    REDIS_LOCAL = RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        ssl=False
    )
    
    REDIS_PRODUCTION = RedisConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        password=os.getenv('REDIS_PASSWORD'),
        ssl=os.getenv('REDIS_SSL', 'false').lower() == 'true'
    )
    
    # App configurations
    APP_CONFIG = AppConfig(
        debug=os.getenv('DEBUG', 'false').lower() == 'true',
        max_hops=int(os.getenv('MAX_HOPS', 3)),
        max_bin_traversal=int(os.getenv('MAX_BIN_TRAVERSAL', 1000)),
        default_fee_rate=float(os.getenv('DEFAULT_FEE_RATE', 0.001))
    )
    
    @classmethod
    def get_redis_config(cls, environment: str = "local") -> RedisConfig:
        """Get Redis configuration for specified environment"""
        if environment == "production":
            return cls.REDIS_PRODUCTION
        else:
            return cls.REDIS_LOCAL
    
    @classmethod
    def get_redis_dict(cls, environment: str = "local") -> Dict[str, Any]:
        """Get Redis configuration as dictionary for redis-py"""
        config = cls.get_redis_config(environment)
        redis_dict = {
            'host': config.host,
            'port': config.port,
            'db': config.db,
            'decode_responses': config.decode_responses
        }
        
        if config.password:
            redis_dict['password'] = config.password
        
        if config.ssl:
            redis_dict['ssl'] = config.ssl
        
        return redis_dict
    
    @classmethod
    def get_app_config(cls) -> AppConfig:
        """Get application configuration"""
        return cls.APP_CONFIG 