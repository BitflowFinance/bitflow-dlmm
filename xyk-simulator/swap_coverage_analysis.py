#!/usr/bin/env python3
"""
Swap Coverage Analysis for DLMM

Analyzes price coverage for different bin step sizes with maximum 384 bins per swap,
starting from the active bin and calculating how far we can go in each direction.
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
    max_bins_per_side: int  # 384 bins per direction
    right_coverage_pct: float  # How much higher we can go
    left_coverage_pct: float   # How much lower we can go
    total_coverage_pct: float  # Total range covered
    price_range: str
    right_bin_id: int
    left_bin_id: int
    right_price_multiplier: float
    left_price_multiplier: float

def calculate_swap_coverage(bin_step_bps: int, max_total_bins: int = 384):
    """
    Calculate price coverage for a given bin step size with maximum bins per swap
    
    Args:
        bin_step_bps: Bin step in basis points
        max_total_bins: Maximum total bins per swap (default 384)
    
    Returns:
        BinStepAnalysis object with coverage details
    """
    
    # Convert basis points to decimal
    bin_step = bin_step_bps / 10000
    
    # Maximum bins per side (using 384 bins in each direction)
    max_bins_per_side = max_total_bins  # 384 bins per direction
    
    # Active bin ID
    active_bin_id = 500
    
    # Calculate price coverage in each direction
    # Price at bin i = P_active * (1 + bin_step)^(i - active_bin_id)
    # For 192 bins to the right: price = (1 + bin_step)^192
    # For 192 bins to the left: price = (1 + bin_step)^(-192)
    
    right_price_multiplier = (1 + bin_step) ** max_bins_per_side
    left_price_multiplier = (1 + bin_step) ** (-max_bins_per_side)
    
    # Calculate percentage changes relative to active bin
    right_coverage_pct = (right_price_multiplier - 1) * 100
    left_coverage_pct = (1 - left_price_multiplier) * 100
    total_coverage_pct = right_coverage_pct + left_coverage_pct
    
    # Calculate bin IDs
    right_bin_id = active_bin_id + max_bins_per_side
    left_bin_id = active_bin_id - max_bins_per_side
    
    # Price range string
    price_range = f"{(1/right_price_multiplier):.4f}x to {right_price_multiplier:.4f}x"
    
    return BinStepAnalysis(
        bin_step_bps=bin_step_bps,
        bin_step_decimal=bin_step,
        max_bins_per_side=max_bins_per_side,
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
    """Analyze swap coverage for different bin step sizes"""
    
    # Bin step sizes to analyze (in basis points)
    bin_step_sizes = [1, 5, 10, 25, 50, 100]
    
    # Calculate coverage for each bin step size
    results = []
    for bin_step_bps in bin_step_sizes:
        result = calculate_swap_coverage(bin_step_bps, 384)
        results.append(result)
    
    print("=" * 120)
    print("DLMM SWAP COVERAGE ANALYSIS - MAXIMUM 384 BINS PER SWAP")
    print("=" * 120)
    print()
    
    print(f"📊 CONFIGURATION:")
    print(f"   Maximum bins per swap: 768 (384 in each direction)")
    print(f"   Maximum bins per side: 384")
    print(f"   Active bin ID: 500")
    print(f"   Coverage calculated from active bin outward")
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
        print(f"   • Bins used: {result.max_bins_per_side * 2} (384 per direction)")
    
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
    
    # Key insights
    print("=" * 120)
    print("KEY INSIGHTS:")
    print("=" * 120)
    
    print(f"\n🎯 COVERAGE PATTERNS:")
    print(f"   • 1 bps: ±{results[0].total_coverage_pct/2:.2f}% - Ultra-precise, limited range")
    print(f"   • 5 bps: ±{results[1].total_coverage_pct/2:.2f}% - Good precision, moderate range")
    print(f"   • 10 bps: ±{results[2].total_coverage_pct/2:.2f}% - Balanced precision/range")
    print(f"   • 25 bps: ±{results[3].total_coverage_pct/2:.2f}% - Good range, moderate precision")
    print(f"   • 50 bps: ±{results[4].total_coverage_pct/2:.2f}% - Wide range, lower precision")
    print(f"   • 100 bps: ±{results[5].total_coverage_pct/2:.2f}% - Maximum range, lowest precision")
    
    print(f"\n💡 SWAP OPTIMIZATION:")
    print(f"   • 384 bins provide maximum flexibility for large trades")
    print(f"   • Larger bin steps = wider price coverage per bin")
    print(f"   • Smaller bin steps = higher price precision but limited range")
    print(f"   • 25-50 bps optimal for most volatile assets")
    print(f"   • 1-5 bps optimal for stable assets requiring precision")

if __name__ == "__main__":
    main()
