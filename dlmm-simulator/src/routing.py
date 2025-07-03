"""
Routing algorithms for DLMM simulator.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from .pool import MockPool, BinData
from .math import DLMMMath


@dataclass
class RouteStep:
    """Represents a single step in a routing path."""
    pool_id: str
    bin_id: int
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price: float
    price_impact: float


@dataclass
class RouteResult:
    """Result of a routing operation."""
    total_amount_in: float
    total_amount_out: float
    steps: List[RouteStep]
    total_price_impact: float
    success: bool
    error_message: Optional[str] = None


class SinglePoolRouter:
    """
    Router for single pool multi-bin operations.
    
    This router implements DLMM routing logic within a single pool:
    
    Routing Strategy:
    1. Start with the active bin (contains both X and Y tokens)
    2. For X→Y swaps: traverse right (higher bin IDs) to find more Y tokens
    3. For Y→X swaps: traverse left (lower bin IDs) to find more X tokens
    4. Use as much liquidity as possible from each bin
    5. Continue until input is exhausted or no more output tokens available
    
    Error Handling:
    - Returns insufficient liquidity error if input cannot be fully swapped
    - Respects minimum output requirements
    - Handles empty bins gracefully
    
    Output:
    - Returns detailed steps showing which bins were used
    - Calculates price impact for each step
    - Provides total output and success status
    """
    
    def __init__(self, pool: MockPool):
        self.pool = pool
        self.math = DLMMMath()
    
    def get_quote(self, token_in: str, amount_in: float, token_out: str, min_amount_out: float = 0) -> RouteResult:
        """
        Get a quote for swapping tokens within a single pool across multiple bins.
        
        Args:
            token_in: Input token symbol
            amount_in: Amount of input token
            token_out: Output token symbol
            min_amount_out: Minimum amount of output token required
        
        Returns:
            RouteResult with quote details
        """
        if token_in not in [self.pool.config.x_token, self.pool.config.y_token]:
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=0,
                steps=[],
                total_price_impact=0,
                success=False,
                error_message=f"Token {token_in} not found in pool"
            )
        
        if token_out not in [self.pool.config.x_token, self.pool.config.y_token]:
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=0,
                steps=[],
                total_price_impact=0,
                success=False,
                error_message=f"Token {token_out} not found in pool"
            )
        
        if token_in == token_out:
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=amount_in,
                steps=[],
                total_price_impact=0,
                success=True
            )
        
        # Determine swap direction
        is_x_to_y = (token_in == self.pool.config.x_token and token_out == self.pool.config.y_token)
        
        # Route the swap
        return self._route_swap(amount_in, is_x_to_y, min_amount_out)
    
    def _route_swap(self, amount_in: float, is_x_to_y: bool, min_amount_out: float) -> RouteResult:
        """
        Route a swap across multiple bins within the pool.
        
        Args:
            amount_in: Amount of input token
            is_x_to_y: True if swapping X for Y, False if Y for X
            min_amount_out: Minimum amount of output token required
        
        Returns:
            RouteResult with swap details
        """
        current_bin = self.pool.config.active_bin_id
        # Apply fee once at the beginning
        fee_amount = amount_in * 0.0  # 0% fee - testing
        remaining_amount = amount_in - fee_amount
        total_amount_out = 0
        steps = []

        # Helper to process a bin
        def process_bin(bin_data, remaining_amount, is_x_to_y):
            amount_out, new_remaining = self.math.swap_within_bin(
                bin_data, remaining_amount, is_x_to_y
            )
            amount_used = remaining_amount - new_remaining
            return amount_used, amount_out, new_remaining

        # Always process bins in correct order: active bin, then left/right
        bin_sequence = []
        if is_x_to_y:
            # X->Y: active bin, then bins to the right (higher bin IDs, higher prices)
            bin_sequence.append(current_bin)
            bin_sequence.extend(range(current_bin + 1, self.pool.config.num_bins))
        else:
            # Y->X: active bin, then bins to the left (lower bin IDs, lower prices)
            bin_sequence.append(current_bin)
            bin_sequence.extend(range(current_bin - 1, -1, -1))

        for bin_id in bin_sequence:
            if remaining_amount <= 0:
                break
            # Skip if remaining amount is too small (numerical precision issue)
            if remaining_amount < 1e-6:  # Increased threshold
                break
            bin_data = self.pool.get_bin(bin_id)
            if not bin_data:
                continue
            
            amount_used, amount_out, new_remaining = process_bin(bin_data, remaining_amount, is_x_to_y)
            
            # Only count bins where we actually get output and amounts are meaningful
            if amount_used > 1e-6 and amount_out > 1e-6:
                total_amount_out += amount_out
                price_impact = self.math.calculate_price_impact(
                    amount_used, amount_out, is_x_to_y, self.pool.config.active_price
                )
                step = RouteStep(
                    pool_id=f"{self.pool.config.x_token}-{self.pool.config.y_token}",
                    bin_id=bin_id,
                    token_in=self.pool.config.x_token if is_x_to_y else self.pool.config.y_token,
                    token_out=self.pool.config.y_token if is_x_to_y else self.pool.config.x_token,
                    amount_in=amount_used,
                    amount_out=amount_out,
                    price=bin_data.price,
                    price_impact=price_impact
                )
                steps.append(step)
            
            remaining_amount = new_remaining

        # If we still have input left after all bins, it's insufficient liquidity
        if remaining_amount > 1e-6:  # Only fail if significant amount remains
            # Calculate average price impact for partial swap
            if total_amount_out > 0:
                # Calculate actual amount that was successfully swapped
                actual_amount_swapped = amount_in - remaining_amount
                
                if is_x_to_y:
                    avg_exec_price = total_amount_out / actual_amount_swapped
                    price_impact = abs(avg_exec_price - self.pool.config.active_price) / self.pool.config.active_price * 100
                else:
                    avg_exec_price = actual_amount_swapped / total_amount_out
                    price_impact = abs(avg_exec_price - self.pool.config.active_price) / self.pool.config.active_price * 100
            else:
                price_impact = 0
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=total_amount_out,
                steps=steps,
                total_price_impact=price_impact,
                success=False,
                error_message=f"Insufficient liquidity: could not swap {remaining_amount} of input token"
            )

        # Check minimum output requirement
        if total_amount_out < min_amount_out:
            # Calculate average price impact for partial swap
            if total_amount_out > 0:
                if is_x_to_y:
                    avg_exec_price = total_amount_out / amount_in
                    price_impact = abs(avg_exec_price - self.pool.config.active_price) / self.pool.config.active_price * 100
                else:
                    avg_exec_price = amount_in / total_amount_out
                    price_impact = abs(avg_exec_price - self.pool.config.active_price) / self.pool.config.active_price * 100
            else:
                price_impact = 0
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=total_amount_out,
                steps=steps,
                total_price_impact=price_impact,
                success=False,
                error_message=f"Insufficient output: {total_amount_out} < {min_amount_out}"
            )

        # Calculate average price impact for the whole swap
        if total_amount_out > 0:
            # Calculate actual amount that was successfully swapped
            actual_amount_swapped = amount_in - remaining_amount if remaining_amount > 0 else amount_in
            
            if is_x_to_y:
                avg_exec_price = total_amount_out / actual_amount_swapped
                price_impact = abs(avg_exec_price - self.pool.config.active_price) / self.pool.config.active_price * 100
            else:
                avg_exec_price = actual_amount_swapped / total_amount_out
                price_impact = abs(avg_exec_price - self.pool.config.active_price) / self.pool.config.active_price * 100
        else:
            price_impact = 0

        return RouteResult(
            total_amount_in=amount_in,
            total_amount_out=total_amount_out,
            steps=steps,
            total_price_impact=price_impact,
            success=True
        )


class MultiPoolRouter:
    """Router for multi-pool operations."""
    
    def __init__(self, pools: Dict[str, MockPool]):
        self.pools = pools
        self.math = DLMMMath()
    
    def get_quote(self, token_in: str, amount_in: float, token_out: str, max_hops: int = 3) -> RouteResult:
        """
        Get a quote for swapping tokens across multiple pools.
        
        Args:
            token_in: Input token symbol
            amount_in: Amount of input token
            token_out: Output token symbol
            max_hops: Maximum number of hops allowed
        
        Returns:
            RouteResult with quote details
        """
        # Check if this is a same trading pair scenario (multiple pools for same token pair)
        same_pair_pools = []
        for pool_id, pool in self.pools.items():
            if (pool.config.x_token == token_in and pool.config.y_token == token_out) or \
               (pool.config.y_token == token_in and pool.config.x_token == token_out):
                same_pair_pools.append(pool_id)
        
        # If we have multiple pools for the same trading pair, use same-pair routing
        if len(same_pair_pools) > 1:
            return self.get_quote_same_pair_multi_pool(token_in, amount_in, token_out)
        
        # Otherwise, use the existing multi-hop pathfinding logic
        # Find all possible paths
        paths = self._find_paths(token_in, token_out, max_hops)
        
        if not paths:
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=0,
                steps=[],
                total_price_impact=0,
                success=False,
                error_message="No valid path found"
            )
        
        # Calculate quotes for each path
        best_quote = None
        best_amount_out = 0
        
        for path in paths:
            quote = self._calculate_path_quote(path, amount_in)
            if quote.success and quote.total_amount_out > best_amount_out:
                best_quote = quote
                best_amount_out = quote.total_amount_out
        
        if best_quote is None:
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=0,
                steps=[],
                total_price_impact=0,
                success=False,
                error_message="No valid quote found"
            )
        
        return best_quote
    
    def _find_paths(self, token_in: str, token_out: str, max_hops: int) -> List[List[str]]:
        """
        Find all possible paths between two tokens.
        
        Args:
            token_in: Input token
            token_out: Output token
            max_hops: Maximum number of hops
        
        Returns:
            List of paths (each path is a list of pool IDs)
        """
        paths = []
        
        # Direct paths (1 hop)
        for pool_id, pool in self.pools.items():
            if (pool.config.x_token == token_in and pool.config.y_token == token_out) or \
               (pool.config.y_token == token_in and pool.config.x_token == token_out):
                paths.append([pool_id])
        
        # Multi-hop paths (2+ hops)
        if max_hops > 1:
            # This is a simplified implementation
            # In practice, you'd want to use a more sophisticated pathfinding algorithm
            for pool1_id, pool1 in self.pools.items():
                for pool2_id, pool2 in self.pools.items():
                    if pool1_id != pool2_id:
                        # Check if pools can be connected
                        if (pool1.config.x_token == token_in and pool1.config.y_token == pool2.config.x_token and pool2.config.y_token == token_out) or \
                           (pool1.config.y_token == token_in and pool1.config.x_token == pool2.config.x_token and pool2.config.y_token == token_out) or \
                           (pool1.config.x_token == token_in and pool1.config.y_token == pool2.config.y_token and pool2.config.x_token == token_out) or \
                           (pool1.config.y_token == token_in and pool1.config.x_token == pool2.config.y_token and pool2.config.x_token == token_out):
                            paths.append([pool1_id, pool2_id])
        
        return paths
    
    def _calculate_path_quote(self, path: List[str], amount_in: float) -> RouteResult:
        """
        Calculate quote for a specific path.
        
        Args:
            path: List of pool IDs representing the path
            amount_in: Amount of input token
        
        Returns:
            RouteResult with quote details
        """
        current_amount = amount_in
        all_steps = []
        total_price_impact = 0
        
        for i, pool_id in enumerate(path):
            pool = self.pools[pool_id]
            
            # Determine input and output tokens for this hop
            if i == 0:
                # First hop: determine which token to use based on what's available
                if pool.config.x_token in [pool.config.x_token, pool.config.y_token]:
                    token_in = pool.config.x_token
                    token_out = pool.config.y_token
                else:
                    token_in = pool.config.y_token
                    token_out = pool.config.x_token
            else:
                # Subsequent hops: use the output from previous hop
                if len(all_steps) > 0:
                    token_in = all_steps[-1].token_out
                    token_out = self._get_output_token(pool, token_in)
                else:
                    # Fallback if no previous steps
                    token_in = pool.config.x_token
                    token_out = pool.config.y_token
            
            # Create single pool router for this hop
            router = SinglePoolRouter(pool)
            
            # Get quote for this hop (fee is now per bin in SinglePoolRouter)
            hop_quote = router.get_quote(token_in, current_amount, token_out)
            
            if not hop_quote.success:
                return RouteResult(
                    total_amount_in=amount_in,
                    total_amount_out=0,
                    steps=all_steps + hop_quote.steps,
                    total_price_impact=total_price_impact + hop_quote.total_price_impact,
                    success=False,
                    error_message=f"Hop {i+1} failed: {hop_quote.error_message}"
                )
            
            # Update for next hop: use the ACTUAL amount swapped (not input) for next pool
            current_amount = hop_quote.total_amount_out
            all_steps.extend(hop_quote.steps)
            total_price_impact += hop_quote.total_price_impact
        
        return RouteResult(
            total_amount_in=amount_in,
            total_amount_out=current_amount,
            steps=all_steps,
            total_price_impact=total_price_impact,
            success=True
        )
    
    def _get_input_token(self, pool: MockPool, amount: float) -> str:
        """Helper to determine input token for a pool."""
        # This is simplified - in practice you'd need more logic
        return pool.config.x_token
    
    def _get_output_token(self, pool: MockPool, token_in: str) -> str:
        """Helper to determine output token for a pool."""
        if pool.config.x_token == token_in:
            return pool.config.y_token
        else:
            return pool.config.x_token

    def get_quote_same_pair_multi_pool(self, token_in: str, amount_in: float, token_out: str) -> RouteResult:
        """
        Get a quote for swapping tokens across multiple pools of the same trading pair.
        
        This method splits the input amount across multiple pools to get the best total output.
        
        Args:
            token_in: Input token symbol
            amount_in: Amount of input token
            token_out: Output token symbol
        
        Returns:
            RouteResult with quote details
        """
        # Find all pools that support this trading pair
        matching_pools = []
        for pool_id, pool in self.pools.items():
            if (pool.config.x_token == token_in and pool.config.y_token == token_out) or \
               (pool.config.y_token == token_in and pool.config.x_token == token_out):
                matching_pools.append((pool_id, pool))
        
        if not matching_pools:
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=0,
                steps=[],
                total_price_impact=0,
                success=False,
                error_message="No pools found for this trading pair"
            )
        
        # If only one pool, use single pool router
        if len(matching_pools) == 1:
            pool_id, pool = matching_pools[0]
            router = SinglePoolRouter(pool)
            return router.get_quote(token_in, amount_in, token_out)
        
        # For multiple pools, implement optimal splitting
        # Strategy: Try different splits and pick the best result
        best_result = None
        best_total_output = 0
        
        # Try different split ratios
        split_ratios = [0.5, 0.6, 0.7, 0.8, 0.9]  # Different ways to split between pools
        
        for ratio in split_ratios:
            # Split amount between the two pools
            amount1 = amount_in * ratio
            amount2 = amount_in * (1 - ratio)
            
            # Get quotes from both pools
            pool1_id, pool1 = matching_pools[0]
            pool2_id, pool2 = matching_pools[1]
            
            router1 = SinglePoolRouter(pool1)
            router2 = SinglePoolRouter(pool2)
            
            quote1 = router1.get_quote(token_in, amount1, token_out)
            quote2 = router2.get_quote(token_in, amount2, token_out)
            
            # If both quotes succeed, combine them
            if quote1.success and quote2.success:
                total_output = quote1.total_amount_out + quote2.total_amount_out
                total_price_impact = (quote1.total_price_impact + quote2.total_price_impact) / 2
                
                # Combine steps from both pools
                all_steps = []
                
                # Update pool_id in steps to distinguish between pools
                for step in quote1.steps:
                    step.pool_id = pool1_id
                    all_steps.append(step)
                
                for step in quote2.steps:
                    step.pool_id = pool2_id
                    all_steps.append(step)
                
                result = RouteResult(
                    total_amount_in=amount_in,
                    total_amount_out=total_output,
                    steps=all_steps,
                    total_price_impact=total_price_impact,
                    success=True
                )
                
                if total_output > best_total_output:
                    best_result = result
                    best_total_output = total_output
        
        # If no successful split found, try single pool approach as fallback
        if best_result is None:
            for pool_id, pool in matching_pools:
                router = SinglePoolRouter(pool)
                quote = router.get_quote(token_in, amount_in, token_out)
                
                if quote.success and quote.total_amount_out > best_total_output:
                    # Update pool_id in steps
                    for step in quote.steps:
                        step.pool_id = pool_id
                    
                    best_result = quote
                    best_total_output = quote.total_amount_out
        
        if best_result is None:
            return RouteResult(
                total_amount_in=amount_in,
                total_amount_out=0,
                steps=[],
                total_price_impact=0,
                success=False,
                error_message="No valid quote found in any pool"
            )
        
        return best_result 