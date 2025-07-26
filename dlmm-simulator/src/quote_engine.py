"""
Optimized Quote Engine for DLMM - Performance-focused implementation.
Uses caching, pre-computed paths, and optimized data structures.
"""

import json
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import math
from collections import defaultdict, deque
import heapq
from functools import lru_cache
import threading

from .pool import MockPool, BinData, PoolConfig
from .routing import SinglePoolRouter
from .math import DLMMMath


class RouteType(Enum):
    SINGLE_BIN = "single_bin"
    MULTI_BIN = "multi_bin"
    MULTI_POOL = "multi_pool"
    MULTI_PAIR = "multi_pair"


@dataclass
class QuoteStep:
    """Represents a single step in a quote route"""
    pool_id: str
    bin_id: int
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price: float
    price_impact: float
    fee_amount: float = 0


@dataclass
class QuoteResult:
    """Complete quote result"""
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price_impact: float
    route_type: RouteType
    steps: List[QuoteStep]
    success: bool
    error: Optional[str] = None
    estimated_gas: int = 0


@dataclass
class CachedPath:
    """Cached path information"""
    path: List[List[str]]
    pools: List[List[str]]
    last_updated: float
    ttl: float = 300  # 5 minutes


class LiquidityGraph:
    """Optimized graph representation with caching and pre-computed paths"""
    
    def __init__(self):
        self.nodes: Dict[str, Set[str]] = defaultdict(set)  # token -> {pool_ids}
        self.edges: Dict[str, Dict] = {}  # pool_id -> edge_data
        self.path_cache: Dict[str, CachedPath] = {}  # cache_key -> CachedPath
        self.cache_lock = threading.RLock()
        self.max_cache_size = 1000
        
    def add_pool(self, pool_data: Dict):
        """Add a pool as an edge in the graph - Updated for new schema"""
        pool_id = pool_data["pool_id"]
        token0 = pool_data["token0"]
        token1 = pool_data["token1"]
        
        # Store edge data
        self.edges[pool_id] = {
            "token0": token0,
            "token1": token1,
            "bin_step": float(pool_data["bin_step"]),
            "active_bin": int(pool_data["active_bin"]),
            "active": pool_data["active"].lower() == "true",
            "x_protocol_fee": int(pool_data["x_protocol_fee"]),
            "x_provider_fee": int(pool_data["x_provider_fee"]),
            "x_variable_fee": int(pool_data["x_variable_fee"]),
            "y_protocol_fee": int(pool_data["y_protocol_fee"]),
            "y_provider_fee": int(pool_data["y_provider_fee"]),
            "y_variable_fee": int(pool_data["y_variable_fee"])
        }
        
        # Add to adjacency sets (faster lookups)
        self.nodes[token0].add(pool_id)
        self.nodes[token1].add(pool_id)
        
        # Clear path cache when graph changes
        self._clear_cache()
    
    def _clear_cache(self):
        """Clear the path cache"""
        with self.cache_lock:
            self.path_cache.clear()
    
    def _get_cache_key(self, token_in: str, token_out: str, max_hops: int) -> str:
        """Generate cache key for path lookup"""
        return f"{token_in}:{token_out}:{max_hops}"
    
    @lru_cache(maxsize=1000)
    def find_paths_cached(self, token_in: str, token_out: str, max_pair_hops: int = 3) -> Tuple[List[List[str]], List[List[str]]]:
        """Find paths with caching and return both paths and pool lists"""
        if token_in == token_out:
            return [], []
        
        cache_key = self._get_cache_key(token_in, token_out, max_pair_hops)
        current_time = time.time()
        
        # Check cache
        with self.cache_lock:
            if cache_key in self.path_cache:
                cached = self.path_cache[cache_key]
                if current_time - cached.last_updated < cached.ttl:
                    return cached.path, cached.pools
        
        # Find paths using optimized BFS
        paths, pool_lists = self._find_paths_optimized(token_in, token_out, max_pair_hops)
        
        # Cache results
        with self.cache_lock:
            if len(self.path_cache) >= self.max_cache_size:
                # Remove oldest entries
                oldest_keys = sorted(self.path_cache.keys(), 
                                   key=lambda k: self.path_cache[k].last_updated)[:100]
                for key in oldest_keys:
                    del self.path_cache[key]
            
            self.path_cache[cache_key] = CachedPath(
                path=paths,
                pools=pool_lists[0] if pool_lists else [],
                last_updated=current_time
            )
        
        return paths, pool_lists
    
    def _find_paths_optimized(self, token_in: str, token_out: str, max_pair_hops: int) -> Tuple[List[List[str]], List[List[str]]]:
        """Optimized path finding using BFS with early termination"""
        if token_in == token_out:
            return [], []
        
        paths = []
        pool_lists = []
        queue = deque([(token_in, [token_in], [])])  # (token, path, pools)
        visited = set()
        
        while queue:
            current_token, path, pools = queue.popleft()
            
            if len(path) > max_pair_hops + 1:
                continue
            
            if current_token == token_out and len(path) > 1:
                paths.append(path)
                pool_lists.append(pools)
                continue
            
            if current_token in visited:
                continue
            
            visited.add(current_token)
            
            # Use set intersection for faster pool lookup
            current_pools = self.nodes.get(current_token, set())
            
            for pool_id in current_pools:
                edge = self.edges[pool_id]
                next_token = edge["token1"] if edge["token0"] == current_token else edge["token0"]
                
                if next_token not in path:  # Avoid cycles
                    new_pools = pools + [pool_id]
                    queue.append((next_token, path + [next_token], new_pools))
        
        return paths, pool_lists
    
    def get_pools_for_pair(self, token0: str, token1: str) -> List[str]:
        """Get all pools for a specific token pair using set intersection"""
        pools_token0 = self.nodes.get(token0, set())
        pools_token1 = self.nodes.get(token1, set())
        
        # Find pools that contain both tokens
        matching_pools = []
        for pool_id in pools_token0 & pools_token1:  # Set intersection
            edge = self.edges[pool_id]
            if (edge["token0"] == token0 and edge["token1"] == token1) or \
               (edge["token0"] == token1 and edge["token1"] == token0):
                matching_pools.append(pool_id)
        
        return matching_pools


