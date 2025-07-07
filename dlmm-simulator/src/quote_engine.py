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
    path: List[str]
    pools: List[str]
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
        """Add a pool as an edge in the graph"""
        pool_id = pool_data["pool_id"]
        token_x = pool_data["token_x"]
        token_y = pool_data["token_y"]
        
        # Store edge data
        self.edges[pool_id] = {
            "token_x": token_x,
            "token_y": token_y,
            "bin_step": pool_data["bin_step"],
            "active_bin_id": pool_data["active_bin_id"],
            "active_bin_price": float(pool_data["active_bin_price"]),
            "total_tvl": float(pool_data["total_tvl"]),
            "status": pool_data["status"]
        }
        
        # Add to adjacency sets (faster lookups)
        self.nodes[token_x].add(pool_id)
        self.nodes[token_y].add(pool_id)
        
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
                next_token = edge["token_y"] if edge["token_x"] == current_token else edge["token_x"]
                
                if next_token not in path:  # Avoid cycles
                    new_pools = pools + [pool_id]
                    queue.append((next_token, path + [next_token], new_pools))
        
        return paths, pool_lists
    
    def get_pools_for_pair(self, token_x: str, token_y: str) -> List[str]:
        """Get all pools for a specific token pair using set intersection"""
        pools_x = self.nodes.get(token_x, set())
        pools_y = self.nodes.get(token_y, set())
        
        # Find pools that contain both tokens
        matching_pools = []
        for pool_id in pools_x & pools_y:  # Set intersection
            edge = self.edges[pool_id]
            if (edge["token_x"] == token_x and edge["token_y"] == token_y) or \
               (edge["token_x"] == token_y and edge["token_y"] == token_x):
                matching_pools.append(pool_id)
        
        return matching_pools


