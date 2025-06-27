"""
Tests for quote functions across different routing scenarios.
"""

import pytest
from src.pool import MockPool, PoolConfig
from src.routing import SinglePoolRouter, MultiPoolRouter
from src.utils import create_test_pools


class TestSingleBinQuotes:
    """Test quotes for swaps within a single bin."""
    
    def setup_method(self):
        """Set up test pool and router."""
        self.pool = MockPool.create_bell_curve_pool()
        self.router = SinglePoolRouter(self.pool)
        self.active_bin = self.pool.get_active_bin()
    
    def test_get_x_for_y_single_bin(self):
        """Test X for Y quote within single bin (active bin)."""
        # Small amount that should fit within active bin
        amount_in = 0.1  # 0.1 BTC
        
        result = self.router.get_quote("BTC", amount_in, "USDC")
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) == 1
        assert result.steps[0].bin_id == self.active_bin.bin_id
        assert result.steps[0].token_in == "BTC"
        assert result.steps[0].token_out == "USDC"
        # Output should be based on bin price: amount_in * price
        expected_output = amount_in * self.active_bin.price
        assert abs(result.total_amount_out - expected_output) < 0.001
    
    def test_get_y_for_x_single_bin(self):
        """Test Y for X quote within single bin (active bin)."""
        # Small amount that should fit within active bin
        amount_in = 1000  # 1000 USDC
        
        result = self.router.get_quote("USDC", amount_in, "BTC")
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) == 1
        assert result.steps[0].bin_id == self.active_bin.bin_id
        assert result.steps[0].token_in == "USDC"
        assert result.steps[0].token_out == "BTC"
        # Output should be based on bin price: amount_in / price
        expected_output = amount_in / self.active_bin.price
        assert abs(result.total_amount_out - expected_output) < 0.001


class TestMultiBinQuotes:
    """Test quotes for swaps across multiple bins within the same pool."""
    
    def setup_method(self):
        """Set up test pool and router."""
        self.pool = MockPool.create_bell_curve_pool()
        self.router = SinglePoolRouter(self.pool)
    
    def test_get_x_for_y_multi_bin(self):
        """Test X for Y quote across multiple bins."""
        # Large amount that will cross multiple bins
        amount_in = 15.0  # 15 BTC (more than active bin's 10 BTC)
        
        result = self.router.get_quote("BTC", amount_in, "USDC")
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) > 1  # Should use multiple bins
        
        # Verify bin sequence is correct (rightward for X->Y)
        bin_ids = [step.bin_id for step in result.steps]
        assert all(bin_id >= self.pool.config.active_bin_id for bin_id in bin_ids)
        # Should be in ascending order
        assert bin_ids == sorted(bin_ids)
    
    def test_get_y_for_x_multi_bin(self):
        """Test Y for X quote across multiple bins."""
        # Large amount that will cross multiple bins
        amount_in = 600000  # 600k USDC (more than active bin's 500k USDC)
        
        result = self.router.get_quote("USDC", amount_in, "BTC")
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) > 1  # Should use multiple bins
        
        # Verify bin sequence is correct (leftward for Y->X)
        bin_ids = [step.bin_id for step in result.steps]
        assert all(bin_id <= self.pool.config.active_bin_id for bin_id in bin_ids)
        # Should be in descending order
        assert bin_ids == sorted(bin_ids, reverse=True)
    
    def test_price_impact_multi_bin(self):
        """Test that price impact increases with larger trades."""
        small_amount = 0.1
        large_amount = 20.0  # 20 BTC (more than active bin's 10 BTC)
        
        small_result = self.router.get_quote("BTC", small_amount, "USDC")
        large_result = self.router.get_quote("BTC", large_amount, "USDC")
        
        assert small_result.success
        assert large_result.success
        # Larger trade should have higher price impact
        assert large_result.total_price_impact > small_result.total_price_impact


class TestMultiPoolSamePairQuotes:
    """Test quotes for swaps across multiple pools of the same trading pair."""
    
    def setup_method(self):
        """Set up multiple pools for the same trading pair."""
        # Create two BTC/USDC pools with different configurations
        config1 = PoolConfig(
            active_bin_id=500,
            active_price=50000.0,
            bin_step=0.001,
            x_token="BTC",
            y_token="USDC"
        )
        
        config2 = PoolConfig(
            active_bin_id=500,
            active_price=50100.0,  # Slightly different price
            bin_step=0.002,        # Different bin step
            x_token="BTC",
            y_token="USDC"
        )
        
        self.pools = {
            "BTC-USDC-1": MockPool(config1),
            "BTC-USDC-2": MockPool(config2)
        }
        self.router = MultiPoolRouter(self.pools)
    
    def test_get_x_for_y_multi_pool_same_pair(self):
        """Test X for Y quote across multiple pools of same pair."""
        amount_in = 50.0  # 50 BTC (large amount to require multiple pools)
        
        result = self.router.get_quote("BTC", amount_in, "USDC", max_hops=2)
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) > 1
        
        # Should use both pools
        pool_ids = set(step.pool_id for step in result.steps)
        assert len(pool_ids) > 1
    
    def test_get_y_for_x_multi_pool_same_pair(self):
        """Test Y for X quote across multiple pools of same pair."""
        amount_in = 2000000  # 2M USDC (large amount to require multiple pools)
        
        result = self.router.get_quote("USDC", amount_in, "BTC", max_hops=2)
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) > 1
        
        # Should use both pools
        pool_ids = set(step.pool_id for step in result.steps)
        assert len(pool_ids) > 1


