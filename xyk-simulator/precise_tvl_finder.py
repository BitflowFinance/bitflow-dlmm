#!/usr/bin/env python3
"""
Precise TVL Finder for 0.5% Slippage

Finds the exact TVL needed for exactly 0.5% slippage on a $100k trade.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from xyk_simulator import XYKSimulator

def find_precise_tvl():
    """Find the precise TVL needed for exactly 0.5% slippage"""
    
    trade_size = 100_000  # $100k
    target_slippage = 0.5  # 0.5%
    
    print(f"Finding precise TVL for:")
    print(f"  Trade Size: ${trade_size:,.0f}")
    print(f"  Target Slippage: {target_slippage}%")
    print()
    
    # We know from previous tests that 2.0x TVL ($79.6M) gives 0.5006%
    # Let's test values around this to find the exact threshold
    base_tvl = 39_800_000  # Base calculation
    test_multipliers = [1.95, 1.96, 1.97, 1.98, 1.99, 2.0, 2.01, 2.02, 2.03, 2.04, 2.05]
    
    print("=" * 70)
    print("PRECISE TVL TESTING:")
    print("=" * 70)
    
    best_tvl = None
    best_slippage = float('inf')
    
    for multiplier in test_multipliers:
        test_tvl = base_tvl * multiplier
        
        try:
            test_sim = XYKSimulator(total_value_locked=test_tvl, initial_price=1.0)
            test_result = test_sim.calculate_price_impact(trade_size, input_is_x=True)
            test_slippage = abs(test_result.slippage_percentage)
            
            # Check if this is the best result so far
            if abs(test_slippage - target_slippage) < abs(best_slippage - target_slippage):
                best_tvl = test_tvl
                best_slippage = test_slippage
            
            # Mark if it meets the target
            status = "✅" if test_slippage <= target_slippage else "❌"
            print(f"{status} {multiplier:5.2f}x TVL (${test_tvl:,.0f}) → {test_slippage:.4f}% slippage")
            
        except Exception as e:
            print(f"❌ {multiplier:5.2f}x TVL (${test_tvl:,.0f}) → Error")
    
    print()
    print("=" * 70)
    print("BEST RESULT:")
    print("=" * 70)
    print(f"Best TVL: ${best_tvl:,.0f}")
    print(f"Best Slippage: {best_slippage:.4f}%")
    print(f"Difference from Target: {abs(best_slippage - target_slippage):.4f}%")
    
    # Calculate final ratios
    trade_to_tvl_ratio = (trade_size / best_tvl) * 100
    trade_to_x_ratio = (trade_size / (best_tvl / 2)) * 100  # X reserves = TVL/2 for 1:1 price
    
    print()
    print("=" * 70)
    print("FINAL ANALYSIS:")
    print("=" * 70)
    print(f"Trade size as % of total pool: {trade_to_tvl_ratio:.3f}%")
    print(f"Trade size as % of X reserves: {trade_to_x_ratio:.3f}%")
    print(f"Pool size multiplier needed: {best_tvl / trade_size:.1f}x")
    
    # Show what happens with slightly different TVL
    print()
    print("=" * 70)
    print("SLIPPAGE SENSITIVITY:")
    print("=" * 70)
    
    sensitivity_tests = [0.98, 0.99, 1.0, 1.01, 1.02]
    
    for sensitivity in sensitivity_tests:
        test_tvl = best_tvl * sensitivity
        try:
            test_sim = XYKSimulator(total_value_locked=test_tvl, initial_price=1.0)
            test_result = test_sim.calculate_price_impact(trade_size, input_is_x=True)
            test_slippage = abs(test_result.slippage_percentage)
            
            status = "✅" if test_slippage <= target_slippage else "❌"
            print(f"{status} {sensitivity:5.2f}x TVL (${test_tvl:,.0f}) → {test_slippage:.4f}% slippage")
            
        except Exception as e:
            print(f"❌ {sensitivity:5.2f}x TVL (${test_tvl:,.0f}) → Error")

if __name__ == "__main__":
    find_precise_tvl()
