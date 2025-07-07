#!/usr/bin/env python3
"""
Test script to verify that pool_id is correctly set in route steps.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.quote_engine import MockRedisClient, QuoteEngine

def test_pool_id_fix():
    """Test that pool_id is correctly set in route steps"""
    print("🔧 Pool ID Fix Test")
    print("=" * 60)
    
    # Initialize quote engine
    redis_client = MockRedisClient()
    quote_engine = QuoteEngine(redis_client)
    
    # Test different trade sizes
    test_cases = [
        (1.0, "Small trade"),
        (1100.0, "Medium trade"), 
        (2000.0, "Large trade")
    ]
    
    for amount, description in test_cases:
        print(f"\n📊 {description}: {amount} BTC → USDC")
        print("-" * 40)
        
        quote = quote_engine.get_quote("BTC", "USDC", amount)
        
        if quote.success:
            print(f"✅ Quote successful!")
            print(f"Route type: {quote.route_type.value}")
            print(f"Steps: {len(quote.steps)}")
            
            for i, step in enumerate(quote.steps):
                print(f"  Step {i}:")
                print(f"    Pool ID: {step.pool_id}")
                print(f"    Bin ID: {step.bin_id}")
                print(f"    Amount In: {step.amount_in:.6f} BTC")
                print(f"    Amount Out: {step.amount_out:,.2f} USDC")
                print(f"    Price: ${step.price:,.2f}")
                print(f"    Price Impact: {step.price_impact:.4f}%")
                
                # Verify pool_id format
                if step.pool_id in ["BTC-USDC-25", "BTC-USDC-50"]:
                    print(f"    ✅ Pool ID format correct: {step.pool_id}")
                else:
                    print(f"    ❌ Pool ID format incorrect: {step.pool_id}")
                print()
        else:
            print(f"❌ Quote failed: {quote.error}")

if __name__ == "__main__":
    test_pool_id_fix() 