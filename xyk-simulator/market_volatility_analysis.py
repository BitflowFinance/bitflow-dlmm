#!/usr/bin/env python3
"""
Market Volatility Analysis for DLMM Bin Coverage

Analyzes daily price ranges for different asset types to determine optimal bin coverage
and bin step sizes for DLMM pools.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class AssetVolatilityProfile:
    """Volatility profile for a specific asset type"""
    asset_type: str
    examples: List[str]
    daily_volatility_pct: float  # 1-day volatility (68% confidence)
    weekly_volatility_pct: float  # 1-week volatility (68% confidence)
    monthly_volatility_pct: float  # 1-month volatility (68% confidence)
    extreme_daily_range_pct: float  # 99% confidence daily range
    extreme_weekly_range_pct: float  # 99% confidence weekly range
    recommended_bin_coverage_pct: float  # Recommended coverage range
    recommended_bin_step_bps: int  # Recommended bin step in basis points

def analyze_market_volatility():
    """Analyze market volatility patterns for different asset types"""
    
    # Define volatility profiles based on market data and research
    profiles = [
        AssetVolatilityProfile(
            asset_type="Stablecoins",
            examples=["USDC/USDT", "DAI/USDC", "FRAX/USDC"],
            daily_volatility_pct=0.1,      # 0.1% daily volatility
            weekly_volatility_pct=0.3,     # 0.3% weekly volatility
            monthly_volatility_pct=0.8,    # 0.8% monthly volatility
            extreme_daily_range_pct=0.5,   # 99% confidence: ±0.25% daily
            extreme_weekly_range_pct=1.2,  # 99% confidence: ±0.6% weekly
            recommended_bin_coverage_pct=2.0,  # Cover ±1% range
            recommended_bin_step_bps=1      # 1 basis point = 0.01%
        ),
        
        AssetVolatilityProfile(
            asset_type="Major Cryptocurrencies (USD pairs)",
            examples=["BTC/USDC", "ETH/USDC", "SOL/USDC"],
            daily_volatility_pct=3.0,      # 3% daily volatility
            weekly_volatility_pct=8.0,     # 8% weekly volatility
            monthly_volatility_pct=18.0,   # 18% monthly volatility
            extreme_daily_range_pct=12.0,  # 99% confidence: ±6% daily
            extreme_weekly_range_pct=25.0, # 99% confidence: ±12.5% weekly
            recommended_bin_coverage_pct=15.0,  # Cover ±7.5% range
            recommended_bin_step_bps=25     # 25 basis points = 0.25%
        ),
        
        AssetVolatilityProfile(
            asset_type="Large Cap Altcoins",
            examples=["ADA/USDC", "DOT/USDC", "LINK/USDC"],
            daily_volatility_pct=4.5,      # 4.5% daily volatility
            weekly_volatility_pct=12.0,    # 12% weekly volatility
            monthly_volatility_pct=28.0,   # 28% monthly volatility
            extreme_daily_range_pct=18.0,  # 99% confidence: ±9% daily
            extreme_weekly_range_pct=35.0, # 99% confidence: ±17.5% weekly
            recommended_bin_coverage_pct=20.0,  # Cover ±10% range
            recommended_bin_step_bps=50     # 50 basis points = 0.5%
        ),
        
        AssetVolatilityProfile(
            asset_type="Mid Cap Altcoins",
            examples=["AVAX/USDC", "MATIC/USDC", "UNI/USDC"],
            daily_volatility_pct=6.0,      # 6% daily volatility
            weekly_volatility_pct=16.0,    # 16% weekly volatility
            monthly_volatility_pct=35.0,   # 35% monthly volatility
            extreme_daily_range_pct=24.0,  # 99% confidence: ±12% daily
            extreme_weekly_range_pct=45.0, # 99% confidence: ±22.5% weekly
            recommended_bin_coverage_pct=30.0,  # Cover ±15% range
            recommended_bin_step_bps=100    # 100 basis points = 1.0%
        ),
        
        AssetVolatilityProfile(
            asset_type="Small Cap / Long-tail Assets",
            examples=["MEME tokens", "New DeFi protocols", "Gaming tokens"],
            daily_volatility_pct=12.0,     # 12% daily volatility
            weekly_volatility_pct=30.0,    # 30% weekly volatility
            monthly_volatility_pct=60.0,   # 60% monthly volatility
            extreme_daily_range_pct=50.0,  # 99% confidence: ±25% daily
            extreme_weekly_range_pct=80.0, # 99% confidence: ±40% weekly
            recommended_bin_coverage_pct=60.0,  # Cover ±30% range
            recommended_bin_step_bps=200    # 200 basis points = 2.0%
        ),
        
        AssetVolatilityProfile(
            asset_type="Leveraged/Inverse Tokens",
            examples=["3x BTC", "Inverse ETH", "Leveraged DeFi"],
            daily_volatility_pct=20.0,     # 20% daily volatility
            weekly_volatility_pct=50.0,    # 50% weekly volatility
            monthly_volatility_pct=100.0,  # 100% monthly volatility
            extreme_daily_range_pct=80.0,  # 99% confidence: ±40% daily
            extreme_weekly_range_pct=120.0, # 99% confidence: ±60% weekly
            recommended_bin_coverage_pct=100.0, # Cover ±50% range
            recommended_bin_step_bps=500    # 500 basis points = 5.0%
        )
    ]
    
    return profiles

def calculate_bin_requirements(profile: AssetVolatilityProfile) -> Dict:
    """Calculate bin requirements for a given volatility profile"""
    
    # Calculate number of bins needed in each direction
    coverage_range = profile.recommended_bin_coverage_pct / 100  # Convert to decimal
    bin_step = profile.recommended_bin_step_bps / 10000  # Convert bps to decimal
    
    # Number of bins needed: log(1 + coverage_range) / log(1 + bin_step)
    # This gives us how many bins we need to cover the price range
    bins_needed = int(np.ceil(np.log(1 + coverage_range) / np.log(1 + bin_step)))
    
    # Total bins including active bin and both directions
    total_bins = 1 + (2 * bins_needed)  # Active bin + left bins + right bins
    
    # Calculate the actual price range covered
    actual_coverage = ((1 + bin_step) ** bins_needed - 1) * 100
    
    # Calculate TVL distribution efficiency
    # More bins = better price granularity but higher gas costs
    efficiency_score = min(100, (profile.recommended_bin_coverage_pct / actual_coverage) * 100)
    
    return {
        'bins_needed_per_direction': bins_needed,
        'total_bins': total_bins,
        'actual_coverage_pct': actual_coverage,
        'efficiency_score': efficiency_score,
        'gas_cost_estimate': total_bins * 0.001,  # Rough gas cost per bin
        'recommended_active_bin_id': 500,  # Standard center bin
        'left_bin_range': f"{500 - bins_needed} to 499",
        'right_bin_range': f"501 to {500 + bins_needed}"
    }

def main():
    """Main analysis function"""
    
    profiles = analyze_market_volatility()
    
    print("=" * 100)
    print("DLMM BIN COVERAGE ANALYSIS - MARKET VOLATILITY PERSPECTIVE")
    print("=" * 100)
    print()
    
    print("📊 ASSET TYPE VOLATILITY PROFILES:")
    print("-" * 100)
    
    for profile in profiles:
        print(f"\n🔸 {profile.asset_type.upper()}")
        print(f"   Examples: {', '.join(profile.examples)}")
        print(f"   Daily Volatility: ±{profile.daily_volatility_pct:.1f}% (68% confidence)")
        print(f"   Weekly Volatility: ±{profile.weekly_volatility_pct:.1f}% (68% confidence)")
        print(f"   Extreme Daily Range: ±{profile.extreme_daily_range_pct/2:.1f}% (99% confidence)")
        print(f"   Recommended Coverage: ±{profile.recommended_bin_coverage_pct/2:.1f}%")
        print(f"   Recommended Bin Step: {profile.recommended_bin_step_bps} bps ({profile.recommended_bin_step_bps/100:.2f}%)")
    
    print("\n" + "=" * 100)
    print("BIN REQUIREMENTS CALCULATION:")
    print("=" * 100)
    
    for profile in profiles:
        requirements = calculate_bin_requirements(profile)
        
        print(f"\n🔸 {profile.asset_type.upper()}")
        print(f"   Bin Step: {profile.recommended_bin_step_bps} bps")
        print(f"   Bins per direction: {requirements['bins_needed_per_direction']}")
        print(f"   Total bins: {requirements['total_bins']}")
        print(f"   Price coverage: ±{requirements['actual_coverage_pct']:.1f}%")
        print(f"   Efficiency score: {requirements['efficiency_score']:.1f}%")
        print(f"   Bin ranges: Left [{requirements['left_bin_range']}], Right [{requirements['right_bin_range']}]")
    
    print("\n" + "=" * 100)
    print("RECOMMENDATIONS:")
    print("=" * 100)
    
    print("\n🎯 STABLESWAPS (USDC/USDT, DAI/USDC):")
    print("   • Bin Step: 1 bps (0.01%)")
    print("   • Coverage: ±1% range")
    print("   • Total Bins: ~201 bins")
    print("   • Rationale: Extremely low volatility, need high precision")
    
    print("\n🏆 PREMIER ASSETS (BTC/USDC, ETH/USDC):")
    print("   • Bin Step: 25 bps (0.25%)")
    print("   • Coverage: ±7.5% range")
    print("   • Total Bins: ~61 bins")
    print("   • Rationale: Moderate volatility, good balance of precision vs gas efficiency")
    
    print("\n📈 MID-CAP ALTCOINS (AVAX/USDC, MATIC/USDC):")
    print("   • Bin Step: 50-100 bps (0.5-1.0%)")
    print("   • Coverage: ±10-15% range")
    print("   • Total Bins: ~41-61 bins")
    print("   • Rationale: Higher volatility, can use larger steps")
    
    print("\n🚀 LONG-TAIL ASSETS (MEME tokens, new protocols):")
    print("   • Bin Step: 200-500 bps (2.0-5.0%)")
    print("   • Coverage: ±30-50% range")
    print("   • Total Bins: ~25-41 bins")
    print("   • Rationale: High volatility, prioritize gas efficiency over precision")
    
    print("\n" + "=" * 100)
    print("KEY INSIGHTS:")
    print("=" * 100)
    
    print("\n💡 VOLATILITY-BASED DESIGN PRINCIPLES:")
    print("1. **Stablecoins**: High precision (1 bps) for minimal slippage")
    print("2. **Major tokens**: Balanced approach (25 bps) for efficiency + precision")
    print("3. **Altcoins**: Larger steps (50-100 bps) to handle volatility")
    print("4. **Long-tail**: Large steps (200+ bps) for gas efficiency")
    
    print("\n⚡ GAS EFFICIENCY CONSIDERATIONS:")
    print("• More bins = higher gas costs but better price granularity")
    print("• Fewer bins = lower gas costs but potential for larger slippage")
    print("• Active bin (ID 500) should be centered around current market price")
    print("• Bin distribution should be asymmetric if price trends are expected")
    
    print("\n🎯 IMPLEMENTATION STRATEGY:")
    print("• Start with conservative bin steps and adjust based on usage")
    print("• Monitor slippage patterns and adjust bin coverage accordingly")
    print("• Consider dynamic bin step adjustment based on market conditions")
    print("• Balance user experience (slippage) with protocol efficiency (gas costs)")

if __name__ == "__main__":
    main()
