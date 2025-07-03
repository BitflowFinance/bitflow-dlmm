"""
Comprehensive demo of all quote functions with formula verification.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.pool import MockPool, PoolConfig
from src.routing import SinglePoolRouter, MultiPoolRouter
from src.utils import print_route_result, print_pool_analysis, create_test_pools, print_route_comparison
from src.math import DLMMMath


def demo_single_bin_quotes():
    """Demonstrate single bin quote functions."""
    print("=" * 60)
    print("1. SINGLE BIN QUOTES")
    print("=" * 60)
    
    pool = MockPool.create_bell_curve_pool()
    router = SinglePoolRouter(pool)
    active_bin = pool.get_active_bin()
    
    print(f"Active Bin: {active_bin.bin_id} at ${active_bin.price:,.2f}")
    print(f"Available X (BTC): {active_bin.x_amount:.6f}")
    print(f"Available Y (USDC): {active_bin.y_amount:.2f}")
    print()
    
    # Test 1: get-x-for-y (BTC to USDC)
    print("--- get-x-for-y (BTC to USDC) ---")
    amount_in = 0.1  # 0.1 BTC
    result = router.get_quote("BTC", amount_in, "USDC")
    
    print(f"Input: {amount_in} BTC")
    print(f"Output: {result.total_amount_out:.6f} USDC")
    print(f"Formula: Δy = min(Δx, x_i) = min({amount_in}, {active_bin.x_amount:.6f}) = {result.total_amount_out:.6f}")
    print(f"1:1 ratio verified: {abs(result.total_amount_out - amount_in) < 0.001}")
    print()
    
    # Test 2: get-y-for-x (USDC to BTC)
    print("--- get-y-for-x (USDC to BTC) ---")
    amount_in = 1000  # 1000 USDC
    result = router.get_quote("USDC", amount_in, "BTC")
    
    print(f"Input: {amount_in} USDC")
    print(f"Output: {result.total_amount_out:.6f} BTC")
    print(f"Formula: Δx = min(Δy, y_i) = min({amount_in}, {active_bin.y_amount:.2f}) = {result.total_amount_out:.6f}")
    print(f"1:1 ratio verified: {abs(result.total_amount_out - amount_in) < 0.001}")
    print()


def demo_multi_bin_quotes():
    """Demonstrate multi-bin quote functions."""
    print("=" * 60)
    print("2. MULTI-BIN QUOTES")
    print("=" * 60)
    
    pool = MockPool.create_bell_curve_pool()
    router = SinglePoolRouter(pool)
    
    # Test 1: get-x-for-y across multiple bins
    print("--- get-x-for-y across multiple bins ---")
    amount_in = 5.0  # 5 BTC
    result = router.get_quote("BTC", amount_in, "USDC")
    
    print(f"Input: {amount_in} BTC")
    print(f"Output: {result.total_amount_out:.6f} USDC")
    print(f"Steps used: {len(result.steps)}")
    print(f"Total price impact: {result.total_price_impact:.4f}%")
    
    print("\nStep details:")
    for i, step in enumerate(result.steps):
        print(f"  Step {i+1}: Bin {step.bin_id}, Price ${step.price:,.2f}")
        print(f"    Used: {step.amount_in:.6f} BTC → {step.amount_out:.6f} USDC")
        print(f"    Price impact: {step.price_impact:.4f}%")
    
    # Verify formula: Δy_total = Σ min(Δx_j, x_j)
    total_expected = sum(step.amount_out for step in result.steps)
    print(f"\nFormula verification: Δy_total = Σ min(Δx_j, x_j) = {total_expected:.6f}")
    print(f"Actual output: {result.total_amount_out:.6f}")
    print(f"Match: {abs(total_expected - result.total_amount_out) < 0.001}")
    print()
    
    # Test 2: get-y-for-x across multiple bins
    print("--- get-y-for-x across multiple bins ---")
    amount_in = 100000  # 100k USDC
    result = router.get_quote("USDC", amount_in, "BTC")
    
    print(f"Input: {amount_in} USDC")
    print(f"Output: {result.total_amount_out:.6f} BTC")
    print(f"Steps used: {len(result.steps)}")
    print(f"Total price impact: {result.total_price_impact:.4f}%")
    
    print("\nStep details:")
    for i, step in enumerate(result.steps):
        print(f"  Step {i+1}: Bin {step.bin_id}, Price ${step.price:,.2f}")
        print(f"    Used: {step.amount_in:.2f} USDC → {step.amount_out:.6f} BTC")
        print(f"    Price impact: {step.price_impact:.4f}%")
    
    # Verify bin sequence (should be ascending for Y→X)
    bin_ids = [step.bin_id for step in result.steps]
    print(f"\nBin sequence verification:")
    print(f"  Bin IDs: {bin_ids}")
    print(f"  All bins > active bin: {all(bin_id > pool.config.active_bin_id for bin_id in bin_ids)}")
    print(f"  Ascending order: {bin_ids == sorted(bin_ids)}")
    print()


def demo_multi_pool_same_pair_quotes():
    """Demonstrate multi-pool quotes for same trading pair."""
    print("=" * 60)
    print("3. MULTI-POOL SAME PAIR QUOTES")
    print("=" * 60)
    
    # Create two BTC/USDC pools with different configurations
    config1 = PoolConfig(
        active_bin_id=500,
        active_price=100000.0,
        bin_step=0.001,
        x_token="BTC",
        y_token="USDC"
    )
    
    config2 = PoolConfig(
        active_bin_id=500,
        active_price=100100.0,  # Slightly different price
        bin_step=0.002,        # Different bin step
        x_token="BTC",
        y_token="USDC"
    )
    
    pools = {
        "BTC-USDC-1": MockPool(config1),
        "BTC-USDC-2": MockPool(config2)
    }
    
    router = MultiPoolRouter(pools)
    
    # Test multi-pool routing
    print("--- Multi-pool BTC to USDC ---")
    amount_in = 2.0  # 2 BTC
    result = router.get_quote("BTC", amount_in, "USDC", max_hops=2)
    
    print(f"Input: {amount_in} BTC")
    print(f"Output: {result.total_amount_out:.6f} USDC")
    print(f"Steps used: {len(result.steps)}")
    print(f"Pools used: {set(step.pool_id for step in result.steps)}")
    
    print("\nStep details:")
    for i, step in enumerate(result.steps):
        print(f"  Step {i+1}: Pool {step.pool_id}, Bin {step.bin_id}")
        print(f"    {step.token_in} → {step.token_out}: {step.amount_in:.6f} → {step.amount_out:.6f}")
        print(f"    Price: ${step.price:,.2f}, Impact: {step.price_impact:.4f}%")
    
    # Verify formula: Δy_total = Σ_p Σ_j min(Δx_p,j, x_p,j)
    total_expected = sum(step.amount_out for step in result.steps)
    print(f"\nFormula verification: Δy_total = Σ_p Σ_j min(Δx_p,j, x_p,j) = {total_expected:.6f}")
    print(f"Actual output: {result.total_amount_out:.6f}")
    print(f"Match: {abs(total_expected - result.total_amount_out) < 0.001}")
    print()


def demo_cross_pair_quotes():
    """Demonstrate cross-pair quotes."""
    print("=" * 60)
    print("4. CROSS-PAIR QUOTES")
    print("=" * 60)
    
    pools = create_test_pools()
    router = MultiPoolRouter(pools)
    
    # Test ETH to USDC via multiple paths
    print("--- ETH to USDC (multiple paths) ---")
    amount_in = 10.0  # 10 ETH
    
    # Test different hop limits
    results = {}
    for max_hops in [1, 2, 3]:
        result = router.get_quote("ETH", amount_in, "USDC", max_hops=max_hops)
        results[max_hops] = result
        print(f"Max {max_hops} hop(s): {result.total_amount_out:.6f} USDC")
    
    # Show best path
    best_hops = max(results.keys(), key=lambda h: results[h].total_amount_out)
    best_result = results[best_hops]
    
    print(f"\nBest path ({best_hops} hops): {best_result.total_amount_out:.6f} USDC")
    print(f"Steps used: {len(best_result.steps)}")
    
    print("\nPath details:")
    for i, step in enumerate(best_result.steps):
        print(f"  Step {i+1}: Pool {step.pool_id}, Bin {step.bin_id}")
        print(f"    {step.token_in} → {step.token_out}: {step.amount_in:.6f} → {step.amount_out:.6f}")
        print(f"    Price: ${step.price:,.2f}, Impact: {step.price_impact:.4f}%")
    
    # Verify path makes sense
    tokens_in_path = [step.token_in for step in best_result.steps]
    tokens_out_path = [step.token_out for step in best_result.steps]
    print(f"\nPath verification:")
    print(f"  Start: {tokens_in_path[0]}")
    print(f"  End: {tokens_out_path[-1]}")
    print(f"  Valid path: {tokens_in_path[0] == 'ETH' and tokens_out_path[-1] == 'USDC'}")
    
    # Test reverse direction
    print("\n--- USDC to ETH (reverse) ---")
    amount_in = 30000  # 30k USDC
    result = router.get_quote("USDC", amount_in, "ETH", max_hops=3)
    
    print(f"Input: {amount_in} USDC")
    print(f"Output: {result.total_amount_out:.6f} ETH")
    print(f"Steps used: {len(result.steps)}")
    
    print("\nPath details:")
    for i, step in enumerate(result.steps):
        print(f"  Step {i+1}: Pool {step.pool_id}, Bin {step.bin_id}")
        print(f"    {step.token_in} → {step.token_out}: {step.amount_in:.2f} → {step.amount_out:.6f}")
        print(f"    Price: ${step.price:,.2f}, Impact: {step.price_impact:.4f}%")
    print()


def demo_price_impact_calculation():
    """Demonstrate price impact calculations."""
    print("=" * 60)
    print("5. PRICE IMPACT CALCULATIONS")
    print("=" * 60)
    
    pool = MockPool.create_bell_curve_pool()
    router = SinglePoolRouter(pool)
    active_price = pool.config.active_price
    
    print(f"Active price: ${active_price:,.2f}")
    print()
    
    # Test different trade sizes
    trade_sizes = [0.1, 1.0, 5.0, 10.0]
    
    for amount_in in trade_sizes:
        result = router.get_quote("BTC", amount_in, "USDC")
        
        # Calculate effective price
        effective_price = result.total_amount_out / result.total_amount_in
        
        # Calculate price impact
        price_impact = abs(effective_price - active_price) / active_price * 100
        
        print(f"Trade size: {amount_in} BTC")
        print(f"  Output: {result.total_amount_out:.6f} USDC")
        print(f"  Effective price: ${effective_price:,.2f}")
        print(f"  Price impact: {price_impact:.4f}%")
        print(f"  Formula: |P_effective - P_active| / P_active × 100% = |{effective_price:.2f} - {active_price:.2f}| / {active_price:.2f} × 100% = {price_impact:.4f}%")
        print()


def demo_slippage_calculation():
    """Demonstrate slippage calculations."""
    print("=" * 60)
    print("6. SLIPPAGE CALCULATIONS")
    print("=" * 60)
    
    pool = MockPool.create_bell_curve_pool()
    router = SinglePoolRouter(pool)
    active_price = pool.config.active_price
    
    print(f"Active price: ${active_price:,.2f}")
    print()
    
    # Test different trade sizes
    trade_sizes = [0.1, 1.0, 5.0]
    
    for amount_in in trade_sizes:
        result = router.get_quote("BTC", amount_in, "USDC")
        
        # Calculate expected output
        expected_output = amount_in * active_price
        actual_output = result.total_amount_out
        
        # Calculate slippage
        slippage = abs(expected_output - actual_output) / expected_output * 100
        
        print(f"Trade size: {amount_in} BTC")
        print(f"  Expected output: {expected_output:.6f} USDC")
        print(f"  Actual output: {actual_output:.6f} USDC")
        print(f"  Slippage: {slippage:.4f}%")
        print(f"  Formula: |Δy_expected - Δy_actual| / Δy_expected × 100% = |{expected_output:.6f} - {actual_output:.6f}| / {expected_output:.6f} × 100% = {slippage:.4f}%")
        print()


def main():
    """Run comprehensive quote function demo."""
    print("DLMM QUOTE FUNCTIONS COMPREHENSIVE DEMO")
    print("=" * 60)
    print("This demo showcases all quote functions with formula verification.")
    print()
    
    # Run all demos
    demo_single_bin_quotes()
    demo_multi_bin_quotes()
    demo_multi_pool_same_pair_quotes()
    demo_cross_pair_quotes()
    demo_price_impact_calculation()
    demo_slippage_calculation()
    
    print("=" * 60)
    print("DEMO COMPLETED")
    print("=" * 60)
    print("All quote functions have been demonstrated with formula verification.")
    print("Check the README.md for detailed mathematical formulas.")


if __name__ == "__main__":
    main() 