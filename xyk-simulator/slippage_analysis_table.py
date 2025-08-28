#!/usr/bin/env python3
"""
Slippage Analysis Table Generator

Creates a comprehensive table showing:
- Trade size as percentage of total pool
- Trade size as percentage of half the pool  
- Resulting price slippage percentage
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from xyk_simulator import XYKSimulator
import pandas as pd

def generate_slippage_table():
    """Generate comprehensive slippage analysis table"""
    
    # Initialize simulator with $3M TVL and 1:1 price ratio
    simulator = XYKSimulator(total_value_locked=3_000_000, initial_price=1.0)
    
    # Get pool details
    tvl = simulator.get_tvl()
    
    print(f"Pool Configuration:")
    print(f"  Total Value Locked: ${tvl:,.0f}")
    print(f"  X Reserves: ${simulator.reserve_x:,.0f}")
    print(f"  Initial Price: ${simulator.get_spot_price():.4f}")
    print()
    
    # Define trade sizes to analyze (from 0.1% to 50% of pool)
    trade_percentages = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]
    
    results = []
    
    for pct in trade_percentages:
        trade_size = (pct / 100) * tvl
        pct_of_pool = pct
        
        # Calculate slippage for X->Y swap
        slippage_result = simulator.calculate_price_impact(trade_size, input_is_x=True)
        
        results.append({
            '% of Total Pool': f"{pct_of_pool:.1f}%",
            '% of X Reserves': f"{(trade_size / simulator.reserve_x) * 100:.1f}%",
            'Slippage %': f"{slippage_result.slippage_percentage:.4f}%"
        })
    
    # Create DataFrame and display
    df = pd.DataFrame(results)
    
    print("=" * 80)
    print("TRADE SIZE vs PRICE SLIPPAGE ANALYSIS")
    print("=" * 80)
    print()
    
    # Display the table
    print(df.to_string(index=False))
    print()
    
    # Additional insights
    print("=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    
    # Find specific thresholds
    for result in results:
        pct_of_pool = float(result['% of Total Pool'].rstrip('%'))
        slippage = float(result['Slippage %'].rstrip('%'))
        
        if pct_of_pool <= 1.0 and slippage <= 1.0:
            print(f"✅ {result['% of Total Pool']} of pool = {result['Slippage %']} slippage (Good for small trades)")
        elif pct_of_pool <= 5.0 and slippage <= 5.0:
            print(f"⚠️  {result['% of Total Pool']} of pool = {result['Slippage %']} slippage (Moderate impact)")
        elif pct_of_pool >= 10.0:
            print(f"🚨 {result['% of Total Pool']} of pool = {result['Slippage %']} slippage (High impact - consider splitting)")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("• Trades < 1% of pool: Minimal slippage impact")
    print("• Trades 1-5% of pool: Moderate slippage, acceptable for most cases")
    print("• Trades 5-10% of pool: High slippage, consider splitting into smaller trades")
    print("• Trades > 10% of pool: Very high slippage, should definitely be split")
    print("• Half pool trades: Extreme slippage, only for emergency situations")

if __name__ == "__main__":
    generate_slippage_table()
