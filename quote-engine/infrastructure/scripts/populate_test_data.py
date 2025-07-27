"""
Script to populate Redis with sample data for testing the quote engine.
Uses the same data structure as the existing dlmm-simulator for consistency.
"""

import sys
import os
import json
import logging
from decimal import Decimal

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.redis.client import RedisClient
from src.redis.schemas import PoolData, BinData, TokenGraphData, RedisSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_pool_data(redis_client):
    """Populate pool data in Redis"""
    pools = [
        {
            "pool_id": "BTC-USDC-25",
            "token0": "BTC",
            "token1": "USDC",
            "bin_step": 0.0025,
            "active_bin": 500,
            "active": True,
            "x_protocol_fee": 4,
            "x_provider_fee": 6,
            "x_variable_fee": 0,
            "y_protocol_fee": 4,
            "y_provider_fee": 6,
            "y_variable_fee": 0
        },
        {
            "pool_id": "BTC-USDC-50",
            "token0": "BTC",
            "token1": "USDC",
            "bin_step": 0.0050,
            "active_bin": 500,
            "active": True,
            "x_protocol_fee": 4,
            "x_provider_fee": 6,
            "x_variable_fee": 0,
            "y_protocol_fee": 4,
            "y_provider_fee": 6,
            "y_variable_fee": 0
        },
        {
            "pool_id": "ETH-USDC-25",
            "token0": "ETH",
            "token1": "USDC",
            "bin_step": 0.0025,
            "active_bin": 500,
            "active": True,
            "x_protocol_fee": 4,
            "x_provider_fee": 6,
            "x_variable_fee": 0,
            "y_protocol_fee": 4,
            "y_provider_fee": 6,
            "y_variable_fee": 0
        },
        {
            "pool_id": "SOL-USDC-25",
            "token0": "SOL",
            "token1": "USDC",
            "bin_step": 0.0025,
            "active_bin": 500,
            "active": True,
            "x_protocol_fee": 4,
            "x_provider_fee": 6,
            "x_variable_fee": 0,
            "y_protocol_fee": 4,
            "y_provider_fee": 6,
            "y_variable_fee": 0
        }
    ]
    
    for pool_data in pools:
        pool = PoolData(**pool_data)
        key = RedisSchema.get_pool_key(pool.pool_id)
        redis_client.client.hset(key, mapping=pool.to_redis_hash())
        logger.info(f"Added pool: {pool.pool_id}")


