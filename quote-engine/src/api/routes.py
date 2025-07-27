"""
FastAPI routes for the quote engine API.
Implements the main quote endpoint and supporting endpoints.
"""

import logging
from typing import List, Dict, Any
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from .models import (
    QuoteRequest, QuoteResponse, HealthResponse, TokensResponse, 
    PoolsResponse, TokenInfo, PoolInfo, ExecutionStep
)
from ..core.graph import build_token_graph, enumerate_paths
from ..core.data import pre_fetch_shared_data
from ..core.quote import find_best_route
from ..redis.client import RedisClient
from ..utils.config import Config
from ..utils.traits import TraitMappings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def get_redis_client() -> RedisClient:
    """Dependency to get Redis client"""
    try:
        return RedisClient(environment="local")  # TODO: Make configurable
    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        raise HTTPException(status_code=500, detail="Redis connection failed")


@router.post("/quote", response_model=QuoteResponse)
async def get_quote(request: QuoteRequest, redis_client: RedisClient = Depends(get_redis_client)):
    """
    Get quote for token swap.
    
    This endpoint follows Grok's design:
    1. Build token graph from Redis
    2. Enumerate paths up to max_hops
    3. Pre-fetch shared data
    4. Find best route
    5. Return execution path for router
    """
    try:
        # Parse input amount
        try:
            amount_in = Decimal(request.amount_in)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid amount_in: {e}")
        
        # Validate tokens
        if not TraitMappings.validate_token(request.input_token):
            raise HTTPException(status_code=400, detail=f"Unsupported input token: {request.input_token}")
        
        if not TraitMappings.validate_token(request.output_token):
            raise HTTPException(status_code=400, detail=f"Unsupported output token: {request.output_token}")
        
        if request.input_token == request.output_token:
            raise HTTPException(status_code=400, detail="Input and output tokens must be different")
        
        logger.info(f"Processing quote: {request.input_token} -> {request.output_token}, amount: {amount_in}")
        
        # Step 1: Build token graph
        graph = build_token_graph(redis_client)
        if not graph.nodes:
            raise HTTPException(status_code=503, detail="No token graph data available")
        
        # Step 2: Enumerate paths
        app_config = Config.get_app_config()
        paths = enumerate_paths(graph, request.input_token, request.output_token, app_config.max_hops)
        
        if not paths:
            return QuoteResponse(
                success=False,
                amount_out="0",
                route_path=[],
                execution_path=[],
                fee="0",
                price_impact_bps=0,
                error="No routes found between tokens"
            )
        
        # Step 3: Pre-fetch shared data
        shared_data = pre_fetch_shared_data(redis_client, paths, graph)
        if not shared_data:
            raise HTTPException(status_code=503, detail="Failed to fetch pool data")
        
        # Step 4: Find best route
        route_result = find_best_route(paths, amount_in, redis_client, shared_data, graph)
        
        if not route_result['success']:
            return QuoteResponse(
                success=False,
                amount_out="0",
                route_path=[],
                execution_path=[],
                fee="0",
                price_impact_bps=0,
                error=route_result.get('error', 'No viable route found')
            )
        
        # Step 5: Convert execution path to Pydantic models
        execution_steps = []
        for step in route_result['execution_path']:
            execution_step = ExecutionStep.from_dict(step)
            execution_steps.append(execution_step)
        
        # Calculate fee and price impact from route result
        fee = route_result.get('total_fee', '0')
        price_impact_bps = 0  # TODO: Calculate actual price impact
        
        return QuoteResponse(
            success=True,
            amount_out=route_result['amount_out'],
            route_path=route_result['route_path'],
            execution_path=execution_steps,
            fee=fee,
            price_impact_bps=price_impact_bps
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing quote: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check(redis_client: RedisClient = Depends(get_redis_client)):
    """Health check endpoint"""
    try:
        redis_info = redis_client.health_check()
        
        return HealthResponse(
            status="healthy" if redis_info['connected'] else "unhealthy",
            redis_connected=redis_info['connected'],
            redis_info=redis_info,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            redis_connected=False,
            redis_info={"error": str(e)},
            version="1.0.0"
        )


@router.get("/tokens", response_model=TokensResponse)
async def get_tokens():
    """Get list of supported tokens"""
    try:
        tokens = []
        for symbol in TraitMappings.get_all_supported_tokens():
            token_info = TokenInfo(
                symbol=symbol,
                trait=TraitMappings.get_token_trait(symbol),
                supported=True
            )
            tokens.append(token_info)
        
        return TokensResponse(tokens=tokens)
    except Exception as e:
        logger.error(f"Error getting tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/pools", response_model=PoolsResponse)
async def get_pools(redis_client: RedisClient = Depends(get_redis_client)):
    """Get list of available pools"""
    try:
        pools = []
        pool_ids = redis_client.get_all_pool_ids()
        
        for pool_id in pool_ids:
            pool_data = redis_client.get_pool_data(pool_id)
            if pool_data:
                pool_info = PoolInfo(
                    pool_id=pool_data.pool_id,
                    token0=pool_data.token0,
                    token1=pool_data.token1,
                    bin_step=pool_data.bin_step,
                    active_bin=pool_data.active_bin,
                    active=pool_data.active,
                    x_protocol_fee=pool_data.x_protocol_fee,
                    x_provider_fee=pool_data.x_provider_fee,
                    x_variable_fee=pool_data.x_variable_fee,
                    y_protocol_fee=pool_data.y_protocol_fee,
                    y_provider_fee=pool_data.y_provider_fee,
                    y_variable_fee=pool_data.y_variable_fee
                )
                pools.append(pool_info)
        
        return PoolsResponse(pools=pools)
    except Exception as e:
        logger.error(f"Error getting pools: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "DLMM Quote Engine API",
        "version": "1.0.0",
        "description": "Quote engine following Grok's modular design",
        "endpoints": {
            "POST /quote": "Get quote for token swap",
            "GET /tokens": "Get supported tokens",
            "GET /pools": "Get available pools",
            "GET /health": "Health check"
        }
    } 