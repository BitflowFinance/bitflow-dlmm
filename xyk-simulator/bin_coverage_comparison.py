#!/usr/bin/env python3
"""
Bin Coverage Comparison: 5 bps vs 20 bps

Compares price coverage for different bin step sizes with the same number of bins.
"""

import numpy as np

def calculate_bin_coverage(bin_step_bps: int, bins_per_side: int):
    """
    Calculate price coverage for a given bin step and number of bins per side
    """
    
    # Convert basis points to decimal
    bin_step = bin_step_bps / 10000
    
    # Calculate price coverage in each direction
    right_price_multiplier = (1 + bin_step) ** bins_per_side
    left_price_multiplier = (1 + bin_step) ** (-bins_per_side)
    
    # Calculate percentage changes
    right_coverage_pct = (right_price_multiplier - 1) * 100
    left_coverage_pct = (1 - left_price_multiplier) * 100
    total_coverage_pct = right_coverage_pct + left_coverage_pct
    
    # Calculate specific price levels
    active_bin_id = 500
    left_bin_range = f"{active_bin_id - bins_per_side} to {active_bin_id - 1}"
    right_bin_range = f"{active_bin_id + 1} to {active_bin_id + bins_per_side}"
    
    # Show some example bin prices
    example_bins = [0, 25, 50, 75, 100]
    example_prices = []
    
    for i in example_bins:
        if i == 0:
            price_multiplier = 1.0  # Active bin
            bin_id = active_bin_id
        else:
            price_multiplier = (1 + bin_step) ** i  # Right side
            bin_id = active_bin_id + i
        
        example_prices.append({
            'bin_id': bin_id,
            'distance': i,
            'price_multiplier': price_multiplier,
            'price_change_pct': (price_multiplier - 1) * 100
        })
    
    return {
        'bin_step_bps': bin_step_bps,
        'bin_step_decimal': bin_step,
        'bins_per_side': bins_per_side,
        'total_bins': 1 + (2 * bins_per_side),
        'right_coverage_pct': right_coverage_pct,
        'left_coverage_pct': left_coverage_pct,
        'total_coverage_pct': total_coverage_pct,
        'price_range': f"{(1/right_price_multiplier):.4f}x to {right_price_multiplier:.4f}x",
        'left_bin_range': left_bin_range,
        'right_bin_range': right_bin_range,
        'example_prices': example_prices
    }

