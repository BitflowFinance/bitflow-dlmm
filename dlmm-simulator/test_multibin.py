#!/usr/bin/env python3
"""
Simple multi-bin routing test.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pool import MockPool
from src.routing import SinglePoolRouter


def test_multibin_routing():
    """Test multi-bin routing with different amounts."""
    
    # Create a pool
    pool = MockPool.create_bell_curve_pool()
    router = SinglePoolRouter(pool)
    
    print("DLMM Multi-Bin Routing Test")
    print("=" * 50)
    print(f"Pool: {pool.config.x_token}/{pool.config.y_token}")
    print(f"Active Bin: {pool.config.active_bin_id}")
    print(f"Active Price: ${pool.config.active_price:,.2f}")
    
    # Test different amounts
    test_amounts = [0.5, 5.0, 15.0, 25.0, 50.0]
    
    for amount in test_amounts:
        print(f"\n{'='*50}")
        print(f"Testing {amount} BTC → USDC")
        print(f"{'='*50}")
        
        quote = router.get_quote("BTC", amount, "USDC")
        
        print(f"Input: {quote.total_amount_in} BTC")
        print(f"Output: {quote.total_amount_out:.2f} USDC")
        print(f"Success: {quote.success}")
        print(f"Price Impact: {quote.total_price_impact:.4f}%")
        print(f"Bins Used: {len(quote.steps)}")
        
        if quote.steps:
            print(f"\nBin Details:")
            print(f"{'Bin':<6} {'Amount In':<12} {'Amount Out':<12} {'Price':<10} {'Impact':<8}")
            print("-" * 60)
            for step in quote.steps:
                print(f"{step.bin_id:<6} {step.amount_in:<12.4f} {step.amount_out:<12.2f} "
                      f"{step.price:<10.2f} {step.price_impact:<8.4f}%")
        
        if not quote.success and quote.error_message:
            print(f"Error: {quote.error_message}")
    
    # Test reverse direction (USDC → BTC)
    print(f"\n{'='*50}")
    print("Testing Reverse Direction: USDC → BTC")
    print(f"{'='*50}")
    
    usdc_amounts = [10000, 100000, 500000, 1000000]
    
    for amount in usdc_amounts:
        print(f"\n{'='*50}")
        print(f"Testing {amount:,} USDC → BTC")
        print(f"{'='*50}")
        
        quote = router.get_quote("USDC", amount, "BTC")
        
        print(f"Input: {quote.total_amount_in:,} USDC")
        print(f"Output: {quote.total_amount_out:.6f} BTC")
        print(f"Success: {quote.success}")
        print(f"Price Impact: {quote.total_price_impact:.4f}%")
        print(f"Bins Used: {len(quote.steps)}")
        
        if quote.steps:
            print(f"\nBin Details:")
            print(f"{'Bin':<6} {'Amount In':<12} {'Amount Out':<12} {'Price':<10} {'Impact':<8}")
            print("-" * 60)
            for step in quote.steps:
                print(f"{step.bin_id:<6} {step.amount_in:<12.2f} {step.amount_out:<12.6f} "
                      f"{step.price:<10.2f} {step.price_impact:<8.4f}%")
        
        if not quote.success and quote.error_message:
            print(f"Error: {quote.error_message}")


if __name__ == "__main__":
    test_multibin_routing() 