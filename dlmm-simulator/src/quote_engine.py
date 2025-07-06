"""
Quote Engine for DLMM - Handles routing and quote calculations across multiple pools and pairs.
Uses graph-based routing where tokens are nodes and pools are edges.
"""

import json
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import math
from collections import defaultdict, deque
import heapq

from .pool import MockPool, BinData, PoolConfig
from .routing import SinglePoolRouter
from .math import DLMMMath


class RouteType(Enum):
    SINGLE_BIN = "single_bin"      # 0 | 0 | 0
    MULTI_BIN = "multi_bin"        # 0 | 0 | N  
    MULTI_POOL = "multi_pool"      # 0 | N | N
    MULTI_PAIR = "multi_pair"      # N | N | N


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
class Route:
    """Represents a trading route"""
    pools: List[str]
    pair_hops: int
    pool_hops: int
    estimated_gas: int
    route_type: RouteType


@dataclass
class GraphNode:
    """Represents a token node in the liquidity graph"""
    token: str
    pools: List[str]  # Pool IDs where this token is involved


@dataclass
class GraphEdge:
    """Represents a pool edge in the liquidity graph"""
    pool_id: str
    token_x: str
    token_y: str
    bin_step: int
    active_bin_id: int
    active_bin_price: float
    total_tvl: float
    status: str


class LiquidityGraph:
    """Graph representation of the liquidity network"""
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}  # token -> GraphNode
        self.edges: Dict[str, GraphEdge] = {}  # pool_id -> GraphEdge
        self.adjacency: Dict[str, List[str]] = defaultdict(list)  # token -> [pool_ids]
    
    def add_pool(self, pool_data: Dict):
        """Add a pool as an edge in the graph"""
        pool_id = pool_data["pool_id"]
        token_x = pool_data["token_x"]
        token_y = pool_data["token_y"]
        
        # Create edge
        edge = GraphEdge(
            pool_id=pool_id,
            token_x=token_x,
            token_y=token_y,
            bin_step=pool_data["bin_step"],
            active_bin_id=pool_data["active_bin_id"],
            active_bin_price=float(pool_data["active_bin_price"]),  # Already a float
            total_tvl=float(pool_data["total_tvl"]),  # Already a float
            status=pool_data["status"]
        )
        self.edges[pool_id] = edge
        
        # Add to adjacency list
        self.adjacency[token_x].append(pool_id)
        self.adjacency[token_y].append(pool_id)
        
        # Create/update nodes
        if token_x not in self.nodes:
            self.nodes[token_x] = GraphNode(token=token_x, pools=[])
        if token_y not in self.nodes:
            self.nodes[token_y] = GraphNode(token=token_y, pools=[])
        
        self.nodes[token_x].pools.append(pool_id)
        self.nodes[token_y].pools.append(pool_id)
    
    def find_paths(self, token_in: str, token_out: str, max_pair_hops: int = 3) -> List[List[str]]:
        """Find all possible paths between tokens using BFS"""
        if token_in == token_out:
            return []
        
        paths = []
        queue = deque([(token_in, [token_in])])
        visited = set()
        
        while queue:
            current_token, path = queue.popleft()
            
            if len(path) > max_pair_hops + 1:  # +1 because we count edges, not nodes
                continue
            
            if current_token == token_out and len(path) > 1:
                paths.append(path)
                continue
            
            if current_token in visited:
                continue
            
            visited.add(current_token)
            
            # Find all pools connected to current token
            for pool_id in self.adjacency.get(current_token, []):
                edge = self.edges[pool_id]
                next_token = edge.token_y if edge.token_x == current_token else edge.token_x
                
                if next_token not in path:  # Avoid cycles
                    queue.append((next_token, path + [next_token]))
        
        return paths
    
    def get_pools_for_path(self, path: List[str]) -> List[str]:
        """Get the pools that connect the tokens in a path"""
        pools = []
        for i in range(len(path) - 1):
            token1, token2 = path[i], path[i + 1]
            
            # Find pool connecting these tokens
            for pool_id in self.adjacency.get(token1, []):
                edge = self.edges[pool_id]
                if (edge.token_x == token1 and edge.token_y == token2) or \
                   (edge.token_x == token2 and edge.token_y == token1):
                    pools.append(pool_id)
                    break
        
        return pools
    
    def get_pools_for_pair(self, token_x: str, token_y: str) -> List[str]:
        """Get all pools for a specific token pair"""
        pools = []
        for pool_id in self.adjacency.get(token_x, []):
            edge = self.edges[pool_id]
            if (edge.token_x == token_x and edge.token_y == token_y) or \
               (edge.token_x == token_y and edge.token_y == token_x):
                pools.append(pool_id)
        return pools


