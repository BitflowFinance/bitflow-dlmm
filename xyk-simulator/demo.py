#!/usr/bin/env python3
"""
Quick Demo of XYK Simulator

This script demonstrates the key capabilities of the XYK simulator
in a simple, easy-to-understand format.
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from xyk_simulator import XYKSimulator


def main():
    """Quick demo of XYK simulator capabilities"""
    
    print("🚀 XYK Simulator - Quick Demo")
    print("=" * 40)
    
    # Create a $3M pool
    print("\n📊 Creating $3M pool...")
    simulator = XYKSimulator(total_value_locked=3_000_000, initial_price=1.0)
    
    print(f"\n💰 Pool State:")
    print(f"   Reserve X: ${simulator.reserve_x:,.0f}")
    print(f"   Reserve Y: ${simulator.reserve_y:,.0f}")
    print(f"   Spot Price: ${simulator.get_spot_price():.4f}")
    
    # Test different trade sizes
    print("\n📈 Testing Different Trade Sizes:")
    print("-" * 40)
    
    trade_sizes = [1000, 10000, 100000, 500000]
    
    for trade_size in trade_sizes:
        result = simulator.calculate_price_impact(trade_size, input_is_x=True)
        print(f"${trade_size:>8,} trade → {result.slippage_percentage:>8.2f}% slippage")
    
    # Reset pool for TVL analysis
    simulator.reset_pool()
    
    print("\n🎯 TVL Requirements for $100K Trade:")
    print("-" * 40)
    
    # Find TVL needed for 1% slippage
    requirement = simulator.find_tvl_for_slippage(
        trade_size=100_000,
        max_slippage=0.01,  # 1%
        input_is_x=True
    )
    
    print(f"1% slippage → ${requirement.required_tvl:,.0f} TVL needed")
    print(f"Trade represents {(100_000 / requirement.required_tvl) * 100:.2f}% of pool")
    
    print("\n✅ Demo Complete!")
    print("\n💡 Key Insight: Slippage increases exponentially with trade size!")
    print("   Small trades (<1% of pool) have minimal impact")
    print("   Large trades (>10% of pool) cause significant price movement")


if __name__ == "__main__":
    main()
