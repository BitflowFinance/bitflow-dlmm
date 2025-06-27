"""
Basic routing example demonstrating single-pool multi-bin routing.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.pool import MockPool, PoolConfig
from src.routing import SinglePoolRouter
from src.utils import print_route_result, print_pool_analysis


def main():
    """Run basic routing examples."""
    print("=== DLMM Basic Routing Example ===\n")
    
    # Create a pool with bell curve liquidity
    print("Creating BTC/USDC pool with bell curve liquidity...")
    pool = MockPool.create_bell_curve_pool()
    
    # Print pool analysis
    print_pool_analysis(pool)
    
    # Create router
    router = SinglePoolRouter(pool)
    
    # Test 1: Small swap within active bin
    print("\n" + "="*50)
    print("Test 1: Small swap within active bin")
    print("="*50)
    
    result1 = router.get_quote("BTC", 0.1, "USDC")
    print_route_result(result1, detailed=True)
    
    # Test 2: Medium swap crossing multiple bins
    print("\n" + "="*50)
    print("Test 2: Medium swap crossing multiple bins")
    print("="*50)
    
    result2 = router.get_quote("BTC", 1.0, "USDC")
    print_route_result(result2, detailed=True)
    
    # Test 3: Large swap with significant price impact
    print("\n" + "="*50)
    print("Test 3: Large swap with significant price impact")
    print("="*50)
    
    result3 = router.get_quote("BTC", 10.0, "USDC")
    print_route_result(result3, detailed=True)
    
    # Test 4: Reverse swap (USDC to BTC)
    print("\n" + "="*50)
    print("Test 4: Reverse swap (USDC to BTC)")
    print("="*50)
    
    result4 = router.get_quote("USDC", 50000.0, "BTC")
    print_route_result(result4, detailed=True)
    
    # Test 5: Invalid token
    print("\n" + "="*50)
    print("Test 5: Invalid token")
    print("="*50)
    
    result5 = router.get_quote("ETH", 1.0, "USDC")
    print_route_result(result5)
    
    # Test 6: Same token swap
    print("\n" + "="*50)
    print("Test 6: Same token swap")
    print("="*50)
    
    result6 = router.get_quote("BTC", 1.0, "BTC")
    print_route_result(result6)
    
    # Test 7: Minimum output requirement
    print("\n" + "="*50)
    print("Test 7: Minimum output requirement")
    print("="*50)
    
    result7 = router.get_quote("BTC", 1.0, "USDC", min_amount_out=100000.0)
    print_route_result(result7)
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    main() 