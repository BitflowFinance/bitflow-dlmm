#!/usr/bin/env python3
"""
Debug script to test the rounding adjustment logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'quote-engine'))

from src.redis.client import RedisClient
from src.core.quote import compute_quote
from decimal import Decimal

def debug_adjustment():
    """Debug the rounding adjustment logic"""
    
    redis_client = RedisClient(environment="local")
    
    # Test parameters
    pool_id = "BTC-USDC-25"
    input_token = "BTC"
    output_token = "USDC"
    amount_in = Decimal("2005")
    
    print(f"🔍 Debugging adjustment logic for {amount_in} {input_token} → {output_token}")
    
    # Get pool data
    pool_data = redis_client.get_pool_data(pool_id)
    active_bin_data = redis_client.get_bin_data(pool_id, pool_data.active_bin)
    
    shared_data = {
        pool_id: {
            'metadata': pool_data,
            'active_bin_id': pool_data.active_bin,
            'active_bin_data': active_bin_data.to_redis_hash()
        }
    }
    
    # Test compute_quote
    result = compute_quote(pool_id, input_token, output_token, amount_in, redis_client, shared_data)
    
    print(f"Success: {result['success']}")
    print(f"Amount out: {result['amount_out']}")
    print(f"Execution path length: {len(result['execution_path'])}")
    
    print("\nExecution path details:")
    for i, step in enumerate(result['execution_path']):
        print(f"  Step {i+1}:")
        print(f"    Bin ID: {step['bin_id']}")
        print(f"    Function: {step['function_name']}")
        print(f"    X Amount: {step.get('x_amount', 'None')}")
        print(f"    Y Amount: {step.get('y_amount', 'None')}")
    
    # Check if adjustment was applied
    if len(result['execution_path']) == 1:
        step = result['execution_path'][0]
        x_amount = Decimal(str(step.get('x_amount', '0')))
        y_amount = Decimal(str(step.get('y_amount', '0')))
        total_used = x_amount + y_amount
        
        print(f"\n🔍 Single step analysis:")
        print(f"  Total used: {total_used}")
        print(f"  Amount in: {amount_in}")
        print(f"  Difference: {amount_in - total_used}")
        
        if abs(amount_in - total_used) < Decimal('0.001'):
            print("  ✅ No adjustment needed")
        else:
            print("  ❌ Adjustment was applied - this is the bug!")

if __name__ == "__main__":
    debug_adjustment() 