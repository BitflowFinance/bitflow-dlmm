#!/usr/bin/env python3
"""
Test script to demonstrate multi-bin swap with price impact.
Shows how large trades span multiple bins and calculate average price impact.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.quote_engine import MockRedisClient, QuoteEngine

def test_multi_bin_swap():
    """Test large swap that spans multiple bins"""
    print("💰 DLMM Multi-Bin Swap Test")
    print("=" * 60)
    
    # Initialize quote engine
    redis_client = MockRedisClient()
    quote_engine = QuoteEngine(redis_client)
    
    # Test with a large amount that will span multiple bins
    input_amount = 2000.0  # 2000 BTC - should span multiple bins
    
    print(f"\n📊 Large Swap Test: {input_amount} BTC → USDC")
    print("-" * 40)
    
    # Get quote
    quote = quote_engine.get_quote("BTC", "USDC", input_amount)
    
    if quote.success:
        print(f"✅ Quote successful!")
        print(f"Input: {input_amount} BTC")
        print(f"Output: {quote.amount_out:,.2f} USDC")
        print(f"Effective price: ${quote.amount_out / input_amount:,.2f} per BTC")
        print(f"Price impact: {quote.price_impact:.4f}%")
        print(f"Route type: {quote.route_type.value}")
        
        print(f"\n📋 Swap Steps:")
        for i, step in enumerate(quote.steps):
            print(f"  Step {i}:")
            print(f"    Pool: {step.pool_id}")
            print(f"    Bin: {step.bin_id}")
            print(f"    Input: {step.amount_in:.6f} BTC")
            print(f"    Output: {step.amount_out:,.2f} USDC")
            print(f"    Bin Price: ${step.price:,.2f}")
            print(f"    Step Price Impact: {step.price_impact:.4f}%")
            print()
        
        # Calculate theoretical price (no price impact)
        theoretical_output = input_amount * 100000  # $100,000 per BTC
        price_impact_calc = abs(theoretical_output - quote.amount_out) / theoretical_output * 100
        
        print(f"📈 Price Impact Analysis:")
        print(f"  Theoretical output: {theoretical_output:,.2f} USDC")
        print(f"  Actual output: {quote.amount_out:,.2f} USDC")
        print(f"  Calculated price impact: {price_impact_calc:.4f}%")
        print(f"  Reported price impact: {quote.price_impact:.4f}%")
        
    else:
        print(f"❌ Quote failed: {quote.error}")

if __name__ == "__main__":
    test_multi_bin_swap() 