def populate_bin_data(redis_client):
    """Populate bin data in Redis with proper DLMM bin distribution"""
    # Define pool configurations with realistic market prices and correct decimal places
    pool_configs = [
        {
            "pool_id": "BTC-USDC-25",
            "active_bin": 500,
            "base_price": 100000.0,  # $100,000 per BTC (realistic 2024 price)
            "bin_step": 0.0025,     # 25 bps
            "base_reserve_x": 1000 * 100000000,  # 1000 BTC (8 decimal places)
            "base_reserve_y": 100000000 * 1000000  # 100M USDC (6 decimal places)
        },
        {
            "pool_id": "BTC-USDC-50",
            "active_bin": 500,
            "base_price": 100000.0,  # $100,000 per BTC (realistic 2024 price)
            "bin_step": 0.005,      # 50 bps
            "base_reserve_x": 500 * 100000000,   # 500 BTC (8 decimal places)
            "base_reserve_y": 50000000 * 1000000  # 50M USDC (6 decimal places)
        },
        {
            "pool_id": "ETH-USDC-25",
            "active_bin": 500,
            "base_price": 4000.0,   # $4,000 per ETH (realistic 2024 price)
            "bin_step": 0.0025,     # 25 bps
            "base_reserve_x": 10000 * 1000000000000000000, # 10,000 ETH (18 decimal places)
            "base_reserve_y": 40000000 * 1000000  # 40M USDC (6 decimal places)
        },
        {
            "pool_id": "SOL-USDC-25",
            "active_bin": 500,
            "base_price": 200.0,    # $200 per SOL (realistic 2024 price)
            "bin_step": 0.0025,     # 25 bps
            "base_reserve_x": 100000 * 1000000000, # 100,000 SOL (9 decimal places)
            "base_reserve_y": 20000000 * 1000000  # 20M USDC (6 decimal places)
        }
    ]
    
    for config in pool_configs:
        pool_id = config["pool_id"]
        active_bin = config["active_bin"]
        base_price = config["base_price"]
        bin_step = config["bin_step"]
        base_reserve_x = config["base_reserve_x"]
        base_reserve_y = config["base_reserve_y"]
        
        # Create bins around the active bin
        for i in range(-50, 51):  # 101 bins total
            bin_id = active_bin + i
            price = base_price * ((1 + bin_step) ** i)
            
            # DLMM Bin Distribution Rules:
            # - Active bin (i=0): Contains both X and Y tokens
            # - Bins to the right (i>0): Higher prices, contain only X tokens (BTC/ETH/SOL)
            # - Bins to the left (i<0): Lower prices, contain only Y tokens (USDC)
            
            if i == 0:  # Active bin - contains both tokens
                reserve_x = base_reserve_x
                reserve_y = base_reserve_y
            elif i > 0:  # Right side - higher prices, only X tokens
                # Decreasing liquidity as we move away from active bin
                liquidity_factor = max(0.1, 1.0 - abs(i) * 0.02)
                reserve_x = int(base_reserve_x * liquidity_factor)
                reserve_y = 0  # No Y tokens in higher-priced bins
            else:  # Left side - lower prices, only Y tokens
                # Decreasing liquidity as we move away from active bin
                liquidity_factor = max(0.1, 1.0 - abs(i) * 0.02)
                reserve_x = 0  # No X tokens in lower-priced bins
                reserve_y = int(base_reserve_y * liquidity_factor)
            
            # Calculate liquidity (rebased in terms of Y)
            liquidity = reserve_y + int(reserve_x * price)
            
            bin_data = BinData(
                pool_id=pool_id,
                bin_id=bin_id,
                reserve_x=reserve_x,
                reserve_y=reserve_y,
                liquidity=liquidity
            )
            
            # Store bin reserves
            bin_key = RedisSchema.get_bin_key(pool_id, bin_id)
            redis_client.client.hset(bin_key, mapping=bin_data.to_redis_hash())
            
            # Store bin price in ZSET
            zset_key = RedisSchema.get_bin_price_zset_key(pool_id)
            redis_client.client.zadd(zset_key, {str(bin_id): price})
        
        logger.info(f"Added bins for pool: {pool_id} with proper DLMM distribution")


def populate_token_graph(redis_client):
    """Populate token graph in Redis"""
    token_graph = TokenGraphData(
        version="1",
        token_pairs={
            "BTC->USDC": ["BTC-USDC-25", "BTC-USDC-50"],
            "USDC->BTC": ["BTC-USDC-25", "BTC-USDC-50"],
            "ETH->USDC": ["ETH-USDC-25"],
            "USDC->ETH": ["ETH-USDC-25"],
            "SOL->USDC": ["SOL-USDC-25"],
            "USDC->SOL": ["SOL-USDC-25"]
        }
    )
    
    key = RedisSchema.get_token_graph_key("1")
    redis_client.client.hset(key, mapping=token_graph.to_redis_hash())
    logger.info("Added token graph")


def main():
    """Main function to populate Redis with test data"""
    try:
        logger.info("🚀 Starting Redis data population...")
        
        # Create Redis client
        redis_client = RedisClient(environment="local")
        
        # Clear existing data (optional)
        logger.info("Clearing existing data...")
        redis_client.client.flushdb()
        
        # Populate data
        logger.info("Populating pool data...")
        populate_pool_data(redis_client)
        
        logger.info("Populating bin data...")
        populate_bin_data(redis_client)
        
        logger.info("Populating token graph...")
        populate_token_graph(redis_client)
        
        logger.info("✅ Redis data population completed successfully!")
        
        # Verify data
        logger.info("Verifying data...")
        pool_count = len(redis_client.get_all_pool_ids())
        logger.info(f"Found {pool_count} pools")
        
        token_graph = redis_client.get_token_graph("1")
        if token_graph:
            logger.info(f"Token graph has {len(token_graph.token_pairs)} pairs")
        
        logger.info("🎉 Ready for testing!")
        
    except Exception as e:
        logger.error(f"❌ Error populating Redis data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 