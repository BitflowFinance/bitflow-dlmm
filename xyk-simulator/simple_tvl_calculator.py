#!/usr/bin/env python3
"""
Simple TVL Calculator for Specific Slippage Threshold

Uses direct mathematical calculation to find TVL needed for target slippage.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from xyk_simulator import XYKSimulator

def calculate_tvl_for_slippage(trade_size: float, target_slippage: float, initial_price: float = 1.0):
    """
    Calculate TVL needed for a specific slippage target using mathematical formula
    
    For X->Y swap with slippage s:
    s = (dx / (x + dx)) * 100
    where dx is trade size, x is X reserves
    
    Solving for x: x = dx * (100/s - 1)
    TVL = x + y = x + price*x = x * (1 + price)
    """
    
    # Convert slippage to decimal
    slippage_decimal = target_slippage / 100
    
    # Calculate required X reserves
    # For small slippage: x = trade_size * (1/slippage - 1)
    required_x = trade_size * (1 / slippage_decimal - 1)
    
    # Calculate required Y reserves (maintaining price ratio)
    required_y = required_x * initial_price
    
    # Total TVL needed
    required_tvl = required_x + required_y
    
    return required_tvl, required_x, required_y

def verify_calculation(tvl: float, trade_size: float, target_slippage: float, initial_price: float = 1.0):
    """Verify the calculation by running it through the simulator"""
    
    simulator = XYKSimulator(total_value_locked=tvl, initial_price=initial_price)
    result = simulator.calculate_price_impact(trade_size, input_is_x=True)
    
    actual_slippage = abs(result.slippage_percentage)
    success = actual_slippage <= target_slippage
    
    return success, actual_slippage, simulator

def main():
    """Main function to calculate TVL requirements"""
    
    trade_size = 100_000  # $100k
    target_slippage = 0.5  # 0.5%
    
    print(f"Calculating TVL requirements for:")
    print(f"  Trade Size: ${trade_size:,.0f}")
    print(f"  Target Slippage: {target_slippage}%")
    print(f"  Initial Price: 1.0 (Y/X)")
    print()
    
    # Calculate required TVL
    required_tvl, required_x, required_y = calculate_tvl_for_slippage(
        trade_size, target_slippage, 1.0
    )
    
    print("=" * 60)
    print("MATHEMATICAL CALCULATION:")
    print("=" * 60)
    print(f"Required TVL: ${required_tvl:,.0f}")
    print(f"Required X Reserves: ${required_x:,.0f}")
    print(f"Required Y Reserves: ${required_y:,.0f}")
    print()
    
    # Verify with simulator
    success, actual_slippage, simulator = verify_calculation(
        required_tvl, trade_size, target_slippage, 1.0
    )
    
    print("=" * 60)
    print("VERIFICATION WITH SIMULATOR:")
    print("=" * 60)
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"Target Slippage: {target_slippage}%")
    print(f"Actual Slippage: {actual_slippage:.4f}%")
    print(f"Simulator TVL: ${simulator.get_tvl():,.0f}")
    print()
    
    # Calculate ratios
    trade_to_tvl_ratio = (trade_size / required_tvl) * 100
    trade_to_x_ratio = (trade_size / required_x) * 100
    
    print("=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print(f"Trade size as % of total pool: {trade_to_tvl_ratio:.3f}%")
    print(f"Trade size as % of X reserves: {trade_to_x_ratio:.3f}%")
    print(f"Pool size multiplier needed: {required_tvl / trade_size:.1f}x")
    print()
    
    # Test different TVL levels around the calculated value
    print("=" * 60)
    print("SLIPPAGE AT DIFFERENT TVL LEVELS:")
    print("=" * 60)
    
    test_multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    
    for multiplier in test_multipliers:
        test_tvl = required_tvl * multiplier
        try:
            test_sim = XYKSimulator(total_value_locked=test_tvl, initial_price=1.0)
            test_result = test_sim.calculate_price_impact(trade_size, input_is_x=True)
            test_slippage = abs(test_result.slippage_percentage)
            
            status = "✅" if test_slippage <= target_slippage else "❌"
            print(f"{status} {multiplier:4.1f}x TVL (${test_tvl:,.0f}) → {test_slippage:.4f}% slippage")
            
        except Exception as e:
            print(f"❌ {multiplier:4.1f}x TVL (${test_tvl:,.0f}) → Error")

if __name__ == "__main__":
    main()
