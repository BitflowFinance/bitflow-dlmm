#!/usr/bin/env python3
"""
Bin Coverage Calculator for DLMM

Calculates the exact price coverage for a given bin step and number of bins.
"""

import numpy as np

def calculate_bin_coverage(bin_step_bps: int, bins_per_side: int):
    """
    Calculate price coverage for a given bin step and number of bins per side
    
    Args:
        bin_step_bps: Bin step in basis points
        bins_per_side: Number of bins on each side of active bin
    
    Returns:
        Dictionary with coverage details
    """
    
    # Convert basis points to decimal
    bin_step = bin_step_bps / 10000  # 5 bps = 0.0005
    
    # Calculate price coverage in each direction
    # Price at bin i = P_active * (1 + bin_step)^(i - active_bin_id)
    # For 100 bins to the right: price = (1 + 0.0005)^100
    # For 100 bins to the left: price = (1 + 0.0005)^(-100)
    
    right_price_multiplier = (1 + bin_step) ** bins_per_side
    left_price_multiplier = (1 + bin_step) ** (-bins_per_side)
    
    # Calculate percentage changes
    right_coverage_pct = (right_price_multiplier - 1) * 100
    left_coverage_pct = (1 - left_price_multiplier) * 100
    
    # Total coverage range
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
        'total_bins': 1 + (2 * bins_per_side),  # Active bin + left + right
        'right_coverage_pct': right_coverage_pct,
        'left_coverage_pct': left_coverage_pct,
        'total_coverage_pct': total_coverage_pct,
        'price_range': f"{(1/right_price_multiplier):.4f}x to {right_price_multiplier:.4f}x",
        'left_bin_range': left_bin_range,
        'right_bin_range': right_bin_range,
        'example_prices': example_prices
    }

def main():
    """Calculate coverage for 5 bps bin step with 100 bins per side"""
    
    bin_step_bps = 5  # 5 basis points
    bins_per_side = 100  # 100 bins on each side
    
    result = calculate_bin_coverage(bin_step_bps, bins_per_side)
    
    print("=" * 80)
    print("DLMM BIN COVERAGE CALCULATION")
    print("=" * 80)
    print()
    
    print(f"📊 CONFIGURATION:")
    print(f"   Bin Step: {result['bin_step_bps']} bps ({result['bin_step_decimal']:.4f})")
    print(f"   Bins per side: {result['bins_per_side']}")
    print(f"   Total bins: {result['total_bins']}")
    print(f"   Active bin ID: 500")
    print()
    
    print(f"📈 PRICE COVERAGE:")
    print(f"   Right side (higher prices): +{result['right_coverage_pct']:.4f}%")
    print(f"   Left side (lower prices): -{result['left_coverage_pct']:.4f}%")
    print(f"   Total coverage range: ±{result['total_coverage_pct']/2:.4f}%")
    print(f"   Price range: {result['price_range']}")
    print()
    
    print(f"🎯 BIN RANGES:")
    print(f"   Left bins: [{result['left_bin_range']}]")
    print(f"   Right bins: [{result['right_bin_range']}]")
    print()
    
    print(f"💡 EXAMPLE BIN PRICES:")
    print(f"   {'Bin ID':<8} {'Distance':<10} {'Multiplier':<12} {'Change %':<10}")
    print(f"   {'-'*8} {'-'*10} {'-'*12} {'-'*10}")
    
    for price_info in result['example_prices']:
        print(f"   {price_info['bin_id']:<8} {price_info['distance']:<10} {price_info['price_multiplier']:<12.4f} {price_info['price_change_pct']:<10.4f}")
    
    print()
    print("=" * 80)
    print("INTERPRETATION:")
    print("=" * 80)
    print()
    
    print(f"🔍 For a 5 bps bin step with 100 bins on each side:")
    print(f"   • You can cover price movements from -{result['left_coverage_pct']:.2f}% to +{result['right_coverage_pct']:.2f}%")
    print(f"   • This covers approximately ±{result['total_coverage_pct']/2:.2f}% price range")
    print(f"   • Price at leftmost bin: {result['price_range'].split(' to ')[0]}x of active bin price")
    print(f"   • Price at rightmost bin: {result['price_range'].split(' to ')[1]}x of active bin price")
    print()
    
    # Compare to our volatility analysis
    print(f"📊 COMPARISON TO ASSET TYPES:")
    print(f"   • Stablecoins (0.1% daily): ✅ Covers {result['total_coverage_pct']/0.1:.1f}x daily range")
    print(f"   • Major crypto (3% daily): ✅ Covers {result['total_coverage_pct']/3:.1f}x daily range")
    print(f"   • Mid-cap altcoins (6% daily): ✅ Covers {result['total_coverage_pct']/6:.1f}x daily range")
    print(f"   • Long-tail assets (12% daily): ✅ Covers {result['total_coverage_pct']/12:.1f}x daily range")
    print(f"   • Leveraged tokens (20% daily): ✅ Covers {result['total_coverage_pct']/20:.1f}x daily range")

if __name__ == "__main__":
    main()