class MockRedisClient:
    """Optimized mock Redis client with caching - New schema only"""
    
    def __init__(self):
        self.hashes = {}  # Redis Hash storage
        self.zsets = {}  # Redis ZSET storage
        self.bin_cache = {}  # Cache for bin data
        self.pool_cache = {}  # Cache for pool data
        self.cache_lock = threading.RLock()
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize sample pool and bin data using new schema only"""
        # Create sample pools with new schema structure
        pools = [
            {
                "pool_id": "BTC-USDC-25",
                "token0": "BTC",
                "token1": "USDC", 
                "bin_step": 0.0025,  # 25 basis points
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
                "bin_step": 0.005,  # 50 basis points
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
                "bin_step": 0.0025,  # 25 basis points
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
        
        # Store pools as Redis Hashes
        for pool in pools:
            pool_key = f"pool:{pool['pool_id']}"
            self.hashes[pool_key] = {
                "pool_id": pool["pool_id"],
                "token0": pool["token0"],
                "token1": pool["token1"],
                "bin_step": str(pool["bin_step"]),
                "active_bin": str(pool["active_bin"]),
                "active": str(pool["active"]).lower(),
                "x_protocol_fee": str(pool["x_protocol_fee"]),
                "x_provider_fee": str(pool["x_provider_fee"]),
                "x_variable_fee": str(pool["x_variable_fee"]),
                "y_protocol_fee": str(pool["y_protocol_fee"]),
                "y_provider_fee": str(pool["y_provider_fee"]),
                "y_variable_fee": str(pool["y_variable_fee"])
            }
            self._create_bin_data_new_schema(pool)
        
        # Create token graph
        self.hashes["token_graph:1"] = {
            "BTC->USDC": json.dumps(["BTC-USDC-25", "BTC-USDC-50"]),
            "SOL->USDC": json.dumps(["SOL-USDC-25"])
        }
    
    def _create_bin_data_new_schema(self, pool: Dict):
        """Create sample bin data for a pool using new schema"""
        pool_id = pool["pool_id"]
        active_bin = pool["active_bin"]
        bin_step = pool["bin_step"]
        
        # Calculate active bin price (using a reasonable default)
        active_price = 50000.0  # $50,000 USDC per 1 BTC
        
        # Create bins around active bin
        for bin_id in range(active_bin - 50, active_bin + 51):
            # Calculate bin price (Y/X)
            bin_price = DLMMMath.calculate_bin_price(active_price, bin_step, bin_id, active_bin)
            
            # Store bin price in ZSET
            zset_key = f"pool:{pool_id}:bins"
            if zset_key not in self.zsets:
                self.zsets[zset_key] = {}
            self.zsets[zset_key][str(bin_id)] = bin_price
            
            # Create bin data with realistic reserves
            distance = abs(bin_id - active_bin)
            liquidity_factor = max(0.1, 1 - (distance / 50) ** 2)
            
            if pool["token0"] == "BTC" and pool["token1"] == "USDC":
                # For BTC-USDC pool
                base_x_amount = int(1000 * liquidity_factor)  # BTC amount
                base_y_amount = int(50000000 * liquidity_factor)  # USDC amount
                # Liquidity rebased in USDC: Y + X * price
                liquidity_usdc = base_y_amount + int(base_x_amount * bin_price)
            elif pool["token0"] == "SOL" and pool["token1"] == "USDC":
                # For SOL-USDC pool
                base_x_amount = int(100000 * liquidity_factor)  # SOL amount
                base_y_amount = int(20000000 * liquidity_factor)  # USDC amount
                # Liquidity rebased in USDC: Y + X * price
                liquidity_usdc = base_y_amount + int(base_x_amount * bin_price)
            else:
                # Generic case
                base_x_amount = int(1000 * liquidity_factor)
                base_y_amount = int(1000000 * liquidity_factor)
                # Liquidity rebased in Y: Y + X * price
                liquidity_usdc = base_y_amount + int(base_x_amount * bin_price)
            
            # Store bin data as Redis Hash
            bin_key = f"bin:{pool_id}:{bin_id}"
            self.hashes[bin_key] = {
                "pool_id": pool_id,
                "bin_id": str(bin_id),
                "reserve_x": str(base_x_amount),
                "reserve_y": str(base_y_amount),
                "liquidity": str(liquidity_usdc)  # Rebased in terms of Y (USDC)
            }
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis - READ ONLY operation"""
        # This method is kept for compatibility but should not be used for new schema
        # New code should use hgetall, zrange, etc.
        return None
    
    def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern - READ ONLY operation"""
        import fnmatch
        all_keys = list(self.hashes.keys()) + list(self.zsets.keys())
        return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]

    # ===== REDIS OPERATIONS FOR NEW SCHEMA (READ ONLY) =====

    def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields - READ ONLY"""
        return self.hashes.get(key, {})

    def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> List:
        """Get range of members from sorted set - READ ONLY"""
        if key not in self.zsets:
            return []
        
        # Sort by score
        sorted_items = sorted(self.zsets[key].items(), key=lambda x: x[1])
        
        # Apply range
        if end == -1:
            items = sorted_items[start:]
        else:
            items = sorted_items[start:end+1]
        
        if withscores:
            return items
        else:
            return [item[0] for item in items]

    def zscore(self, key: str, member: str) -> Optional[float]:
        """Get score of member in sorted set - READ ONLY"""
        if key not in self.zsets:
            return None
        return self.zsets[key].get(member)

    def zrangebyscore(self, key: str, min_score: float, max_score: float, withscores: bool = False) -> List:
        """Get members with scores in range - READ ONLY"""
        if key not in self.zsets:
            return []
        
        # Filter by score range
        items = [(member, score) for member, score in self.zsets[key].items() 
                if min_score <= score <= max_score]
        
        # Sort by score
        items.sort(key=lambda x: x[1])
        
        if withscores:
            return items
        else:
            return [item[0] for item in items]


