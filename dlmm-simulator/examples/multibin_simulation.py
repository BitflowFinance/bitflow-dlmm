#!/usr/bin/env python3
"""
Multi-bin routing simulation in a single pool.

This script demonstrates how DLMM routes swaps across multiple bins within a single pool,
showing the detailed quote results including token amounts and price impact.
"""

from src.pool import MockPool, PoolConfig
from src.routing import SinglePoolRouter
from src.math import DLMMMath
import json


def print_quote_details(quote, title=""):
    """Print detailed quote information in a formatted way."""
    print(f"\n{'='*60}")
    if title:
        print(f"{title}")
        print(f"{'='*60}")
    
    print(f"Input Amount: {quote.total_amount_in}")
    print(f"Output Amount: {quote.total_amount_out:.2f}")
    print(f"Success: {quote.success}")
    print(f"Total Price Impact: {quote.total_price_impact:.4f}%")
    
    if not quote.success and quote.error_message:
        print(f"Error: {quote.error_message}")
    
    print(f"\nSteps ({len(quote.steps)} bins used):")
    print("-" * 80)
    print(f"{'Bin ID':<8} {'Token In':<8} {'Token Out':<8} {'Amount In':<12} {'Amount Out':<12} {'Price':<10} {'Price Impact':<12}")
    print("-" * 80)
    
    for i, step in enumerate(quote.steps):
        print(f"{step.bin_id:<8} {step.token_in:<8} {step.token_out:<8} "
              f"{step.amount_in:<12.4f} {step.amount_out:<12.2f} "
              f"{step.price:<10.2f} {step.price_impact:<12.4f}%")
    
    print("-" * 80)


def simulate_multibin_routing():
    """Simulate multi-bin routing scenarios."""
    
    # Create a pool with bell curve liquidity distribution
    pool = MockPool.create_bell_curve_pool()
    router = SinglePoolRouter(pool)
    
    print("DLMM Multi-Bin Routing Simulation")
    print("=" * 60)
    print(f"Pool: {pool.config.x_token}/{pool.config.y_token}")
    print(f"Active Bin: {pool.config.active_bin_id}")
    print(f"Active Price: ${pool.config.active_price:,.2f}")
    print(f"Bin Step: {pool.config.bin_step}")
    
    # Show pool liquidity distribution
    active_bin = pool.get_bin(pool.config.active_bin_id)
    print(f"\nActive Bin Liquidity:")
    print(f"  X tokens: {active_bin.x_amount:.2f} {pool.config.x_token}")
    print(f"  Y tokens: {active_bin.y_amount:.2f} {pool.config.y_token}")
    print(f"  Price: ${active_bin.price:,.2f}")
    
    # Test 1: Small amount (single bin)
    print("\n" + "="*60)
    print("TEST 1: Small Amount (Single Bin)")
    print("="*60)
    
    small_amount = 0.5  # 0.5 BTC
    quote1 = router.get_quote("BTC", small_amount, "USDC")
    print_quote_details(quote1, "BTC → USDC (Small Amount)")
    
    # Test 2: Medium amount (multiple bins)
    print("\n" + "="*60)
    print("TEST 2: Medium Amount (Multiple Bins)")
    print("="*60)
    
    medium_amount = 15.0  # 15 BTC
    quote2 = router.get_quote("BTC", medium_amount, "USDC")
    print_quote_details(quote2, "BTC → USDC (Medium Amount)")
    
    # Test 3: Large amount (many bins)
    print("\n" + "="*60)
    print("TEST 3: Large Amount (Many Bins)")
    print("="*60)
    
    large_amount = 50.0  # 50 BTC
    quote3 = router.get_quote("BTC", large_amount, "USDC")
    print_quote_details(quote3, "BTC → USDC (Large Amount)")
    
    # Test 4: Reverse direction (Y → X)
    print("\n" + "="*60)
    print("TEST 4: Reverse Direction (Y → X)")
    print("="*60)
    
    usdc_amount = 1000000  # 1M USDC
    quote4 = router.get_quote("USDC", usdc_amount, "BTC")
    print_quote_details(quote4, "USDC → BTC (Large Amount)")
    
    # Test 5: Insufficient liquidity
    print("\n" + "="*60)
    print("TEST 5: Insufficient Liquidity")
    print("="*60)
    
    huge_amount = 1000000.0  # 1M BTC
    quote5 = router.get_quote("BTC", huge_amount, "USDC")
    print_quote_details(quote5, "BTC → USDC (Insufficient Liquidity)")
    
    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    successful_quotes = [q for q in [quote1, quote2, quote3, quote4] if q.success]
    
    print(f"Successful Quotes: {len(successful_quotes)}/5")
    print(f"Average Price Impact: {sum(q.total_price_impact for q in successful_quotes) / len(successful_quotes):.4f}%")
    print(f"Total Bins Used: {sum(len(q.steps) for q in successful_quotes)}")
    
    # Show price impact vs trade size
    print(f"\nPrice Impact Analysis:")
    print("-" * 40)
    for i, quote in enumerate([quote1, quote2, quote3, quote4], 1):
        if quote.success:
            print(f"Test {i}: {quote.total_amount_in} → {quote.total_price_impact:.4f}% impact")
    
    # Export detailed results to JSON
    results = {
        "pool_config": {
            "x_token": pool.config.x_token,
            "y_token": pool.config.y_token,
            "active_bin_id": pool.config.active_bin_id,
            "active_price": pool.config.active_price,
            "bin_step": pool.config.bin_step
        },
        "quotes": [
            {
                "test": "Small Amount",
                "input": quote1.total_amount_in,
                "output": quote1.total_amount_out,
                "success": quote1.success,
                "price_impact": quote1.total_price_impact,
                "bins_used": len(quote1.steps),
                "steps": [
                    {
                        "bin_id": step.bin_id,
                        "amount_in": step.amount_in,
                        "amount_out": step.amount_out,
                        "price": step.price,
                        "price_impact": step.price_impact
                    } for step in quote1.steps
                ]
            },
            {
                "test": "Medium Amount", 
                "input": quote2.total_amount_in,
                "output": quote2.total_amount_out,
                "success": quote2.success,
                "price_impact": quote2.total_price_impact,
                "bins_used": len(quote2.steps),
                "steps": [
                    {
                        "bin_id": step.bin_id,
                        "amount_in": step.amount_in,
                        "amount_out": step.amount_out,
                        "price": step.price,
                        "price_impact": step.price_impact
                    } for step in quote2.steps
                ]
            },
            {
                "test": "Large Amount",
                "input": quote3.total_amount_in,
                "output": quote3.total_amount_out,
                "success": quote3.success,
                "price_impact": quote3.total_price_impact,
                "bins_used": len(quote3.steps),
                "steps": [
                    {
                        "bin_id": step.bin_id,
                        "amount_in": step.amount_in,
                        "amount_out": step.amount_out,
                        "price": step.price,
                        "price_impact": step.price_impact
                    } for step in quote3.steps
                ]
            },
            {
                "test": "Reverse Direction",
                "input": quote4.total_amount_in,
                "output": quote4.total_amount_out,
                "success": quote4.success,
                "price_impact": quote4.total_price_impact,
                "bins_used": len(quote4.steps),
                "steps": [
                    {
                        "bin_id": step.bin_id,
                        "amount_in": step.amount_in,
                        "amount_out": step.amount_out,
                        "price": step.price,
                        "price_impact": step.price_impact
                    } for step in quote4.steps
                ]
            }
        ]
    }
    
    with open("multibin_simulation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results exported to: multibin_simulation_results.json")


if __name__ == "__main__":
    simulate_multibin_routing() 