#!/usr/bin/env python3
"""
Test $100k swap on $20M TVL pool
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from xyk_simulator import XYKSimulator

def test_20m_tvl():
    """Test slippage for $100k swap on $20M TVL"""
    
    tvl = 20_000_000  # $20M
    trade_size = 100_000  # $100k
    initial_price = 1.0
    
    print(f"Testing slippage for:")
    print(f"  Pool TVL: ${tvl:,.0f}")
    print(f"  Trade Size: ${trade_size:,.0f}")
    print(f"  Initial Price: {initial_price}")
    print()
    
    # Initialize simulator
    simulator = XYKSimulator(total_value_locked=tvl, initial_price=initial_price)
    
    # Calculate slippage
    result = simulator.calculate_price_impact(trade_size, input_is_x=True)
    
    print("=" * 60)
    print("POOL STATE:")
    print("=" * 60)
    print(f"Total Value Locked: ${simulator.get_tvl():,.0f}")
    print(f"Reserve X: ${simulator.reserve_x:,.0f}")
    print(f"Reserve Y: ${simulator.reserve_y:,.0f}")
    print(f"Initial Price: ${simulator.get_spot_price():.4f}")
    print()
    
    print("=" * 60)
    print("TRADE IMPACT:")
    print("=" * 60)
    print(f"Input Amount: ${result.input_amount:,.0f}")
    print(f"Output Amount: ${result.output_amount:,.2f}")
    print(f"Price Before: ${result.price_before:.4f}")
    print(f"Price After: ${result.price_after:.4f}")
    print(f"Price Impact: ${result.price_impact:.6f}")
    print(f"Slippage: {result.slippage_percentage:.4f}%")
    print()
    
    # Calculate ratios
    trade_to_tvl_ratio = (trade_size / tvl) * 100
    trade_to_x_ratio = (trade_size / simulator.reserve_x) * 100
    
    print("=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print(f"Trade size as % of total pool: {trade_to_tvl_ratio:.3f}%")
    print(f"Trade size as % of X reserves: {trade_to_x_ratio:.3f}%")
    print(f"Pool size multiplier: {tvl / trade_size:.1f}x")
    print()
    
    # Compare to our previous findings
    print("=" * 60)
    print("COMPARISON TO 0.5% SLIPPAGE TARGET:")
    print("=" * 60)
    
    if abs(result.slippage_percentage) <= 0.5:
        print("✅ This pool meets the 0.5% slippage target")
    else:
        print("❌ This pool exceeds the 0.5% slippage target")
        print(f"   Current slippage: {abs(result.slippage_percentage):.4f}%")
        print(f"   Target slippage: 0.5000%")
        print(f"   Difference: {abs(result.slippage_percentage) - 0.5:.4f}%")
    
    # Show what TVL would be needed
    required_tvl_for_0_5 = tvl * (abs(result.slippage_percentage) / 0.5)
    print(f"   TVL needed for 0.5% slippage: ${required_tvl_for_0_5:,.0f}")
    print(f"   Current TVL: ${tvl:,.0f}")
    print(f"   Additional TVL needed: ${required_tvl_for_0_5 - tvl:,.0f}")

if __name__ == "__main__":
    test_20m_tvl()
