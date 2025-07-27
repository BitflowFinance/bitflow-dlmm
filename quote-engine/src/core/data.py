"""
Data pre-fetching operations for the quote engine.
Implements pre_fetch_shared_data function following Grok's design.
"""

import logging
from typing import Dict, List, Any, Set
from decimal import Decimal
from ..redis.client import RedisClient
from ..redis.schemas import PoolData, BinData

logger = logging.getLogger(__name__)


def pre_fetch_shared_data(redis_client: RedisClient, paths: List[List[str]], graph) -> Dict[str, Dict[str, Any]]:
    """
    Pre-fetch shared pool metadata and active bin data across all paths.
    
    Args:
        redis_client: Redis client instance
        paths: List of token paths
        graph: NetworkX graph
        
    Returns:
        Dictionary with pool_id as key and metadata/spot data as value
    """
    try:
        # Extract unique pools from all paths
        unique_pools = set()
        for path in paths:
            for i in range(len(path) - 1):
                from_token, to_token = path[i], path[i + 1]
                pools = get_pools_for_token_pair(graph, from_token, to_token)
                unique_pools.update(pools)
        
        if not unique_pools:
            logger.warning("No pools found in paths")
            return {}
        
        logger.info(f"Pre-fetching data for {len(unique_pools)} unique pools")
        
        # Use Redis pipeline for batch operations
        pipe = redis_client.pipeline()
        
        # Queue pool metadata requests
        pool_metadata_requests = {}
        for pool_id in unique_pools:
            pool_key = f"pool:{pool_id}"
            pool_metadata_requests[pool_id] = pool_key
            pipe.hgetall(pool_key)
        
        # Execute pipeline for pool metadata
        pool_results = pipe.execute()
        
        # Parse pool metadata results
        shared_data = {}
        for i, pool_id in enumerate(unique_pools):
            pool_data = pool_results[i]
            if pool_data:
                try:
                    # Parse pool metadata
                    pool_metadata = PoolData.from_redis_hash(pool_data)
                    
                    # Get active bin price from ZSET
                    active_bin_id = pool_metadata.active_bin
                    active_bin_price = redis_client.get_bin_price(pool_id, active_bin_id)
                    
                    # Get active bin reserves
                    active_bin_data = redis_client.get_bin_data(pool_id, active_bin_id)
                    
                    shared_data[pool_id] = {
                        'metadata': pool_metadata,
                        'active_bin_id': active_bin_id,
                        'active_bin_data': active_bin_data.to_redis_hash() if active_bin_data else {}
                    }
                    
                    logger.debug(f"Pre-fetched data for pool {pool_id}: price={active_bin_price}")
                    
                except Exception as e:
                    logger.error(f"Error parsing pool data for {pool_id}: {e}")
                    continue
        
        logger.info(f"Successfully pre-fetched data for {len(shared_data)} pools")
        return shared_data
        
    except Exception as e:
        logger.error(f"Error pre-fetching shared data: {e}")
        return {}


def get_pools_for_token_pair(graph, token_a: str, token_b: str) -> List[str]:
    """
    Get available pools for a token pair.
    
    Args:
        graph: NetworkX graph
        token_a: First token
        token_b: Second token
        
    Returns:
        List of pool IDs for the token pair
    """
    try:
        if graph.has_edge(token_a, token_b):
            return graph[token_a][token_b].get('pools', [])
        return []
    except Exception as e:
        logger.error(f"Error getting pools for {token_a} -> {token_b}: {e}")
        return []


def batch_load_bin_reserves(redis_client: RedisClient, pool_id: str, bin_ids: List[int]) -> Dict[int, BinData]:
    """
    Batch load bin reserves for a pool.
    
    Args:
        redis_client: Redis client instance
        pool_id: Pool ID
        bin_ids: List of bin IDs to load
        
    Returns:
        Dictionary mapping bin_id to BinData
    """
    try:
        if not bin_ids:
            return {}
        
        # Use Redis pipeline for batch operations
        pipe = redis_client.pipeline()
        
        # Queue bin data requests
        for bin_id in bin_ids:
            bin_key = f"bin:{pool_id}:{bin_id}"
            pipe.hgetall(bin_key)
        
        # Execute pipeline
        bin_results = pipe.execute()
        
        # Parse results
        bin_data = {}
        for i, bin_id in enumerate(bin_ids):
            result = bin_results[i]
            if result:
                try:
                    bin_data[bin_id] = BinData.from_redis_hash(result)
                except Exception as e:
                    logger.error(f"Error parsing bin data for {pool_id}:{bin_id}: {e}")
                    continue
        
        logger.debug(f"Batch loaded {len(bin_data)} bins for pool {pool_id}")
        return bin_data
        
    except Exception as e:
        logger.error(f"Error batch loading bin reserves for {pool_id}: {e}")
        return {}


def validate_shared_data(shared_data: Dict[str, Dict[str, Any]]) -> bool:
    """
    Validate pre-fetched shared data.
    
    Args:
        shared_data: Pre-fetched data dictionary
        
    Returns:
        True if data is valid, False otherwise
    """
    try:
        for pool_id, data in shared_data.items():
            # Check required keys
            required_keys = ['metadata', 'active_bin_id', 'active_bin_data']
            for key in required_keys:
                if key not in data:
                    logger.error(f"Missing required key '{key}' for pool {pool_id}")
                    return False
            
            # Validate metadata
            if not isinstance(data['metadata'], PoolData):
                logger.error(f"Invalid metadata type for pool {pool_id}")
                return False
            
            # Validate active bin ID
            if not isinstance(data['active_bin_id'], int):
                logger.error(f"Invalid active bin ID type for pool {pool_id}")
                return False
            
            # Validate active bin data
            if not isinstance(data['active_bin_data'], dict):
                logger.error(f"Invalid active bin data type for pool {pool_id}")
                return False
        
        logger.info("Shared data validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Shared data validation error: {e}")
        return False 