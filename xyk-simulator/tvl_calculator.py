#!/usr/bin/env python3
"""
TVL Calculator for Specific Slippage Threshold

Calculates the minimum TVL needed to achieve a target slippage percentage
for a specific trade size.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from xyk_simulator import XYKSimulator

def find_tvl_for_slippage_target(trade_size: float, target_slippage: float, initial_price: float = 1.0):
    """
    Find the minimum TVL needed to achieve target slippage for a given trade size
    
    Args:
        trade_size: Size of the trade in USD
        target_slippage: Maximum allowed slippage percentage (e.g., 0.5 for 0.5%)
        initial_price: Initial price ratio Y/X
    
    Returns:
        Tuple of (required_tvl, actual_slippage, reserve_x, reserve_y)
    """
    
    # Start with a reasonable TVL estimate and iterate
    # For small slippage, we need much larger TVL than trade size
    min_tvl = trade_size * 10  # Start with 10x trade size
    max_tvl = trade_size * 1000  # Go up to 1000x trade size
    
    best_tvl = None
    best_slippage = float('inf')
    
    # Binary search for the optimal TVL
    while min_tvl <= max_tvl:
        test_tvl = (min_tvl + max_tvl) / 2
        
        try:
            simulator = XYKSimulator(total_value_locked=test_tvl, initial_price=initial_price)
            result = simulator.calculate_price_impact(trade_size, input_is_x=True)
            
            slippage = abs(result.slippage_percentage)
            
            if slippage <= target_slippage:
                # This TVL works, try to find a smaller one
                if test_tvl < best_tvl or best_tvl is None:
                    best_tvl = test_tvl
                    best_slippage = slippage
                max_tvl = test_tvl - 1
            else:
                # This TVL is too small, need larger
                min_tvl = test_tvl + 1
                
        except Exception as e:
            # If there's an error, try larger TVL
            min_tvl = test_tvl + 1
    
    if best_tvl is None:
        return None, None, None, None
    
    # Get final simulator with the best TVL
    final_simulator = XYKSimulator(total_value_locked=best_tvl, initial_price=initial_price)
    final_result = final_simulator.calculate_price_impact(trade_size, input_is_x=True)
    
    return best_tvl, abs(final_result.slippage_percentage), final_simulator.reserve_x, final_simulator.reserve_y

def main():
    """Main function to calculate TVL requirements"""
    
    trade_size = 100_000  # $100k
    target_slippage = 0.5  # 0.5%
    
    print(f"Calculating TVL requirements for:")
    print(f"  Trade Size: ${trade_size:,.0f}")
    print(f"  Target Slippage: {target_slippage}%")
    print(f"  Initial Price: 1.0 (Y/X)")
    print()
    
    tvl, actual_slippage, reserve_x, reserve_y = find_tvl_for_slippage_target(
        trade_size, target_slippage, 1.0
    )
    
    if tvl is None:
        print("❌ Could not find suitable TVL within reasonable bounds")
        return
    
    print("=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(f"Required TVL: ${tvl:,.0f}")
    print(f"Actual Slippage: {actual_slippage:.4f}%")
    print(f"Reserve X: ${reserve_x:,.0f}")
    print(f"Reserve Y: ${reserve_y:,.0f}")
    print()
    
    # Calculate some ratios
    trade_to_tvl_ratio = (trade_size / tvl) * 100
    trade_to_reserve_x_ratio = (trade_size / reserve_x) * 100
    
    print("=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print(f"Trade size as % of total pool: {trade_to_tvl_ratio:.3f}%")
    print(f"Trade size as % of X reserves: {trade_to_reserve_x_ratio:.3f}%")
    print(f"Pool size multiplier needed: {tvl / trade_size:.1f}x")
    print()
    
    # Show what happens with different TVL levels
    print("=" * 60)
    print("SLIPPAGE AT DIFFERENT TVL LEVELS:")
    print("=" * 60)
    
    test_tvls = [tvl * 0.5, tvl * 0.75, tvl, tvl * 1.25, tvl * 1.5]
    
    for test_tvl in test_tvls:
        try:
            test_sim = XYKSimulator(total_value_locked=test_tvl, initial_price=1.0)
            test_result = test_sim.calculate_price_impact(trade_size, input_is_x=True)
            test_slippage = abs(test_result.slippage_percentage)
            
            status = "✅" if test_slippage <= target_slippage else "❌"
            print(f"{status} ${test_tvl:,.0f} TVL → {test_slippage:.4f}% slippage")
            
        except Exception as e:
            print(f"❌ ${test_tvl:,.0f} TVL → Error")

if __name__ == "__main__":
    main()
