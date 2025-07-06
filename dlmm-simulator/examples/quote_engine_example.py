#!/usr/bin/env python3
"""
Example integration of the DLMM Quote Engine for frontend applications.
This demonstrates how to use the quote engine in a web application context.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.quote_engine import MockRedisClient, QuoteEngine, RouteType
import json
from typing import Dict, Any


class QuoteEngineAPI:
    """
    API wrapper for the DLMM Quote Engine.
    This can be easily integrated into a web framework like FastAPI or Flask.
    """
    
    def __init__(self):
        self.redis_client = MockRedisClient()
        self.quote_engine = QuoteEngine(self.redis_client)
    
    def get_quote(self, token_in: str, token_out: str, amount_in: float) -> Dict[str, Any]:
        """
        Get a quote for swapping tokens.
        
        Args:
            token_in: Input token symbol (e.g., "BTC")
            token_out: Output token symbol (e.g., "USDC")
            amount_in: Input amount (e.g., 1.5 for 1.5 BTC)
            
        Returns:
            Dictionary with quote information
        """
        # Get quote from engine (amount_in is already a float)
        quote = self.quote_engine.get_quote(token_in, token_out, amount_in)
        
        # Format response
        return self._format_quote_response(quote)
    
    def get_available_tokens(self) -> Dict[str, Any]:
        """Get list of available tokens and pairs"""
        tokens = set()
        pairs = []
        
        # Extract tokens from pool data
        for key in self.redis_client.keys("pool:*"):
            pool_data = self.redis_client.data[key]
            tokens.add(pool_data["token_x"])
            tokens.add(pool_data["token_y"])
        
        # Extract pairs
        for key in self.redis_client.keys("pairs:*"):
            tokens = key.split(":")[1:]
            pair_data = self.redis_client.data[key]
            pairs.append({
                "pair": f"{tokens[0]}-{tokens[1]}",
                "pools": pair_data["pools"],
                "last_updated": pair_data["last_updated"]
            })
        
        print("📊 Pairs Data:")
        for pair in pairs:
            print(f"  • {pair['pair']}: {pair['pools']} pools")
        
        return {
            "tokens": list(tokens),
            "pairs": pairs
        }
    
    def get_pool_info(self, pool_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific pool"""
        pool_key = f"pool:{pool_id}"
        if pool_key not in self.redis_client.data:
            return {"error": "Pool not found"}
        
        pool_data = self.redis_client.data[pool_key]
        
        # Get bin information
        bins = []
        for key in self.redis_client.keys(f"bin:{pool_id}:*"):
            bin_id = int(key.split(":")[-1])
            bin_data = self.redis_client.data[key]
            if float(bin_data["x_amount"]) > 0 or float(bin_data["y_amount"]) > 0:
                bins.append({
                    "bin_id": bin_id,
                    "x_amount": float(bin_data["x_amount"]),
                    "y_amount": float(bin_data["y_amount"]),
                    "price": float(bin_data["price"]),
                    "is_active": bin_data["is_active"]
                })
        
        return {
            "pool_id": pool_id,
            "token_x": pool_data["token_x"],
            "token_y": pool_data["token_y"],
            "bin_step": pool_data["bin_step"],
            "active_bin_id": pool_data["active_bin_id"],
            "active_bin_price": float(pool_data["active_bin_price"]),
            "total_tvl": float(pool_data["total_tvl"]),
            "status": pool_data["status"],
            "bins": bins
        }
    
    def _format_quote_response(self, quote) -> Dict[str, Any]:
        """Format quote result for API response"""
        if not quote.success:
            return {
                "success": False,
                "error": quote.error,
                "token_in": quote.token_in,
                "token_out": quote.token_out,
                "amount_in": quote.amount_in
            }
        
        # Format steps
        steps = []
        for step in quote.steps:
            steps.append({
                "pool_id": step.pool_id,
                "bin_id": step.bin_id,
                "token_in": step.token_in,
                "token_out": step.token_out,
                "amount_in": step.amount_in,
                "amount_out": step.amount_out,
                "price": step.price,
                "price_impact": step.price_impact
            })
        
        return {
            "success": True,
            "token_in": quote.token_in,
            "token_out": quote.token_out,
            "amount_in": quote.amount_in,
            "amount_out": quote.amount_out,
            "price_impact": quote.price_impact,
            "route_type": quote.route_type.value,
            "estimated_gas": quote.estimated_gas,
            "steps": steps,
            "effective_price": quote.amount_out / quote.amount_in if quote.amount_in > 0 else 0
        }


def main():
    """Example usage of the Quote Engine API"""
    print("🚀 DLMM Quote Engine API Example")
    print("=" * 60)
    
    # Initialize API
    api = QuoteEngineAPI()
    
    # Example 1: Get available tokens and pairs
    print("\n📋 Available Tokens and Pairs:")
    tokens_info = api.get_available_tokens()
    print(f"Tokens: {', '.join(tokens_info['tokens'])}")
    print("Pairs:")
    for pair in tokens_info["pairs"]:
        print(f"  • {pair['pair']}: {pair['pools']} pools")
    
    # Example 2: Get quote for BTC to USDC
    print("\n💰 Quote Examples:")
    
    # Small trade
    quote1 = api.get_quote("BTC", "USDC", 0.1)
    print(f"0.1 BTC → USDC:")
    print(f"  Amount out: {quote1['amount_out']:.2f} USDC")
    print(f"  Price impact: {quote1['price_impact']:.4f}%")
    print(f"  Route type: {quote1['route_type']}")
    print(f"  Steps: {len(quote1['steps'])}")
    
    # Large trade
    quote2 = api.get_quote("BTC", "USDC", 5.0)
    print(f"\n5.0 BTC → USDC:")
    print(f"  Amount out: {quote2['amount_out']:.2f} USDC")
    print(f"  Price impact: {quote2['price_impact']:.4f}%")
    print(f"  Route type: {quote2['route_type']}")
    print(f"  Steps: {len(quote2['steps'])}")
    
    # ETH to USDC
    quote3 = api.get_quote("ETH", "USDC", 10.0)
    print(f"\n10.0 ETH → USDC:")
    print(f"  Amount out: {quote3['amount_out']:.2f} USDC")
    print(f"  Price impact: {quote3['price_impact']:.4f}%")
    print(f"  Route type: {quote3['route_type']}")
    print(f"  Steps: {len(quote3['steps'])}")
    
    # Example 3: Get pool information
    print("\n🏊 Pool Information:")
    pool_info = api.get_pool_info("BTC-USDC-25")
    print(f"Pool: {pool_info['pool_id']}")
    print(f"Tokens: {pool_info['token_x']}-{pool_info['token_y']}")
    print(f"Bin step: {pool_info['bin_step']} bps")
    print(f"Active bin: {pool_info['active_bin_id']}")
    print(f"Active price: ${pool_info['active_bin_price']:.2f}")
    print(f"Total TVL: ${pool_info['total_tvl']:.2f}")
    print(f"Bins with liquidity: {len(pool_info['bins'])}")
    
    # Example 4: Error handling
    print("\n❌ Error Handling:")
    invalid_quote = api.get_quote("BTC", "INVALID", 1.0)
    print(f"Invalid route: {invalid_quote['error']}")
    
    # Example 5: JSON response format
    print("\n📄 JSON Response Format:")
    sample_quote = api.get_quote("BTC", "USDC", 1.0)
    print(json.dumps(sample_quote, indent=2))


if __name__ == "__main__":
    main() 