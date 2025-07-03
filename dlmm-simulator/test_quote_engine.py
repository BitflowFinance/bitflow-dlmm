#!/usr/bin/env python3
"""
Test script for the DLMM Quote Engine.
Demonstrates quote calculation for different route types.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.quote_engine import MockRedisClient, QuoteEngine, RouteType


def format_amount(amount: float, decimals: int = 18) -> str:
    """Format amount with proper decimal places"""
    return f"{amount:.6f}"


def print_quote_result(quote, title: str):
    """Print formatted quote result"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    if not quote.success:
        print(f"❌ Quote failed: {quote.error}")
        return
    
    print(f"✅ Quote successful!")
    print(f"Route Type: {quote.route_type.value}")
    print(f"Token In: {quote.token_in}")
    print(f"Token Out: {quote.token_out}")
    print(f"Amount In: {format_amount(quote.amount_in)} {quote.token_in}")
    print(f"Amount Out: {format_amount(quote.amount_out)} {quote.token_out}")
    print(f"Price Impact: {quote.price_impact:.4f}%")
    print(f"Estimated Gas: {quote.estimated_gas:,}")
    
    if quote.steps:
        print(f"\nRoute Steps ({len(quote.steps)} steps):")
        for i, step in enumerate(quote.steps, 1):
            print(f"  Step {i}: {step.pool_id} (Bin {step.bin_id})")
            print(f"    {format_amount(step.amount_in)} {step.token_in} → {format_amount(step.amount_out)} {step.token_out}")
            print(f"    Price: ${step.price:.2f}, Impact: {step.price_impact:.4f}%")


def main():
    """Main test function"""
    print("🚀 DLMM Quote Engine Test")
    print("=" * 60)
    
    # Initialize quote engine
    redis_client = MockRedisClient()
    quote_engine = QuoteEngine(redis_client)
    
    # Test cases
    test_cases = [
        {
            "title": "Single Pool Quote (BTC → USDC)",
            "token_in": "BTC",
            "token_out": "USDC", 
            "amount_in": 1.0,  # 1 BTC (remove 1e18 scaling)
            "expected_type": RouteType.MULTI_BIN
        },
        {
            "title": "Multi-Pool Quote (BTC → USDC)",
            "token_in": "BTC",
            "token_out": "USDC",
            "amount_in": 5.0,  # 5 BTC (remove 1e18 scaling)
            "expected_type": RouteType.MULTI_POOL
        },
        {
            "title": "Multi-Pair Quote (BTC → ETH → USDC)",
            "token_in": "BTC", 
            "token_out": "USDC",
            "amount_in": 2.0,  # 2 BTC (remove 1e18 scaling)
            "expected_type": RouteType.MULTI_PAIR
        },
        {
            "title": "ETH → USDC Quote",
            "token_in": "ETH",
            "token_out": "USDC", 
            "amount_in": 10.0,  # 10 ETH (remove 1e18 scaling)
            "expected_type": RouteType.MULTI_BIN
        },
        {
            "title": "Invalid Route Test",
            "token_in": "BTC",
            "token_out": "INVALID",
            "amount_in": 1.0,  # Remove 1e18 scaling
            "expected_type": None
        }
    ]
    
    # Run test cases
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['title']}")
        
        quote = quote_engine.get_quote(
            test_case["token_in"],
            test_case["token_out"], 
            test_case["amount_in"]
        )
        
        print_quote_result(quote, test_case["title"])
    
    # Test Redis cache data
    print(f"\n{'='*60}")
    print("📊 Redis Cache Data Overview")
    print(f"{'='*60}")
    
    # Show available pools
    pools = []
    for key in redis_client.keys("pool:*"):
        pool_id = key.split(":")[1]
        pool_data = redis_client.data[key]
        pools.append({
            "id": pool_id,
            "tokens": f"{pool_data['token_x']}-{pool_data['token_y']}",
            "bin_step": f"{pool_data['bin_step']} bps",
            "tvl": float(pool_data['total_tvl'])  # Remove 1e18 scaling
        })
    
    print(f"Available Pools ({len(pools)}):")
    for pool in pools:
        print(f"  • {pool['id']}: {pool['tokens']} ({pool['bin_step']}) - TVL: ${pool['tvl']}")
    
    # Show available pairs
    pairs = []
    for key in redis_client.keys("pairs:*"):
        tokens = key.split(":")[1:]
        pair_data = redis_client.data[key]
        pairs.append({
            "pair": f"{tokens[0]}-{tokens[1]}",
            "pools": len(pair_data["pools"]),
            "best_pool": pair_data["best_pool"]
        })
    
    print(f"\nAvailable Pairs ({len(pairs)}):")
    for pair in pairs:
        print(f"  • {pair['pair']}: {pair['pools']} pools (best: {pair['best_pool']})")
    
    # Show bin distribution for BTC-USDC-25
    print(f"\nBin Distribution (BTC-USDC-25):")
    btc_usdc_bins = []
    for key in redis_client.keys("bin:BTC-USDC-25:*"):
        bin_id = int(key.split(":")[-1])
        bin_data = redis_client.data[key]
        if float(bin_data["x_amount"]) > 0 or float(bin_data["y_amount"]) > 0:
            btc_usdc_bins.append({
                "id": bin_id,
                "x": float(bin_data["x_amount"]),  # Remove 1e18 scaling
                "y": float(bin_data["y_amount"]),  # Remove 1e18 scaling
                "price": float(bin_data["price"])  # Remove 1e18 scaling
            })
    
    # Show active bin and nearby bins
    active_bin = next((b for b in btc_usdc_bins if b["id"] == 500), None)
    if active_bin:
        print(f"  Active Bin 500: {active_bin['x']} BTC, {active_bin['y']} USDC @ ${active_bin['price']}")
    
    # Show some nearby bins
    nearby_bins = [b for b in btc_usdc_bins if 495 <= b["id"] <= 505]
    print(f"  Nearby Bins (495-505): {len(nearby_bins)} bins with liquidity")


if __name__ == "__main__":
    main() 