def main():
    """Compare coverage for 5 bps vs 20 bps bin steps"""
    
    bins_per_side = 100  # 100 bins on each side
    
    # Calculate for both bin step sizes
    result_5bps = calculate_bin_coverage(5, bins_per_side)
    result_20bps = calculate_bin_coverage(20, bins_per_side)
    
    print("=" * 100)
    print("DLMM BIN COVERAGE COMPARISON: 5 bps vs 20 bps")
    print("=" * 100)
    print()
    
    # Show configuration
    print(f"📊 CONFIGURATION:")
    print(f"   Bins per side: {bins_per_side}")
    print(f"   Total bins: {result_5bps['total_bins']}")
    print(f"   Active bin ID: 500")
    print()
    
    # Compare price coverage
    print(f"📈 PRICE COVERAGE COMPARISON:")
    print("-" * 100)
    print(f"{'Metric':<25} {'5 bps':<20} {'20 bps':<20} {'Difference':<20}")
    print(f"{'-'*25} {'-'*20} {'-'*20} {'-'*20}")
    
    print(f"{'Bin Step':<25} {result_5bps['bin_step_bps']:<20} {result_20bps['bin_step_bps']:<20} {result_20bps['bin_step_bps']/result_5bps['bin_step_bps']:<20.1f}x")
    print(f"{'Right Coverage':<25} +{result_5bps['right_coverage_pct']:<19.4f}% +{result_20bps['right_coverage_pct']:<19.4f}% {result_20bps['right_coverage_pct']/result_5bps['right_coverage_pct']:<20.1f}x")
    print(f"{'Left Coverage':<25} -{result_5bps['left_coverage_pct']:<19.4f}% -{result_20bps['left_coverage_pct']:<19.4f}% {result_20bps['left_coverage_pct']/result_5bps['left_coverage_pct']:<20.1f}x")
    print(f"{'Total Coverage':<25} ±{result_5bps['total_coverage_pct']/2:<19.4f}% ±{result_20bps['total_coverage_pct']/2:<19.4f}% {result_20bps['total_coverage_pct']/result_5bps['total_coverage_pct']:<20.1f}x")
    print(f"{'Price Range':<25} {result_5bps['price_range']:<20} {result_20bps['price_range']:<20} {'N/A':<20}")
    
    print()
    
    # Show bin ranges
    print(f"🎯 BIN RANGES:")
    print(f"   5 bps:  Left [{result_5bps['left_bin_range']}], Right [{result_5bps['right_bin_range']}]")
    print(f"   20 bps: Left [{result_20bps['left_bin_range']}], Right [{result_20bps['right_bin_range']}]")
    print()
    
    # Show example prices for both
    print(f"💡 EXAMPLE BIN PRICES:")
    print("-" * 100)
    
    # 5 bps prices
    print(f"   5 bps Bin Step:")
    print(f"   {'Bin ID':<8} {'Distance':<10} {'Multiplier':<12} {'Change %':<10}")
    print(f"   {'-'*8} {'-'*10} {'-'*12} {'-'*10}")
    
    for price_info in result_5bps['example_prices']:
        print(f"   {price_info['bin_id']:<8} {price_info['distance']:<10} {price_info['price_multiplier']:<12.4f} {price_info['price_change_pct']:<10.4f}")
    
    print()
    
    # 20 bps prices
    print(f"   20 bps Bin Step:")
    print(f"   {'Bin ID':<8} {'Distance':<10} {'Multiplier':<12} {'Change %':<10}")
    print(f"   {'-'*8} {'-'*10} {'-'*12} {'-'*10}")
    
    for price_info in result_20bps['example_prices']:
        print(f"   {price_info['bin_id']:<8} {price_info['distance']:<10} {price_info['price_multiplier']:<12.4f} {price_info['price_change_pct']:<10.4f}")
    
    print()
    
    # Asset type comparison
    print(f"📊 ASSET TYPE SUITABILITY:")
    print("-" * 100)
    
    asset_types = [
        ("Stablecoins", 0.1),
        ("Major crypto", 3.0),
        ("Mid-cap altcoins", 6.0),
        ("Long-tail assets", 12.0),
        ("Leveraged tokens", 20.0)
    ]
    
    print(f"{'Asset Type':<20} {'Daily Vol':<12} {'5 bps':<15} {'20 bps':<15} {'Better':<15}")
    print(f"{'-'*20} {'-'*12} {'-'*15} {'-'*15} {'-'*15}")
    
    for asset_name, daily_vol in asset_types:
        coverage_5bps = result_5bps['total_coverage_pct'] / daily_vol
        coverage_20bps = result_20bps['total_coverage_pct'] / daily_vol
        
        if coverage_5bps > coverage_20bps:
            better = "5 bps"
        elif coverage_20bps > coverage_5bps:
            better = "20 bps"
        else:
            better = "Equal"
        
        print(f"{asset_name:<20} ±{daily_vol:<11.1f}% {coverage_5bps:<15.1f}x {coverage_20bps:<15.1f}x {better:<15}")
    
    print()
    print("=" * 100)
    print("KEY INSIGHTS:")
    print("=" * 100)
    
    print(f"\n🔍 COVERAGE DIFFERENCES:")
    print(f"   • 20 bps provides {result_20bps['total_coverage_pct']/result_5bps['total_coverage_pct']:.1f}x more price coverage")
    print(f"   • 20 bps covers ±{result_20bps['total_coverage_pct']/2:.1f}% vs 5 bps covers ±{result_5bps['total_coverage_pct']/2:.1f}%")
    print(f"   • 20 bps price granularity: {result_20bps['bin_step_bps']/result_5bps['bin_step_bps']:.0f}x coarser than 5 bps")
    
    print(f"\n💡 TRADE-OFFS:")
    print(f"   • 5 bps: Higher precision, lower coverage, more bins needed for wide ranges")
    print(f"   • 20 bps: Lower precision, higher coverage, fewer bins needed for wide ranges")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    print(f"   • 5 bps: Best for stablecoins, major crypto, high-frequency trading")
    print(f"   • 20 bps: Best for altcoins, long-tail assets, volatile markets")
    print(f"   • 20 bps: More gas efficient for the same coverage range")

if __name__ == "__main__":
    main()
