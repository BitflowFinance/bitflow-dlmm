#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.quote_engine import MockRedisClient, QuoteEngine

def test_btc_usdc_routing():
    """Test BTC to USDC routing"""
    print("Testing BTC to USDC routing...")
    
    # Create mock Redis client
    redis_client = MockRedisClient()
    
    # Create quote engine
    quote_engine = QuoteEngine(redis_client)
    
    # Test BTC to USDC swap
    amount_in = 100.0  # 100 BTC
    result = quote_engine.get_quote("BTC", "USDC", amount_in)
    
    print(f"Input: {amount_in} BTC")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Output: {result.amount_out} USDC")
        print(f"Price Impact: {result.price_impact:.4f}%")
        print(f"Route Type: {result.route_type.value}")
        print(f"Steps: {len(result.steps)}")
        for i, step in enumerate(result.steps):
            print(f"  Step {i}: Pool {step.pool_id}, Bin {step.bin_id}, {step.amount_in:.6f} -> {step.amount_out:.6f}, Price: {step.price:.2f}")
    else:
        print(f"Error: {result.error}")
    
    return result.success

if __name__ == "__main__":
    success = test_btc_usdc_routing()
    sys.exit(0 if success else 1) 