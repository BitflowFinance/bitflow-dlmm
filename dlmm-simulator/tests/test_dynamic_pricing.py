#!/usr/bin/env python3
"""
Test script to demonstrate dynamic pricing logic in DLMM.
Shows how bin prices change when the active bin moves.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.quote_engine import MockRedisClient, QuoteEngine


def test_dynamic_pricing():
    """Test dynamic pricing with active bin movement"""
    print("🚀 DLMM Dynamic Pricing Test")
    print("=" * 60)
    
    # Initialize quote engine
    redis_client = MockRedisClient()
    quote_engine = QuoteEngine(redis_client)
    
    # Test 1: Initial state (active bin at 500)
    print("\n📊 Test 1: Initial State (Active Bin 500)")
    print("-" * 40)
    
    # Get initial quote
    quote1 = quote_engine.get_quote("BTC", "USDC", 1.0)
    print(f"1.0 BTC → USDC: {quote1.amount_out:.2f} USDC")
    print(f"Price impact: {quote1.price_impact:.4f}%")
    
    # Show some bin prices
    print("\nBin Prices (Active Bin 500):")
    for bin_id in [498, 499, 500, 501, 502]:
        key = f"bin:BTC-USDC-25:{bin_id}"
        if key in redis_client.data:
            bin_data = redis_client.data[key]
            print(f"  Bin {bin_id}: ${bin_data['price']:.2f}")
    
    # Test 2: Move active bin to 501 (price should increase)
    print("\n📈 Test 2: Move Active Bin to 501 (Price Increase)")
    print("-" * 40)
    
    quote_engine.simulate_active_bin_movement("BTC-USDC-25", 501)
    
    # Get quote after movement
    quote2 = quote_engine.get_quote("BTC", "USDC", 1.0)
    print(f"1.0 BTC → USDC: {quote2.amount_out:.2f} USDC")
    print(f"Price impact: {quote2.price_impact:.4f}%")
    
    # Show updated bin prices
    print("\nBin Prices (Active Bin 501):")
    for bin_id in [499, 500, 501, 502, 503]:
        key = f"bin:BTC-USDC-25:{bin_id}"
        if key in redis_client.data:
            bin_data = redis_client.data[key]
            print(f"  Bin {bin_id}: ${bin_data['price']:.2f}")
    
    # Test 3: Move active bin to 499 (price should decrease)
    print("\n📉 Test 3: Move Active Bin to 499 (Price Decrease)")
    print("-" * 40)
    
    quote_engine.simulate_active_bin_movement("BTC-USDC-25", 499)
    
    # Get quote after movement
    quote3 = quote_engine.get_quote("BTC", "USDC", 1.0)
    print(f"1.0 BTC → USDC: {quote3.amount_out:.2f} USDC")
    print(f"Price impact: {quote3.price_impact:.4f}%")
    
    # Show updated bin prices
    print("\nBin Prices (Active Bin 499):")
    for bin_id in [497, 498, 499, 500, 501]:
        key = f"bin:BTC-USDC-25:{bin_id}"
        if key in redis_client.data:
            bin_data = redis_client.data[key]
            print(f"  Bin {bin_id}: ${bin_data['price']:.2f}")
    
    # Summary
    print("\n📋 Summary:")
    print("-" * 40)
    print(f"Initial quote (bin 500): {quote1.amount_out:.2f} USDC")
    print(f"After move to bin 501:   {quote2.amount_out:.2f} USDC")
    print(f"After move to bin 499:   {quote3.amount_out:.2f} USDC")
    
    price_change_501 = ((quote2.amount_out - quote1.amount_out) / quote1.amount_out) * 100
    price_change_499 = ((quote3.amount_out - quote1.amount_out) / quote1.amount_out) * 100
    
    print(f"\nPrice change moving to bin 501: {price_change_501:+.2f}%")
    print(f"Price change moving to bin 499: {price_change_499:+.2f}%")


if __name__ == "__main__":
    test_dynamic_pricing() 