class MockRedisClient:
    """Mock Redis client for development and testing"""
    
    def __init__(self):
        self.data = {}
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize sample pool and bin data"""
        # Sample pools
        pools = [
            {
                "pool_id": "BTC-USDC-25",
                "token_x": "BTC",
                "token_y": "USDC",
                "bin_step": 25,
                "active_bin_id": 500,
                "active_bin_price": 100000.0,  # 100,000 USDC per BTC
                "status": "active",
                "total_tvl": 1000000.0,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "pool_id": "BTC-USDC-50", 
                "token_x": "BTC",
                "token_y": "USDC",
                "bin_step": 50,
                "active_bin_id": 500,
                "active_bin_price": 100000.0,  # 100,000 USDC per BTC
                "status": "active", 
                "total_tvl": 500000.0,
                "created_at": "2024-01-01T00:00:00Z"
            },
            {
                "pool_id": "SOL-USDC-25",
                "token_x": "SOL",
                "token_y": "USDC",
                "bin_step": 25,
                "active_bin_id": 500,
                "active_bin_price": 200.0,  # 200 USDC per SOL
                "status": "active",
                "total_tvl": 100000.0,
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        for pool in pools:
            self.data[f"pool:{pool['pool_id']}"] = pool
            
            # Create bin data for each pool
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
        """Create sample bin data for a pool"""
        pool_id = pool["pool_id"]
        active_bin_id = pool["active_bin_id"]
        active_price = float(pool["active_bin_price"])  # Price is already stored as float
        bin_step = pool["bin_step"] / 1000000  # Convert bps to decimal (25 bps = 0.000025)
        
        # Define token decimals
        token_decimals = {
            "BTC": 8,
            "USDC": 6,
            "SOL": 9
        }
        
        token_x = pool["token_x"]
        token_y = pool["token_y"]
        x_decimals = token_decimals.get(token_x, 18)
        y_decimals = token_decimals.get(token_y, 18)
        
        print(f"DEBUG: Creating bins for {pool_id}")
        print(f"DEBUG: active_price: {active_price}")
        print(f"DEBUG: bin_step: {bin_step}")
        print(f"DEBUG: {token_x} decimals: {x_decimals}, {token_y} decimals: {y_decimals}")
        
        # Create bins around active bin
        for bin_id in range(active_bin_id - 50, active_bin_id + 51):
            # Calculate bin price using DLMMMath
            bin_price = DLMMMath.calculate_bin_price(active_price, bin_step, bin_id, active_bin_id)
            if bin_id in [499, 500, 501]:
                print(f"DEBUG: {pool_id} bin {bin_id}: calculated price = {bin_price} (active_price={active_price}, bin_step={bin_step})")
            # Create liquidity distribution (bell curve around active bin)
            distance = abs(bin_id - active_bin_id)
            liquidity_factor = max(0.1, 1 - (distance / 50) ** 2)
            # Create realistic liquidity amounts based on token decimals
            if token_x == "BTC" and token_y == "USDC":
                base_x_amount = 1000 * liquidity_factor  # 1000 BTC
                base_y_amount = 100000000 * liquidity_factor  # 100M USDC
            elif token_x == "SOL" and token_y == "USDC":
                base_x_amount = 100000 * liquidity_factor  # 100K SOL
                base_y_amount = 20000000 * liquidity_factor  # 20M USDC
            else:
                base_x_amount = 1000 * liquidity_factor
                base_y_amount = 1000000 * liquidity_factor
            if bin_id < active_bin_id:
                # Left bins: only X tokens
                x_amount = base_x_amount
                y_amount = 0
            elif bin_id > active_bin_id:
                # Right bins: only Y tokens
                x_amount = 0
                y_amount = base_y_amount
            else:
                # Active bin: both tokens
                x_amount = base_x_amount
                y_amount = base_y_amount
            bin_data = {
                "pool_id": pool_id,
                "bin_id": bin_id,
                "x_amount": x_amount,
                "y_amount": y_amount,
                "price": bin_price,
                "total_liquidity": x_amount + y_amount,
                "is_active": bin_id == active_bin_id
            }
            self.data[f"bin:{pool_id}:{bin_id}"] = bin_data
        # After all bins are created, print debug info for bins 499, 500, 501
        for check_bin in [499, 500, 501]:
            key = f"bin:{pool_id}:{check_bin}"
            if key in self.data:
                bin_data = self.data[key]
                print(f"DEBUG: {pool_id} bin {check_bin}: x_amount={bin_data['x_amount']}, y_amount={bin_data['y_amount']}, price={bin_data['price']}")
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        return json.dumps(self.data.get(key)) if key in self.data else None
    
    def set(self, key: str, value: str) -> bool:
        """Set value in Redis"""
        self.data[key] = json.loads(value)
        return True
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return key in self.data
    
    def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        import fnmatch
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]


class QuoteEngine:
    """
    Main quote engine for DLMM routing and quote calculations.
    Uses graph-based routing to find optimal paths through the liquidity network.
    
    Supports all route types:
    1. Single pair, single pool, single bin   (0 | 0 | 0)
    2. Single pair, single pool, multi bin   (0 | 0 | N)  
    3. Single pair, multi pool, multi bin    (0 | N | N)
    4. Multi pair, multi pool, multi bin     (N | N | N)
    """
    
    def __init__(self, redis_client: MockRedisClient):
        self.redis = redis_client
        self.graph = LiquidityGraph()
        self.max_pair_hops = 3
        self.max_pool_hops = 5
        self.fee_rate = 0.001  # 10 basis points
        
        # Build the liquidity graph
        self._build_graph()
    
    def _build_graph(self):
        """Build the liquidity graph from Redis data"""
        for key in self.redis.keys("pool:*"):
            pool_data = json.loads(self.redis.get(key))
            self.graph.add_pool(pool_data)
    
    def get_quote(self, token_in: str, token_out: str, amount_in: float) -> QuoteResult:
        """
        Get the best quote for swapping token_in to token_out.
        
        Args:
            token_in: Input token symbol
            token_out: Output token symbol  
            amount_in: Input amount (scaled by 1e18)
            
        Returns:
            Best quote result
        """
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
        
        # Find all possible paths through the graph
        paths = self.graph.find_paths(token_in, token_out, self.max_pair_hops)
        print(f"DEBUG: Found {len(paths)} paths for {token_in} -> {token_out}:")
        for i, path in enumerate(paths):
            print(f"DEBUG: Path {i}: {' -> '.join(path)}")
        
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
        
        # Calculate quotes for all paths
        quotes = []
        for i, path in enumerate(paths):
            print(f"DEBUG: Calculating quote for path {i}: {' -> '.join(path)}")
            quote = self._calculate_path_quote(path, amount_in, token_in, token_out)
            if quote.success:
                print(f"DEBUG: Path {i} quote: {quote.amount_out:.6f} {token_out}")
                quotes.append(quote)
            else:
                print(f"DEBUG: Path {i} failed: {quote.error}")
        
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
        print(f"DEBUG: Best quote: {best_quote.amount_out:.6f} {token_out} (route type: {best_quote.route_type.value})")
        return best_quote
    
    def _calculate_path_quote(self, path: List[str], amount_in: float, token_in: str, token_out: str) -> QuoteResult:
        """Calculate quote for a specific path through the graph"""
        if len(path) == 2:
            # Direct path - single pair
            quote = self._calculate_single_pair_quote(path[0], path[1], amount_in, token_in, token_out)
            print(f"DEBUG: Single pair quote result: success={quote.success}, amount_out={quote.amount_out}")
            if quote.success and quote.amount_out > 0:
                return quote
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
                    error="No valid single pair quote"
                )
        else:
            # Multi-hop path
            return self._calculate_multi_pair_quote(path, amount_in, token_in, token_out)
    
    def _calculate_single_pair_quote(self, token_x: str, token_y: str, amount_in: float, token_in: str, token_out: str) -> QuoteResult:
        """Calculate quote for single pair (route types 1-3)"""
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
            # Single pool - route types 1-2
            return self._single_pool_quote(pools[0], amount_in, token_in, token_out)
        else:
            # Multi pool - route type 3
            return self._multi_pool_quote(pools, amount_in, token_in, token_out)
    
    def _calculate_multi_pair_quote(self, path: List[str], amount_in: float, token_in: str, token_out: str) -> QuoteResult:
        """Calculate quote for multi-pair path (route type 4) using DLMMMath for all math"""
        path_pools = self.graph.get_pools_for_path(path)
        if len(path_pools) < len(path) - 1:
            return QuoteResult(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                amount_out=0,
                price_impact=0.0,
                route_type=RouteType.MULTI_PAIR,
                steps=[],
                success=False,
                error="Incomplete path - missing pools"
            )
        current_amount = amount_in
        all_steps = []
        # For theoretical output calculation
        theoretical_amount = amount_in
        for i, pool_id in enumerate(path_pools):
            hop_token_in = path[i]
            hop_token_out = path[i + 1]
            hop_quote = self._single_pool_quote(pool_id, current_amount, hop_token_in, hop_token_out)
            if not hop_quote.success:
                return QuoteResult(
                    token_in=token_in,
                    token_out=token_out,
                    amount_in=amount_in,
                    amount_out=0,
                    price_impact=0.0,
                    route_type=RouteType.MULTI_PAIR,
                    steps=[],
                    success=False,
                    error=f"Hop {i+1} failed: {hop_quote.error}"
                )
            all_steps.extend(hop_quote.steps)
            # For theoretical output: use active bin price for the full input of this hop
            pool_data = json.loads(self.redis.get(f"pool:{pool_id}"))
            active_price = float(pool_data["active_bin_price"])
            if hop_token_in == pool_data["token_x"] and hop_token_out == pool_data["token_y"]:
                # X→Y
                theoretical_amount = theoretical_amount * active_price
            else:
                # Y→X
                theoretical_amount = theoretical_amount / active_price if active_price > 0 else 0
            current_amount = hop_quote.amount_out
        
        # Calculate price impact as described
        price_impact = abs(current_amount - theoretical_amount) / theoretical_amount if theoretical_amount > 0 else 0
        print(f"DEBUG: After swap loop: total_amount_out={current_amount}, theoretical_amount={theoretical_amount}, price_impact={price_impact}")
        return QuoteResult(
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            amount_out=current_amount,
            price_impact=price_impact * 100,  # as percent
            route_type=RouteType.MULTI_PAIR,
            steps=all_steps,
            success=True
        )
    
    def _single_pool_quote(self, pool_id: str, amount_in: float, token_in: str = None, token_out: str = None) -> QuoteResult:
        """Calculate quote for a single pool using SinglePoolRouter"""
        pool_data = json.loads(self.redis.get(f"pool:{pool_id}"))
        if not pool_data:
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
        
        # Create a MockPool instance for the SinglePoolRouter
        from .pool import MockPool, PoolConfig, BinData
        config = PoolConfig(
            active_bin_id=pool_data["active_bin_id"],
            active_price=float(pool_data["active_bin_price"]),
            bin_step=pool_data["bin_step"] / 1000000,  # Convert bps to decimal (25 bps = 0.000025)
            num_bins=1000,  # Default value, could be made configurable
            x_token=pool_data["token_x"],
            y_token=pool_data["token_y"]
        )
        pool = MockPool(config)
        
        # Clear the default bins and add our custom bins
        pool.bins = {}
        bins = self._get_pool_bins(pool_id)
        for bin_id, bin_data in bins.items():
            pool.bins[bin_id] = BinData(
                bin_id=bin_id,
                x_amount=float(bin_data["x_amount"]),
                y_amount=float(bin_data["y_amount"]),
                price=float(bin_data["price"]),
                total_liquidity=float(bin_data["x_amount"]) + float(bin_data["y_amount"]) / float(bin_data["price"]),
                is_active=bin_id == pool_data["active_bin_id"]
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
        
        # Use SinglePoolRouter to get the quote
        router = SinglePoolRouter(pool)
        route_result = router.get_quote(actual_token_in, amount_after_fees, actual_token_out)
        
        # Debug output
        print(f"DEBUG: SinglePoolRouter result:")
        print(f"  input: {amount_after_fees} {actual_token_in}")
        print(f"  output: {route_result.total_amount_out} {actual_token_out}")
        print(f"  steps: {len(route_result.steps)}")
        for i, step in enumerate(route_result.steps):
            print(f"    Step {i}: bin_id={step.bin_id}, amount_in={step.amount_in}, amount_out={step.amount_out}, price={step.price}")
        
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
    
    def _get_pool_bins(self, pool_id: str) -> Dict[int, Dict]:
        """Get all bins for a pool"""
        bins = {}
        for key in self.redis.keys(f"bin:{pool_id}:*"):
            bin_id = int(key.split(":")[-1])
            bin_data = json.loads(self.redis.get(key))
            bins[int(bin_id)] = bin_data  # Ensure bin_id is always int
        return bins
    
    def _multi_pool_quote(self, pool_ids: List[str], amount_in: float, token_in: str = None, token_out: str = None) -> QuoteResult:
        """Calculate quote for multiple pools of same pair"""
        # For now, use the best single pool quote
        # TODO: Implement optimal distribution across pools
        best_quote = None
        best_amount_out = 0
        
        for pool_id in pool_ids:
            quote = self._single_pool_quote(pool_id, amount_in, token_in, token_out)
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