"""
Pydantic models for the quote engine API.
Defines request and response models for the FastAPI application.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from decimal import Decimal


class QuoteRequest(BaseModel):
    """Quote request model"""
    input_token: str = Field(..., description="Input token symbol")
    output_token: str = Field(..., description="Output token symbol")
    amount_in: str = Field(..., description="Input amount as string (large integer in atomic units)")


class ExecutionStep(BaseModel):
    """Execution step for router contract"""
    pool_trait: str = Field(..., description="Pool trait identifier")
    x_token_trait: str = Field(..., description="X token trait identifier")
    y_token_trait: str = Field(..., description="Y token trait identifier")
    bin_id: int = Field(..., description="Bin identifier")
    function_name: str = Field(..., description="Function name (swap-x-for-y or swap-y-for-x)")
    x_amount: Optional[str] = Field(None, description="X amount (if X->Y swap)")
    y_amount: Optional[str] = Field(None, description="Y amount (if Y->X swap)")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionStep':
        """Create ExecutionStep from dictionary, converting Decimal to string"""
        # Convert Decimal values to strings
        if 'x_amount' in data and data['x_amount'] is not None:
            data['x_amount'] = str(data['x_amount'])
        if 'y_amount' in data and data['y_amount'] is not None:
            data['y_amount'] = str(data['y_amount'])
        
        return cls(**data)


class QuoteResponse(BaseModel):
    """Quote response model"""
    success: bool = Field(..., description="Whether the quote was successful")
    amount_out: str = Field(..., description="Output amount as string")
    route_path: List[str] = Field(..., description="List of tokens in the route")
    execution_path: List[ExecutionStep] = Field(..., description="Flattened execution steps for router")
    fee: str = Field(..., description="Total fee as string")
    price_impact_bps: int = Field(..., description="Price impact in basis points")
    error: Optional[str] = Field(None, description="Error message if quote failed")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    redis_connected: bool = Field(..., description="Redis connection status")
    redis_info: Dict[str, Any] = Field(..., description="Redis connection information")
    version: str = Field(..., description="API version")


class TokenInfo(BaseModel):
    """Token information model"""
    symbol: str = Field(..., description="Token symbol")
    trait: str = Field(..., description="Token trait identifier")
    supported: bool = Field(..., description="Whether token is supported")


class PoolInfo(BaseModel):
    """Pool information model"""
    pool_id: str = Field(..., description="Pool identifier")
    token0: str = Field(..., description="Token 0 symbol")
    token1: str = Field(..., description="Token 1 symbol")
    bin_step: float = Field(..., description="Bin step in basis points")
    active_bin: int = Field(..., description="Currently active bin ID")
    active: bool = Field(..., description="Whether pool is active")
    x_protocol_fee: int = Field(..., description="Protocol fee for X→Y swaps (basis points)")
    x_provider_fee: int = Field(..., description="Provider fee for X→Y swaps (basis points)")
    x_variable_fee: int = Field(..., description="Variable fee for X→Y swaps (basis points)")
    y_protocol_fee: int = Field(..., description="Protocol fee for Y→X swaps (basis points)")
    y_provider_fee: int = Field(..., description="Provider fee for Y→X swaps (basis points)")
    y_variable_fee: int = Field(..., description="Variable fee for Y→X swaps (basis points)")


class TokensResponse(BaseModel):
    """Tokens response model"""
    tokens: List[TokenInfo] = Field(..., description="List of supported tokens")


class PoolsResponse(BaseModel):
    """Pools response model"""
    pools: List[PoolInfo] = Field(..., description="List of available pools")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information") 