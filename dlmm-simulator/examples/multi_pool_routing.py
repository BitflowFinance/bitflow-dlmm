"""
Multi-pool routing example demonstrating routing across multiple pools.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.pool import MockPool, PoolConfig
from src.routing import SinglePoolRouter, MultiPoolRouter
from src.utils import print_route_result, print_pool_analysis, create_test_pools, print_route_comparison


def main():
    """Run multi-pool routing examples."""
    print("=== DLMM Multi-Pool Routing Example ===\n")
    
    # Create test pools
    print("Creating test pools...")
    pools = create_test_pools()
    
    # Print analysis of each pool
    for pool_id, pool in pools.items():
        print_pool_analysis(pool)
    
    # Create multi-pool router
    router = MultiPoolRouter(pools)
    
    # Test 1: Direct route (BTC to USDC)
    print("\n" + "="*50)
    print("Test 1: Direct route (BTC to USDC)")
    print("="*50)
    
    result1 = router.get_quote("BTC", 1.0, "USDC")
    print_route_result(result1, detailed=True)
    
    # Test 2: Direct route (ETH to USDC)
    print("\n" + "="*50)
    print("Test 2: Direct route (ETH to USDC)")
    print("="*50)
    
    result2 = router.get_quote("ETH", 10.0, "USDC")
    print_route_result(result2, detailed=True)
    
    # Test 3: Multi-hop route (ETH to BTC via USDC)
    print("\n" + "="*50)
    print("Test 3: Multi-hop route (ETH to BTC via USDC)")
    print("="*50)
    
    result3 = router.get_quote("ETH", 10.0, "BTC")
    print_route_result(result3, detailed=True)
    
    # Test 4: Compare direct vs multi-hop for ETH to BTC
    print("\n" + "="*50)
    print("Test 4: Compare direct vs multi-hop for ETH to BTC")
    print("="*50)
    
    # Direct route (if ETH-BTC pool exists)
    direct_result = router.get_quote("ETH", 10.0, "BTC", max_hops=1)
    
    # Multi-hop route
    multi_hop_result = router.get_quote("ETH", 10.0, "BTC", max_hops=2)
    
    print_route_comparison(direct_result, multi_hop_result)
    
    # Test 5: Large swap with price impact
    print("\n" + "="*50)
    print("Test 5: Large swap with price impact")
    print("="*50)
    
    result5 = router.get_quote("BTC", 50.0, "USDC")
    print_route_result(result5, detailed=True)
    
    # Test 6: Invalid route
    print("\n" + "="*50)
    print("Test 6: Invalid route")
    print("="*50)
    
    result6 = router.get_quote("BTC", 1.0, "INVALID")
    print_route_result(result6)
    
    # Test 7: Single pool routing comparison
    print("\n" + "="*50)
    print("Test 7: Single pool routing comparison")
    print("="*50)
    
    # Get BTC-USDC pool
    btc_usdc_pool = pools["BTC-USDC"]
    single_router = SinglePoolRouter(btc_usdc_pool)
    
    # Compare single pool vs multi-pool for same route
    single_result = single_router.get_quote("BTC", 1.0, "USDC")
    multi_result = router.get_quote("BTC", 1.0, "USDC", max_hops=1)
    
    print_route_comparison(single_result, multi_result)
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    main() 