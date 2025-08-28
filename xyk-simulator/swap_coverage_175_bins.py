#!/usr/bin/env python3
"""
Swap Coverage Analysis for DLMM - 175 Total Bins

Analyzes price coverage for different bin step sizes with 175 total bins,
going ±87.5 bins in each direction from the active bin.
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class BinStepAnalysis:
    """Analysis results for a specific bin step size"""
    bin_step_bps: int
    bin_step_decimal: float
    bins_per_side: int  # 87 bins per direction (175/2)
    right_coverage_pct: float  # How much higher we can go
    left_coverage_pct: float   # How much lower we can go
    total_coverage_pct: float  # Total range covered
    price_range: str
    right_bin_id: int
    left_bin_id: int
    right_price_multiplier: float
    left_price_multiplier: float

def calculate_swap_coverage_175(bin_step_bps: int, total_bins: int = 175):
    """
    Calculate price coverage for a given bin step size with 175 total bins
    
    Args:
        bin_step_bps: Bin step in basis points
        total_bins: Total bins to distribute (default 175)
    
    Returns:
        BinStepAnalysis object with coverage details
    """
    
    # Convert basis points to decimal
    bin_step = bin_step_bps / 10000
    
    # Bins per side (175 total = 87 bins per direction)
    bins_per_side = total_bins // 2  # 87 bins per direction
    
    # Active bin ID
    active_bin_id = 500
    
    # Calculate price coverage in each direction
    # Price at bin i = P_active * (1 + bin_step)^(i - active_bin_id)
    # For 87.5 bins to the right: price = (1 + bin_step)^87.5
    # For 87.5 bins to the left: price = (1 + bin_step)^(-87.5)
    
    right_price_multiplier = (1 + bin_step) ** bins_per_side
    left_price_multiplier = (1 + bin_step) ** (-bins_per_side)
    
    # Calculate percentage changes relative to active bin
    right_coverage_pct = (right_price_multiplier - 1) * 100
    left_coverage_pct = (1 - left_price_multiplier) * 100
    total_coverage_pct = right_coverage_pct + left_coverage_pct
    
    # Calculate bin IDs
    right_bin_id = active_bin_id + bins_per_side
    left_bin_id = active_bin_id - bins_per_side
    
    # Price range string
    price_range = f"{(1/right_price_multiplier):.4f}x to {right_price_multiplier:.4f}x"
    
    return BinStepAnalysis(
        bin_step_bps=bin_step_bps,
        bin_step_decimal=bin_step,
        bins_per_side=bins_per_side,
        right_coverage_pct=right_coverage_pct,
        left_coverage_pct=left_coverage_pct,
        total_coverage_pct=total_coverage_pct,
        price_range=price_range,
        right_bin_id=right_bin_id,
        left_bin_id=left_bin_id,
        right_price_multiplier=right_price_multiplier,
        left_price_multiplier=left_price_multiplier
    )

def main():
    """Analyze swap coverage for different bin step sizes with 175 total bins"""
    
    # Bin step sizes to analyze (in basis points)
    bin_step_sizes = [1, 5, 10, 25, 50, 100]
    
    # Calculate coverage for each bin step size
    results = []
    for bin_step_bps in bin_step_sizes:
        result = calculate_swap_coverage_175(bin_step_bps, 175)
        results.append(result)
    
    print("=" * 120)
    print("DLMM SWAP COVERAGE ANALYSIS - 175 TOTAL BINS (±87 BINS PER DIRECTION)")
    print("=" * 120)
    print()
    
    print(f"📊 CONFIGURATION:")
    print(f"   Total bins per swap: 175")
    print(f"   Bins per side: 87")
    print(f"   Active bin ID: 500")
    print(f"   Coverage calculated from active bin outward (±87 bins)")
    print()
    
    # Create results table
    print("📈 PRICE COVERAGE RESULTS:")
    print("-" * 120)
    
    # Header
    print(f"{'Bin Step':<12} {'Bin Step':<12} {'Right':<12} {'Left':<12} {'Total':<12} {'Lower':<12} {'Upper':<12} {'Bin Range':<20}")
    print(f"{'(bps)':<12} {'(decimal)':<12} {'Coverage':<12} {'Coverage':<12} {'Coverage':<12} {'Price':<12} {'Price':<12} {'(Left-Right)':<20}")
    print(f"{'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*20}")
    
    # Results rows
    for result in results:
        lower_price = result.left_price_multiplier
        upper_price = result.right_price_multiplier
        print(f"{result.bin_step_bps:<12} {result.bin_step_decimal:<12.4f} +{result.right_coverage_pct:<11.2f}% -{result.left_coverage_pct:<11.2f}% ±{result.total_coverage_pct/2:<11.2f}% {lower_price:<12.4f} {upper_price:<12.4f} [{result.left_bin_id}-{result.right_bin_id}]")
    
    print()
    
    # Detailed breakdown
    print("🔍 DETAILED BREAKDOWN:")
    print("-" * 120)
    
    for result in results:
        print(f"\n🔸 {result.bin_step_bps} bps ({result.bin_step_decimal:.4f}):")
        print(f"   • Right coverage: +{result.right_coverage_pct:.2f}% (bin {result.right_bin_id})")
        print(f"   • Left coverage: -{result.left_coverage_pct:.2f}% (bin {result.left_bin_id})")
        print(f"   • Total range: ±{result.total_coverage_pct/2:.2f}%")
        print(f"   • Price range: {result.price_range}")
        print(f"   • Bins used: {result.bins_per_side * 2} (87 per direction)")
    
    print()
    
    # Asset type comparison
    print("📊 ASSET TYPE SUITABILITY:")
    print("-" * 120)
    
    asset_types = [
        ("Stablecoins", 0.1),
        ("Major crypto", 3.0),
        ("Mid-cap altcoins", 6.0),
        ("Long-tail assets", 12.0),
        ("Leveraged tokens", 20.0)
    ]
    
    print(f"{'Asset Type':<20} {'Daily Vol':<12} {'1 bps':<12} {'5 bps':<12} {'10 bps':<12} {'25 bps':<12} {'50 bps':<12} {'100 bps':<12}")
    print(f"{'-'*20} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    
    for asset_name, daily_vol in asset_types:
        coverage_values = []
        for result in results:
            coverage = result.total_coverage_pct / daily_vol
            coverage_values.append(f"{coverage:.1f}x")
        
        print(f"{asset_name:<20} ±{daily_vol:<11.1f}% {coverage_values[0]:<12} {coverage_values[1]:<12} {coverage_values[2]:<12} {coverage_values[3]:<12} {coverage_values[4]:<12} {coverage_values[5]:<12}")
    
    print()
    
    # Comparison with 384 bins analysis
    print("=" * 120)
    print("COMPARISON WITH 384 BINS PER DIRECTION:")
    print("=" * 120)
    
    print(f"\n🔍 COVERAGE COMPARISON:")
    print(f"   • 175 total bins (±87 per direction) vs 768 total bins (±384 per direction)")
    print(f"   • 175 bins provide approximately 1/4 the coverage of 384 bins per direction")
    print(f"   • More suitable for smaller trades or higher precision requirements")
    print(f"   • Better gas efficiency for the same bin step size")
    
    print(f"\n💡 USE CASES:")
    print(f"   • 175 bins: Smaller trades, higher precision, gas efficiency")
    print(f"   • 384 bins: Larger trades, wider coverage, maximum flexibility")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    print(f"   • 175 bins: Best for stable assets and moderate volatility")
    print(f"   • 384 bins: Best for volatile assets and extreme market conditions")

if __name__ == "__main__":
    main()