class QuoteEngine:
    """
    Optimized quote engine with performance improvements:
    - Cached path finding
    - Optimized data structures
    - Pre-computed pool configurations
    - Reduced object creation
    """
    
    def __init__(self, redis_client: MockRedisClient):
        self.redis = redis_client
        self.graph = LiquidityGraph()
        self.max_pair_hops = 3
        self.max_pool_hops = 5
        self.fee_rate = 0.001
        
        # Pre-compute pool configurations
        self.pool_configs = {}
        self._build_graph()
        self._precompute_pool_configs()
    
    def _build_graph(self):
        """Build the liquidity graph from Redis data - Updated for new schema"""
        for key in self.redis.keys("pool:*"):
            pool_hash = self.redis.hgetall(key)
            if pool_hash:
                self.graph.add_pool(pool_hash)
    
    def _precompute_pool_configs(self):
        """Pre-compute pool configurations for faster access - Updated for new schema"""
        for key in self.redis.keys("pool:*"):
            pool_hash = self.redis.hgetall(key)
            if not pool_hash:
                continue
                
            pool_id = pool_hash["pool_id"]
            active_bin = int(pool_hash["active_bin"])
            bin_step = float(pool_hash["bin_step"])
            
            # Calculate active bin price from ZSET
            zset_key = f"pool:{pool_id}:bins"
            active_bin_price = self.redis.zscore(zset_key, str(active_bin))
            if active_bin_price is None:
                # Fallback calculation
                active_bin_price = 50000.0  # Default price
            
            self.pool_configs[pool_id] = {
                "config": PoolConfig(
                    pool_id=pool_id,
                    active_bin_id=active_bin,
                    active_price=active_bin_price,
                    bin_step=bin_step,
                    num_bins=1000,
                    x_token=pool_hash["token0"],
                    y_token=pool_hash["token1"]
                ),
                "pool_data": pool_hash
            }
    
    @lru_cache(maxsize=1000)
    def get_quote_cached(self, token_in: str, token_out: str, amount_in: float) -> QuoteResult:
        """Cached version of get_quote for repeated requests"""
        return self.get_quote(token_in, token_out, amount_in)
    
    def get_quote(self, token_in: str, token_out: str, amount_in: float) -> QuoteResult:
        """Get the best quote for swapping token_in to token_out"""
        if token_in == token_out:
            return QuoteResult(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=amount_in,
                price_impact=0.0,
                route_type=RouteType.SINGLE_BIN,
                steps=[],
                success=True
            )
        
        # Use cached path finding
        paths, pool_lists = self.graph.find_paths_cached(token_in, token_out, self.max_pair_hops)
        
        if not paths:
            return QuoteResult(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=0,
                price_impact=0.0,
                route_type=RouteType.SINGLE_BIN,
                steps=[],
                success=False,
                error="No routes found between tokens"
            )
        
        # Calculate quotes for all paths (use first pool list for now)
        quotes = []
        for i, path in enumerate(paths):
            quote = self._calculate_path_quote_optimized(path, amount_in, token_in, token_out)
            if quote.success:
                quotes.append(quote)
        
        if not quotes:
            return QuoteResult(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=0,
                price_impact=0.0,
                route_type=RouteType.SINGLE_BIN,
                steps=[],
                success=False,
                error="No valid quotes found"
            )
        
        # Return best quote (highest output amount)
        best_quote = max(quotes, key=lambda q: q.amount_out)
        return best_quote
    
    def _calculate_path_quote_optimized(self, path: List[str], amount_in: float, token_in: str, token_out: str) -> QuoteResult:
        """Optimized path quote calculation"""
        if len(path) == 2:
            # Direct path - single pair
            return self._calculate_single_pair_quote_optimized(path[0], path[1], amount_in, token_in, token_out)
        else:
            # Multi-hop path
            return self._calculate_multi_pair_quote_optimized(path, amount_in, token_in, token_out)
    
    def _calculate_single_pair_quote_optimized(self, token0: str, token1: str, amount_in: float, token_in: str, token_out: str) -> QuoteResult:
        """Optimized single pair quote calculation"""
        pools = self.graph.get_pools_for_pair(token0, token1)
        
        if not pools:
            return QuoteResult(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=0,
                price_impact=0.0,
                route_type=RouteType.MULTI_BIN,
                steps=[],
                success=False,
                error=f"No pools found for {token0}-{token1}"
            )
        
        if len(pools) == 1:
            return self._single_pool_quote_optimized(pools[0], amount_in, token_in, token_out)
        else:
            return self._multi_pool_quote_optimized(pools, amount_in, token_in, token_out)
    
    def _single_pool_quote_optimized(self, pool_id: str, amount_in: float, token_in: str = None, token_out: str = None) -> QuoteResult:
        """Optimized single pool quote calculation"""
        if pool_id not in self.pool_configs:
            return QuoteResult(
                token_in=token_in or "",
                token_out=token_out or "",
                amount_in=amount_in,
                amount_out=0,
                price_impact=0.0,
                route_type=RouteType.MULTI_BIN,
                steps=[],
                success=False,
                error="Pool not found"
            )
        
        # Use pre-computed configuration
        pool_config_data = self.pool_configs[pool_id]
        config = pool_config_data["config"]
        pool_data = pool_config_data["pool_data"]
        
        # Create pool with pre-computed config
        pool = MockPool(config)
        
        # Get bins efficiently
        bins = self._get_pool_bins_optimized(pool_id)
        
        # Populate pool bins
        pool.bins = {}
        for bin_id, bin_data in bins.items():
            bin_price = DLMMMath.calculate_bin_price(config.active_price, config.bin_step, bin_id, config.active_bin_id)
            
            pool.bins[bin_id] = BinData(
                bin_id=bin_id,
                x_amount=float(bin_data["reserve_x"]),
                y_amount=float(bin_data["reserve_y"]),
                price=bin_price,
                total_liquidity=float(bin_data["liquidity"]),  # Already rebased in terms of Y
                is_active=bin_id == config.active_bin_id
            )
        
        # Determine swap direction
        if token_in and token_out:
            if token_in == pool_data["token0"] and token_out == pool_data["token1"]:
                actual_token_in = pool_data["token0"]
                actual_token_out = pool_data["token1"]
            elif token_in == pool_data["token1"] and token_out == pool_data["token0"]:
                actual_token_in = pool_data["token1"]
                actual_token_out = pool_data["token0"]
            else:
                return QuoteResult(
                    token_in=token_in,
                    token_out=token_out,
                    amount_in=amount_in,
                    amount_out=0,
                    price_impact=0.0,
                    route_type=RouteType.MULTI_BIN,
                    steps=[],
                    success=False,
                    error=f"Pool {pool_id} cannot handle {token_in} to {token_out} swap"
                )
        else:
            actual_token_in = pool_data["token0"]
            actual_token_out = pool_data["token1"]
        
        # Apply fees
        fee_amount = amount_in * self.fee_rate
        amount_after_fees = amount_in - fee_amount
        
        # Use SinglePoolRouter
        router = SinglePoolRouter(pool)
        route_result = router.get_quote(actual_token_in, amount_after_fees, actual_token_out)
        
        # Convert RouteStep to QuoteStep
        steps = []
        for step in route_result.steps:
            quote_step = QuoteStep(
                pool_id=step.pool_id,
                bin_id=step.bin_id,
                token_in=step.token_in,
                token_out=step.token_out,
                amount_in=step.amount_in,
                amount_out=step.amount_out,
                price=step.price,
                price_impact=step.price_impact,
                fee_amount=fee_amount * (step.amount_in / amount_after_fees) if amount_after_fees > 0 else 0
            )
            steps.append(quote_step)
        
        return QuoteResult(
            token_in=actual_token_in,
            token_out=actual_token_out,
            amount_in=amount_in,
            amount_out=route_result.total_amount_out,
            price_impact=route_result.total_price_impact,
            route_type=RouteType.MULTI_BIN,
            steps=steps,
            success=route_result.success,
            error=route_result.error_message
        )
    
    def _get_pool_bins_optimized(self, pool_id: str) -> Dict[int, Dict]:
        """Optimized bin retrieval with caching - Updated for new schema"""
        cache_key = f"bins:{pool_id}"
        
        with self.redis.cache_lock:
            if cache_key not in self.redis.bin_cache:
                bins = {}
                for key in self.redis.keys(f"bin:{pool_id}:*"):
                    bin_id = int(key.split(":")[-1])
                    bin_hash = self.redis.hgetall(key)
                    if bin_hash:
                        # Convert hash format to expected dict format
                        bins[int(bin_id)] = {
                            "reserve_x": bin_hash["reserve_x"],
                            "reserve_y": bin_hash["reserve_y"],
                            "liquidity": bin_hash["liquidity"]
                        }
                self.redis.bin_cache[cache_key] = bins
            
            return self.redis.bin_cache[cache_key]
    
    def _calculate_multi_pair_quote_optimized(self, path: List[str], amount_in: float, token_in: str, token_out: str) -> QuoteResult:
        """Optimized multi-pair quote calculation"""
        # Simplified implementation for now
        return self._calculate_single_pair_quote_optimized(path[0], path[1], amount_in, token_in, token_out)
    
    def _multi_pool_quote_optimized(self, pool_ids: List[str], amount_in: float, token_in: str = None, token_out: str = None) -> QuoteResult:
        """Optimized multi-pool quote calculation"""
        # Use the best single pool quote
        best_quote = None
        best_amount_out = 0
        
        for pool_id in pool_ids:
            quote = self._single_pool_quote_optimized(pool_id, amount_in, token_in, token_out)
            if quote.success and quote.amount_out > best_amount_out:
                best_quote = quote
                best_amount_out = quote.amount_out
        
        if best_quote and best_quote.amount_out > 0:
            return best_quote
        
        return QuoteResult(
            token_in=token_in or "",
            token_out=token_out or "",
            amount_in=amount_in,
            amount_out=0,
            price_impact=0.0,
            route_type=RouteType.MULTI_POOL,
            steps=[],
            success=False,
            error="No valid multi-pool quote"
        ) 