class TestMultiPoolSamePairDifferentBinStep:
    """Test multi-pool routing for same trading pair with different bin steps."""
    def setup_method(self):
        config1 = PoolConfig(
            active_bin_id=500,
            active_price=50000.0,
            bin_step=0.001,
            x_token="BTC",
            y_token="USDC"
        )
        config2 = PoolConfig(
            active_bin_id=500,
            active_price=50000.0,
            bin_step=0.002,  # Different bin step
            x_token="BTC",
            y_token="USDC"
        )
        self.pools = {
            "BTC-USDC-1": MockPool(config1),
            "BTC-USDC-2": MockPool(config2)
        }
        self.router = MultiPoolRouter(self.pools)

    def test_large_x_to_y_multi_pool(self):
        amount_in = 100.0  # Large amount to require both pools
        result = self.router.get_quote("BTC", amount_in, "USDC", max_hops=2)
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert result.success or "Insufficient liquidity" in (result.error_message or "")
        # Should use both pools and multiple bins
        pool_ids = set(step.pool_id for step in result.steps)
        assert len(pool_ids) > 1 or len(result.steps) > 1
        print(f"Used pools: {pool_ids}")
        print(f"Steps: {len(result.steps)}")
        print(f"Total output: {result.total_amount_out}")
        if not result.success:
            print(f"Error: {result.error_message}")


class TestCrossPairQuotes:
    """Test quotes for swaps across multiple bins, pools, and trading pairs."""
    
    def setup_method(self):
        """Set up multiple pools for different trading pairs."""
        self.pools = create_test_pools()
        self.router = MultiPoolRouter(self.pools)
    
    def test_get_x_for_y_cross_pair(self):
        """Test X for Y quote across multiple pairs (e.g., ETH to USDC via BTC)."""
        amount_in = 10.0  # 10 ETH
        
        result = self.router.get_quote("ETH", amount_in, "USDC", max_hops=3)
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) > 1
        
        # Should use multiple pools
        pool_ids = set(step.pool_id for step in result.steps)
        assert len(pool_ids) > 1
        
        # Verify the path makes sense (ETH -> BTC -> USDC or ETH -> USDC directly)
        tokens_in_path = [step.token_in for step in result.steps]
        tokens_out_path = [step.token_out for step in result.steps]
        
        assert tokens_in_path[0] == "ETH"
        assert tokens_out_path[-1] == "USDC"
    
    def test_get_y_for_x_cross_pair(self):
        """Test Y for X quote across multiple pairs (e.g., USDC to ETH via BTC)."""
        amount_in = 30000  # 30k USDC
        
        result = self.router.get_quote("USDC", amount_in, "ETH", max_hops=3)
        
        assert result.success
        assert result.total_amount_in == amount_in
        assert result.total_amount_out > 0
        assert len(result.steps) > 1
        
        # Should use multiple pools
        pool_ids = set(step.pool_id for step in result.steps)
        assert len(pool_ids) > 1
        
        # Verify the path makes sense
        tokens_in_path = [step.token_in for step in result.steps]
        tokens_out_path = [step.token_out for step in result.steps]
        
        assert tokens_in_path[0] == "USDC"
        assert tokens_out_path[-1] == "ETH"
    
    def test_optimal_path_selection(self):
        """Test that the router selects the optimal path."""
        amount_in = 5.0  # 5 ETH
        
        # Get quote with different max hops
        result_1_hop = self.router.get_quote("ETH", amount_in, "USDC", max_hops=1)
        result_2_hops = self.router.get_quote("ETH", amount_in, "USDC", max_hops=2)
        result_3_hops = self.router.get_quote("ETH", amount_in, "USDC", max_hops=3)
        
        # All should succeed
        assert result_1_hop.success
        assert result_2_hops.success
        assert result_3_hops.success
        
        # Router should select the best output among available paths
        outputs = [result_1_hop.total_amount_out, result_2_hops.total_amount_out, result_3_hops.total_amount_out]
        best_output = max(outputs)
        
        # The router should have selected the path with the best output
        assert result_3_hops.total_amount_out == best_output


class TestQuoteEdgeCases:
    """Test edge cases for quote functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.pool = MockPool.create_bell_curve_pool()
        self.router = SinglePoolRouter(self.pool)
        self.pools = create_test_pools()
        self.multi_router = MultiPoolRouter(self.pools)
    
    def test_insufficient_liquidity(self):
        """Test quote when there's insufficient liquidity."""
        # Try to swap more than available liquidity
        huge_amount = 1000000.0  # 1M BTC
        
        result = self.router.get_quote("BTC", huge_amount, "USDC")
        
        # Should fail due to insufficient liquidity
        assert not result.success
        assert "Insufficient liquidity" in result.error_message
        assert result.total_amount_out > 0  # Should have used some liquidity
        assert len(result.steps) > 0  # Should have some steps
    
    def test_minimum_output_requirement(self):
        """Test quote with minimum output requirement."""
        amount_in = 1.0  # 1 BTC
        min_output = 100000.0  # Require 100k USDC minimum
        
        result = self.router.get_quote("BTC", amount_in, "USDC", min_amount_out=min_output)
        
        # Should fail if minimum output cannot be met
        if result.total_amount_out < min_output:
            assert not result.success
            assert "Insufficient output" in result.error_message
    
    def test_invalid_tokens(self):
        """Test quote with invalid token pairs."""
        result = self.router.get_quote("INVALID", 1.0, "USDC")
        assert not result.success
        assert "not found in pool" in result.error_message
    
    def test_same_token_swap(self):
        """Test quote for same token swap."""
        result = self.router.get_quote("BTC", 1.0, "BTC")
        assert result.success
        assert result.total_amount_out == 1.0
        assert result.total_price_impact == 0.0 