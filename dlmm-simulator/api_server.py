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

from src.quote_engine import MockRedisClient, QuoteEngine, RouteType


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
    token_x: str
    token_y: str
    bin_step: int
    active_bin_id: int
    active_bin_price: float
    total_tvl: float
    status: str


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

# Initialize quote engine
redis_client = MockRedisClient()
quote_engine = QuoteEngine(redis_client)

# Print the actual in-memory bin data for the active bin of BTC-USDC-25
active_bin_key = f"bin:BTC-USDC-25:500"
if active_bin_key in redis_client.data:
    print("DEBUG: In-memory active bin data for BTC-USDC-25:")
    print(redis_client.data[active_bin_key])


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
            effective_price=quote.amount_out / quote.amount_in if quote.amount_in > 0 else 0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote calculation failed: {str(e)}")


@app.get("/tokens")
async def get_tokens():
    """Get list of available tokens"""
    tokens = set()
    
    # Extract tokens from pool data
    for key in redis_client.keys("pool:*"):
        pool_data = redis_client.data[key]
        tokens.add(pool_data["token_x"])
        tokens.add(pool_data["token_y"])
    
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
        pool_data = redis_client.data[key]
        
        pools.append({
            "pool_id": pool_id,
            "token_x": pool_data["token_x"],
            "token_y": pool_data["token_y"],
            "bin_step": pool_data["bin_step"],
            "active_bin_id": pool_data["active_bin_id"],
            "active_bin_price": float(pool_data["active_bin_price"]),  # Already a float
            "total_tvl": float(pool_data["total_tvl"]),  # Already a float
            "status": pool_data["status"]
        })
    
    return {"pools": pools}


@app.get("/pools/{pool_id}")
async def get_pool_info(pool_id: str):
    """Get detailed information about a specific pool"""
    pool_key = f"pool:{pool_id}"
    
    if pool_key not in redis_client.data:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    pool_data = redis_client.data[pool_key]
    
    # Get bin information
    bins = []
    for key in redis_client.keys(f"bin:{pool_id}:*"):
        bin_id = int(key.split(":")[-1])
        bin_data = redis_client.data[key]
        # Only show bins with nonzero liquidity
        if float(bin_data["x_amount"]) > 0 or float(bin_data["y_amount"]) > 0:
            # Debug: Print raw bin data
            print(f"DEBUG: Raw bin data for {key}:")
            print(f"  x_amount: {bin_data['x_amount']}")
            print(f"  y_amount: {bin_data['y_amount']}")
            print(f"  price: {bin_data['price']}")
            print(f"  is_active: {bin_data['is_active']}")
            
            bins.append({
                "bin_id": bin_id,
                "x_amount": float(bin_data["x_amount"]),  # Already a float
                "y_amount": float(bin_data["y_amount"]),  # Already a float
                "price": float(bin_data["price"]),  # Already a float
                "is_active": bin_data["is_active"]
            })
    
    return {
        "pool_id": pool_id,
        "token_x": pool_data["token_x"],
        "token_y": pool_data["token_y"],
        "bin_step": pool_data["bin_step"],
        "active_bin_id": pool_data["active_bin_id"],
        "active_bin_price": float(pool_data["active_bin_price"]),  # Already a float
        "total_tvl": float(pool_data["total_tvl"]),  # Already a float
        "status": pool_data["status"],
        "bins": bins
    }


@app.get("/pairs")
async def get_pairs():
    """Get available trading pairs"""
    pairs = []
    
    for key in redis_client.keys("pairs:*"):
        tokens = key.split(":")[1:]
        if len(tokens) == 2:
            pair_data = redis_client.data[key]
            pairs.append({
                "token1": tokens[0],
                "token2": tokens[1],
                "pools": pair_data["pools"],
                "best_pool": pair_data["best_pool"]
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