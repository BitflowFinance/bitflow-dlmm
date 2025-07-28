#!/usr/bin/env python3
"""
Test USDC availability for BTC swap
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'quote-engine'))

from src.redis.client import RedisClient
from decimal import Decimal

def test_usdc_availability():
    """Test USDC availability for BTC swap"""
    
    redis_client = RedisClient(environment="local")
    
    # Test parameters
    pool_id = "BTC-USDC-25"
    btc_amount = 2005
    btc_price = 100000  # $100,000 per BTC
    
    print(f"🔍 Testing USDC availability for {btc_amount} BTC swap")
    print(f"Expected USDC needed: {btc_amount * btc_price:,} USDC")
    
    # Get active bin data
    pool_data = redis_client.get_pool_data(pool_id)
    active_bin_data = redis_client.get_bin_data(pool_id, pool_data.active_bin)
    
    print(f"\nActive bin ({pool_data.active_bin}):")
    print(f"  BTC available: {active_bin_data.reserve_x:,}")
    print(f"  USDC available: {active_bin_data.reserve_y:,}")
    
    # Check if active bin has enough USDC
    usdc_needed = btc_amount * btc_price
    if active_bin_data.reserve_y >= usdc_needed:
        print(f"✅ Active bin has enough USDC ({active_bin_data.reserve_y:,} >= {usdc_needed:,})")
    else:
        print(f"❌ Active bin needs more USDC ({active_bin_data.reserve_y:,} < {usdc_needed:,})")
        print(f"   Need additional: {usdc_needed - active_bin_data.reserve_y:,} USDC")
    
    # Check bins to the LEFT for additional USDC
    print(f"\n🔍 Checking bins to the LEFT for additional USDC:")
    active_bin_price = redis_client.get_bin_price(pool_id, pool_data.active_bin)
    left_bins = redis_client.get_bin_prices_reverse_range(pool_id, active_bin_price, 0)
    left_bins.sort(key=lambda x: x[1], reverse=True)
    
    total_usdc_available = active_bin_data.reserve_y
    bins_checked = 1
    
    for bin_id, price in left_bins[1:11]:  # Skip active bin, check next 10
        bin_data = redis_client.get_bin_data(pool_id, bin_id)
        if bin_data and bin_data.reserve_y > 0:
            total_usdc_available += bin_data.reserve_y
            bins_checked += 1
            print(f"  Bin {bin_id}: {bin_data.reserve_y:,} USDC (price: {price:,.2f})")
            if total_usdc_available >= usdc_needed:
                print(f"    ✅ Total USDC now sufficient: {total_usdc_available:,} >= {usdc_needed:,}")
                break
    
    print(f"\n📊 Summary:")
    print(f"  USDC needed: {usdc_needed:,}")
    print(f"  USDC available in {bins_checked} bins: {total_usdc_available:,}")
    print(f"  Sufficient: {'✅' if total_usdc_available >= usdc_needed else '❌'}")

if __name__ == "__main__":
    test_usdc_availability() 