class MockRedisClient:
    """Optimized mock Redis client with caching"""
    
    def __init__(self):
        self.data = {}
        self.bin_cache = {}  # Cache for bin data
        self.pool_cache = {}  # Cache for pool data
        self.cache_lock = threading.RLock()
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize sample pool and bin data"""
        # Same initialization as original
        pools = [
            {
                "pool_id": "BTC-USDC-25",
                "token_x": "BTC",
                "token_y": "USDC",
                "bin_step": 25,
                "initial_active_bin_id": 500,
                "active_bin_id": 500,
                "active_bin_price": 100000.0,
                "status": "active",
                "total_tvl": 1000000.0,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "pool_id": "BTC-USDC-50", 
                "token_x": "BTC",
                "token_y": "USDC",
                "bin_step": 50,
                "initial_active_bin_id": 500,
                "active_bin_id": 500,
                "active_bin_price": 100000.0,
                "status": "active", 
                "total_tvl": 500000.0,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "pool_id": "SOL-USDC-25",
                "token_x": "SOL",
                "token_y": "USDC",
                "bin_step": 25,
                "initial_active_bin_id": 500,
                "active_bin_id": 500,
                "active_bin_price": 200.0,
                "status": "active",
                "total_tvl": 100000.0,
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        for pool in pools:
            self.data[f"pool:{pool['pool_id']}"] = pool
            self._create_bin_data(pool)
        
        # Create pair indices
        self.data["pairs:BTC:USDC"] = {
            "pools": ["BTC-USDC-25", "BTC-USDC-50"],
            "last_updated": "2024-01-01T00:00:00Z"
        }
        
        self.data["pairs:SOL:USDC"] = {
            "pools": ["SOL-USDC-25"],
            "last_updated": "2024-01-01T00:00:00Z"
        }
    
    def _create_bin_data(self, pool: Dict):
        """Create sample bin data for a pool (same as original)"""
        # Same implementation as original MockRedisClient
        pool_id = pool["pool_id"]
        initial_active_bin_id = pool["initial_active_bin_id"]
        current_active_bin_id = pool["active_bin_id"]
        initial_active_price = float(pool["active_bin_price"])
        bin_step = pool["bin_step"] / 10000
        
        current_active_price = initial_active_price * ((1 + bin_step) ** (current_active_bin_id - initial_active_bin_id))
        
        token_decimals = {"BTC": 8, "USDC": 6, "SOL": 9}
        token_x = pool["token_x"]
        token_y = pool["token_y"]
        x_decimals = token_decimals.get(token_x, 18)
        y_decimals = token_decimals.get(token_y, 18)
        
        # Create bins around current active bin
        for bin_id in range(current_active_bin_id - 50, current_active_bin_id + 51):
            bin_price = DLMMMath.calculate_bin_price(current_active_price, bin_step, bin_id, current_active_bin_id)
            
            distance = abs(bin_id - current_active_bin_id)
            liquidity_factor = max(0.1, 1 - (distance / 50) ** 2)
            
            if token_x == "BTC" and token_y == "USDC":
                base_x_amount = 1000 * liquidity_factor
                base_y_amount = 100000000 * liquidity_factor
            elif token_x == "SOL" and token_y == "USDC":
                base_x_amount = 100000 * liquidity_factor
                base_y_amount = 20000000 * liquidity_factor
            else:
                base_x_amount = 1000 * liquidity_factor
                base_y_amount = 1000000 * liquidity_factor
                
            if bin_id < current_active_bin_id:
                x_amount = base_x_amount
                y_amount = 0
            elif bin_id > current_active_bin_id:
                x_amount = 0
                y_amount = base_y_amount
            else:
                x_amount = base_x_amount
                y_amount = base_y_amount
                
            bin_data = {
                "pool_id": pool_id,
                "bin_id": bin_id,
                "x_amount": x_amount,
                "y_amount": y_amount,
                "price": bin_price,
                "total_liquidity": x_amount + y_amount,
                "is_active": bin_id == current_active_bin_id
            }
            self.data[f"bin:{pool_id}:{bin_id}"] = bin_data
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis with caching"""
        with self.cache_lock:
            if key.startswith("pool:"):
                if key not in self.pool_cache:
                    self.pool_cache[key] = json.dumps(self.data.get(key)) if key in self.data else None
                return self.pool_cache[key]
            else:
                return json.dumps(self.data.get(key)) if key in self.data else None
    
    def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        import fnmatch
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]


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
        """Build the liquidity graph from Redis data"""
        for key in self.redis.keys("pool:*"):
            pool_data = json.loads(self.redis.get(key))
            self.graph.add_pool(pool_data)
    
    def _precompute_pool_configs(self):
        """Pre-compute pool configurations for faster access"""
        for key in self.redis.keys("pool:*"):
            pool_data = json.loads(self.redis.get(key))
            pool_id = pool_data["pool_id"]
            
            initial_active_bin_id = pool_data["initial_active_bin_id"]
            current_active_bin_id = pool_data["active_bin_id"]
            initial_active_price = float(pool_data["active_bin_price"])
            bin_step = pool_data["bin_step"] / 10000
            
            current_active_price = initial_active_price * ((1 + bin_step) ** (current_active_bin_id - initial_active_bin_id))
            
            self.pool_configs[pool_id] = {
                "config": PoolConfig(
                    pool_id=pool_id,
                    active_bin_id=current_active_bin_id,
                    active_price=current_active_price,
                    bin_step=bin_step,
                    num_bins=1000,
                    x_token=pool_data["token_x"],
                    y_token=pool_data["token_y"]
                ),
                "pool_data": pool_data
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
    
    def _calculate_single_pair_quote_optimized(self, token_x: str, token_y: str, amount_in: float, token_in: str, token_out: str) -> QuoteResult:
        """Optimized single pair quote calculation"""
        pools = self.graph.get_pools_for_pair(token_x, token_y)
        
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
                error=f"No pools found for {token_x}-{token_y}"
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
                x_amount=float(bin_data["x_amount"]),
                y_amount=float(bin_data["y_amount"]),
                price=bin_price,
                total_liquidity=float(bin_data["x_amount"]) + float(bin_data["y_amount"]) / bin_price,
                is_active=bin_id == config.active_bin_id
            )
        
        # Determine swap direction
        if token_in and token_out:
            if token_in == pool_data["token_x"] and token_out == pool_data["token_y"]:
                actual_token_in = pool_data["token_x"]
                actual_token_out = pool_data["token_y"]
            elif token_in == pool_data["token_y"] and token_out == pool_data["token_x"]:
                actual_token_in = pool_data["token_y"]
                actual_token_out = pool_data["token_x"]
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
            actual_token_in = pool_data["token_x"]
            actual_token_out = pool_data["token_y"]
        
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
        """Optimized bin retrieval with caching"""
        cache_key = f"bins:{pool_id}"
        
        with self.redis.cache_lock:
            if cache_key not in self.redis.bin_cache:
                bins = {}
                for key in self.redis.keys(f"bin:{pool_id}:*"):
                    bin_id = int(key.split(":")[-1])
                    bin_data = json.loads(self.redis.get(key))
                    bins[int(bin_id)] = bin_data
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