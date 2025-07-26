#!/usr/bin/env python3
"""
FastAPI server for the DLMM Quote Engine.
Provides REST API endpoints for frontend integration.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn

from src.quote_engine import QuoteEngine, RouteType, MockRedisClient


# Pydantic models for API requests/responses
class QuoteRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: float


class QuoteStepResponse(BaseModel):
    pool_id: str
    bin_id: int
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price: float
    price_impact: float


class QuoteResponse(BaseModel):
    success: bool
    token_in: str
    token_out: str
    amount_in: float
    amount_out: Optional[float] = None
    price_impact: Optional[float] = None
    route_type: Optional[str] = None
    estimated_gas: Optional[int] = None
    steps: Optional[List[QuoteStepResponse]] = None
    effective_price: Optional[float] = None
    error: Optional[str] = None


class TokenInfo(BaseModel):
    token: str
    symbol: str
    decimals: int = 18


class PoolInfo(BaseModel):
    pool_id: str
    token0: str
    token1: str
    bin_step: float
    active_bin: int
    active: bool
    x_protocol_fee: int
    x_provider_fee: int
    x_variable_fee: int
    y_protocol_fee: int
    y_provider_fee: int
    y_variable_fee: int


# Initialize FastAPI app
app = FastAPI(
    title="DLMM Quote Engine API",
    description="API for DLMM routing and quote calculations",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client and quote engine
try:
    # Use MockRedisClient for testing
    redis_client = MockRedisClient()
    print("✅ Using MockRedisClient for testing")
except Exception as e:
    print(f"⚠️ Failed to initialize MockRedisClient: {e}")
    redis_client = MockRedisClient()

quote_engine = QuoteEngine(redis_client)

# Print the actual bin data for the active bin of BTC-USDC-25
try:
    active_bin_key = "bin:BTC-USDC-25:500"
    active_bin_hash = redis_client.hgetall(active_bin_key)
    if active_bin_hash:
        print("DEBUG: Active bin data for BTC-USDC-25:")
        print(active_bin_hash)
    else:
        print("DEBUG: No active bin data found")
except Exception as e:
    print(f"DEBUG: Error getting active bin data: {e}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "DLMM Quote Engine API",
        "version": "1.0.0",
        "endpoints": {
            "GET /quote": "Get quote for token swap",
            "GET /tokens": "Get available tokens",
            "GET /pools": "Get available pools",
            "GET /pools/{pool_id}": "Get specific pool information"
        }
    }


@app.post("/quote", response_model=QuoteResponse)
async def get_quote(request: QuoteRequest):
    """
    Get a quote for swapping tokens.
    
    Args:
        request: QuoteRequest with token_in, token_out, and amount_in
        
    Returns:
        QuoteResponse with quote details or error information
    """
    try:
        # Get quote from engine (amount_in is already a float)
        quote = quote_engine.get_quote(
            request.token_in, 
            request.token_out, 
            request.amount_in
        )
        
        # Format response
        if not quote.success:
            return QuoteResponse(
                success=False,
                token_in=quote.token_in,
                token_out=quote.token_out,
                amount_in=request.amount_in,
                error=quote.error
            )
        
        # Format steps
        steps = []
        for step in quote.steps:
            steps.append(QuoteStepResponse(
                pool_id=step.pool_id,
                bin_id=step.bin_id,
                token_in=step.token_in,
                token_out=step.token_out,
                amount_in=step.amount_in,
                amount_out=step.amount_out,
                price=step.price,
                price_impact=step.price_impact
            ))
        
        # Calculate effective price based on actual amount swapped
        actual_amount_swapped = sum(step.amount_in for step in quote.steps)
        effective_price = quote.amount_out / actual_amount_swapped if actual_amount_swapped > 0 else 0
        
        # Debug output
        print(f"DEBUG: Effective price calculation:")
        print(f"  quote.amount_out: {quote.amount_out}")
        print(f"  actual_amount_swapped: {actual_amount_swapped}")
        print(f"  effective_price: {effective_price}")
        print(f"  Steps:")
        for i, step in enumerate(quote.steps):
            print(f"    Step {i}: amount_in={step.amount_in}, amount_out={step.amount_out}")
        
        return QuoteResponse(
            success=True,
            token_in=quote.token_in,
            token_out=quote.token_out,
            amount_in=request.amount_in,
            amount_out=quote.amount_out,
            price_impact=quote.price_impact,
            route_type=quote.route_type.value,
            estimated_gas=quote.estimated_gas,
            steps=steps,
            effective_price=effective_price
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote calculation failed: {str(e)}")


@app.get("/tokens")
async def get_tokens():
    """Get list of available tokens"""
    tokens = set()
    
    # Extract tokens from pool data
    for key in redis_client.keys("pool:*"):
        pool_hash = redis_client.hgetall(key)
        if pool_hash:
            tokens.add(pool_hash["token0"])
            tokens.add(pool_hash["token1"])
    
    return {
        "tokens": [
            {
                "symbol": token,
                "name": token,
                "decimals": 18
            }
            for token in sorted(tokens)
        ]
    }


@app.get("/pools")
async def get_pools():
    """Get list of available pools"""
    pools = []
    
    for key in redis_client.keys("pool:*"):
        pool_id = key.split(":")[1]
        pool_hash = redis_client.hgetall(key)
        if pool_hash:
            pools.append({
                "pool_id": pool_id,
                "token0": pool_hash["token0"],
                "token1": pool_hash["token1"],
                "bin_step": float(pool_hash["bin_step"]),
                "active_bin": int(pool_hash["active_bin"]),
                "active": pool_hash["active"].lower() == "true",
                "x_protocol_fee": int(pool_hash["x_protocol_fee"]),
                "x_provider_fee": int(pool_hash["x_provider_fee"]),
                "x_variable_fee": int(pool_hash["x_variable_fee"]),
                "y_protocol_fee": int(pool_hash["y_protocol_fee"]),
                "y_provider_fee": int(pool_hash["y_provider_fee"]),
                "y_variable_fee": int(pool_hash["y_variable_fee"])
            })
    
    return {"pools": pools}


@app.get("/pools/{pool_id}")
async def get_pool_info(pool_id: str):
    """Get detailed information about a specific pool"""
    pool_key = f"pool:{pool_id}"
    
    pool_hash = redis_client.hgetall(pool_key)
    if not pool_hash:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    # Get bin information
    bins = []
    for key in redis_client.keys(f"bin:{pool_id}:*"):
        bin_id = int(key.split(":")[-1])
        bin_hash = redis_client.hgetall(key)
        if bin_hash:
            # Only show bins with nonzero liquidity
            reserve_x = int(bin_hash["reserve_x"])
            reserve_y = int(bin_hash["reserve_y"])
            if reserve_x > 0 or reserve_y > 0:
                # Get bin price from ZSET
                zset_key = f"pool:{pool_id}:bins"
                bin_price = redis_client.zscore(zset_key, str(bin_id))
                if bin_price is None:
                    bin_price = 0.0  # Fallback
                
                bins.append({
                    "bin_id": bin_id,
                    "reserve_x": reserve_x,
                    "reserve_y": reserve_y,
                    "liquidity": int(bin_hash["liquidity"]),
                    "price": float(bin_price),
                    "is_active": bin_id == int(pool_hash["active_bin"])
                })
    
    return {
        "pool_id": pool_id,
        "token0": pool_hash["token0"],
        "token1": pool_hash["token1"],
        "bin_step": float(pool_hash["bin_step"]),
        "active_bin": int(pool_hash["active_bin"]),
        "active": pool_hash["active"].lower() == "true",
        "x_protocol_fee": int(pool_hash["x_protocol_fee"]),
        "x_provider_fee": int(pool_hash["x_provider_fee"]),
        "x_variable_fee": int(pool_hash["x_variable_fee"]),
        "y_protocol_fee": int(pool_hash["y_protocol_fee"]),
        "y_provider_fee": int(pool_hash["y_provider_fee"]),
        "y_variable_fee": int(pool_hash["y_variable_fee"]),
        "bins": bins
    }


@app.get("/pairs")
async def get_pairs():
    """Get available trading pairs"""
    pairs = []
    
    # Get pairs from token graph
    token_graph = redis_client.hgetall("token_graph:1")
    if token_graph:
        for pair, pools_json in token_graph.items():
            import json
            pool_list = json.loads(pools_json)
            pairs.append({
                "pair": pair,
                "pools": pool_list,
                "last_updated": "2024-01-01T00:00:00Z"
            })
    
    return {"pairs": pairs}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


if __name__ == "__main__":
    print("🚀 Starting DLMM Quote Engine API Server...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔗 Frontend Test: http://localhost:8000/frontend_test.html")
    print("💡 Example API call: curl -X POST http://localhost:8000/quote \\")
    print("   -H 'Content-Type: application/json' \\")
    print("   -d '{\"token_in\": \"BTC\", \"token_out\": \"USDC\", \"amount_in\": 1.0}'")
    
    uvicorn.run(app, host="0.0.0.0", port=8000) 