# DLMM Quote Engine API Documentation

## Overview

The DLMM Quote Engine provides a REST API for getting quotes on token swaps across Distributed Liquidity Market Maker pools. The API supports both direct token pairs and multi-hop routes through intermediate tokens.

**Base URL**: `http://localhost:8000`

**API Version**: `v1`

## Authentication

Currently, no authentication is required for the API endpoints.

## Endpoints

### 1. Health Check

#### `GET /api/v1/health`

Check the health status of the quote engine and Redis connection.

**Response:**
```json
{
  "status": "healthy",
  "redis_connected": true,
  "redis_info": {
    "connected": true,
    "environment": "local",
    "redis_version": "7.0.0",
    "used_memory_human": "2.5M",
    "connected_clients": 1
  },
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service is unhealthy

### 2. Get Quote

#### `POST /api/v1/quote`

Get a quote for swapping tokens. Supports both direct and multi-hop routes.

**Request Body:**
```json
{
  "input_token": "BTC",
  "output_token": "USDC",
  "amount_in": "100000000"
}
```

**Parameters:**
- `input_token` (string, required): Input token symbol (e.g., "BTC", "ETH", "SOL", "USDC")
- `output_token` (string, required): Output token symbol
- `amount_in` (string, required): Input amount in atomic units (e.g., "100000000" for 1 BTC)

**Response (Success):**
```json
{
  "success": true,
  "amount_out": "9990000000000",
  "route_path": ["BTC", "USDC"],
  "execution_path": [
    {
      "pool_trait": "dlmm-pool-btc-usdc-v-1-1",
      "x_token_trait": "sbtc-trait",
      "y_token_trait": "usdc-trait",
      "bin_id": 500,
      "function_name": "swap-x-for-y",
      "x_amount": "100000000"
    }
  ],
  "fee": "100000",
  "price_impact_bps": 0
}
```

**Response (Error):**
```json
{
  "success": false,
  "amount_out": "0",
  "route_path": [],
  "execution_path": [],
  "fee": "0",
  "error": "No viable route found"
}
```

**Response Fields:**
- `success` (boolean): Whether the quote was successful
- `amount_out` (string): Output amount in atomic units
- `route_path` (array): List of tokens in the route (e.g., ["BTC", "USDC", "SOL"])
- `execution_path` (array): Detailed execution steps for router contracts
- `fee` (string): Total fee amount in atomic units
- `price_impact_bps` (integer): Price impact in basis points (currently 0)
- `error` (string, optional): Error message if quote failed

**Status Codes:**
- `200 OK`: Quote generated successfully
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: Server error

### 3. List Pools

#### `GET /api/v1/pools`

Get a list of all available pools and their metadata.

**Response:**
```json
{
  "pools": [
    {
      "pool_id": "BTC-USDC-25",
      "token0": "BTC",
      "token1": "USDC",
      "active_bin": 500,
      "x_protocol_fee": 2,
      "x_provider_fee": 3,
      "x_variable_fee": 5,
      "y_protocol_fee": 2,
      "y_provider_fee": 3,
      "y_variable_fee": 5
    },
    {
      "pool_id": "BTC-USDC-50",
      "token0": "BTC",
      "token1": "USDC",
      "active_bin": 500,
      "x_protocol_fee": 2,
      "x_provider_fee": 3,
      "x_variable_fee": 5,
      "y_protocol_fee": 2,
      "y_provider_fee": 3,
      "y_variable_fee": 5
    }
  ]
}
```

**Pool Fields:**
- `pool_id` (string): Unique pool identifier
- `token0` (string): First token in the pair
- `token1` (string): Second token in the pair
- `active_bin` (integer): Current active bin ID
- `x_protocol_fee` (integer): Protocol fee for X→Y swaps (basis points)
- `x_provider_fee` (integer): Provider fee for X→Y swaps (basis points)
- `x_variable_fee` (integer): Variable fee for X→Y swaps (basis points)
- `y_protocol_fee` (integer): Protocol fee for Y→X swaps (basis points)
- `y_provider_fee` (integer): Provider fee for Y→X swaps (basis points)
- `y_variable_fee` (integer): Variable fee for Y→X swaps (basis points)

### 4. List Tokens

#### `GET /api/v1/tokens`

Get a list of all supported tokens and their traits.

**Response:**
```json
{
  "tokens": [
    {
      "symbol": "BTC",
      "trait": "sbtc-trait",
      "supported": true
    },
    {
      "symbol": "ETH",
      "trait": "seth-trait",
      "supported": true
    },
    {
      "symbol": "SOL",
      "trait": "sol-trait",
      "supported": true
    },
    {
      "symbol": "USDC",
      "trait": "usdc-trait",
      "supported": true
    }
  ]
}
```

**Token Fields:**
- `symbol` (string): Token symbol
- `trait` (string): On-chain trait identifier
- `supported` (boolean): Whether the token is supported

## Request Examples

### Direct Token Swap

**BTC to USDC:**
```bash
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{
    "input_token": "BTC",
    "output_token": "USDC",
    "amount_in": "100000000"
  }'
```

**ETH to USDC:**
```bash
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{
    "input_token": "ETH",
    "output_token": "USDC",
    "amount_in": "1000000000000000000"
  }'
```

### Multi-hop Token Swap

**BTC to SOL (via USDC):**
```bash
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{
    "input_token": "BTC",
    "output_token": "SOL",
    "amount_in": "100000000"
  }'
```

**SOL to BTC (via USDC):**
```bash
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{
    "input_token": "SOL",
    "output_token": "BTC",
    "amount_in": "1000000000000"
  }'
```

## Response Examples

### Small Swap (Single Bin)

**Request:** 1 BTC → USDC
```json
{
  "input_token": "BTC",
  "output_token": "USDC",
  "amount_in": "100000000"
}
```

**Response:**
```json
{
  "success": true,
  "amount_out": "9990000000000",
  "route_path": ["BTC", "USDC"],
  "execution_path": [
    {
      "pool_trait": "dlmm-pool-btc-usdc-v-1-1",
      "x_token_trait": "sbtc-trait",
      "y_token_trait": "usdc-trait",
      "bin_id": 500,
      "function_name": "swap-x-for-y",
      "x_amount": "100000000"
    }
  ],
  "fee": "100000",
  "price_impact_bps": 0
}
```

### Large Swap (Multiple Bins)

**Request:** 500 BTC → USDC
```json
{
  "input_token": "BTC",
  "output_token": "USDC",
  "amount_in": "500000000000"
}
```

**Response:**
```json
{
  "success": true,
  "amount_out": "49691970424794740",
  "route_path": ["BTC", "USDC"],
  "execution_path": [
    {
      "pool_trait": "dlmm-pool-btc-usdc-v-1-1",
      "x_token_trait": "sbtc-trait",
      "y_token_trait": "usdc-trait",
      "bin_id": 500,
      "function_name": "swap-x-for-y",
      "x_amount": "100000000000"
    },
    {
      "pool_trait": "dlmm-pool-btc-usdc-v-1-1",
      "x_token_trait": "sbtc-trait",
      "y_token_trait": "usdc-trait",
      "bin_id": 499,
      "function_name": "swap-x-for-y",
      "x_amount": "100000000000"
    }
  ],
  "fee": "500000000000",
  "price_impact_bps": 0
}
```

### Multi-hop Swap

**Request:** BTC → SOL
```json
{
  "input_token": "BTC",
  "output_token": "SOL",
  "amount_in": "100000000"
}
```

**Response:**
```json
{
  "success": true,
  "amount_out": "49900050000",
  "route_path": ["BTC", "USDC", "SOL"],
  "execution_path": [
    {
      "pool_trait": "dlmm-pool-btc-usdc-v-1-1",
      "x_token_trait": "sbtc-trait",
      "y_token_trait": "usdc-trait",
      "bin_id": 500,
      "function_name": "swap-x-for-y",
      "x_amount": "100000000"
    },
    {
      "pool_trait": "dlmm-pool-sol-usdc-v-1-1",
      "x_token_trait": "usdc-trait",
      "y_token_trait": "sol-trait",
      "bin_id": 500,
      "function_name": "swap-x-for-y",
      "x_amount": "9990000000000"
    }
  ],
  "fee": "9990100000",
  "price_impact_bps": 0
}
```

## Error Handling

### Common Error Responses

**Invalid Token:**
```json
{
  "success": false,
  "amount_out": "0",
  "route_path": [],
  "execution_path": [],
  "fee": "0",
  "error": "Token 'INVALID' not supported"
}
```

**No Route Found:**
```json
{
  "success": false,
  "amount_out": "0",
  "route_path": [],
  "execution_path": [],
  "fee": "0",
  "error": "No viable route found"
}
```

**Invalid Amount:**
```json
{
  "success": false,
  "amount_out": "0",
  "route_path": [],
  "execution_path": [],
  "fee": "0",
  "error": "Invalid amount_in: must be positive"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production use.

## CORS

CORS is enabled for all origins. Configure CORS settings in production for security.

## WebSocket Support

WebSocket support is not currently implemented. Consider adding WebSocket endpoints for real-time quote updates.

## SDK Examples

### Python

```python
import requests

def get_quote(input_token, output_token, amount_in):
    url = "http://localhost:8000/api/v1/quote"
    data = {
        "input_token": input_token,
        "output_token": output_token,
        "amount_in": str(amount_in)
    }
    response = requests.post(url, json=data)
    return response.json()

# Example usage
quote = get_quote("BTC", "USDC", 100000000)
print(f"Amount out: {quote['amount_out']}")
print(f"Fee: {quote['fee']}")
```

### JavaScript

```javascript
async function getQuote(inputToken, outputToken, amountIn) {
    const response = await fetch('http://localhost:8000/api/v1/quote', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            input_token: inputToken,
            output_token: outputToken,
            amount_in: amountIn.toString()
        })
    });
    return await response.json();
}

// Example usage
getQuote('BTC', 'USDC', '100000000')
    .then(quote => {
        console.log(`Amount out: ${quote.amount_out}`);
        console.log(`Fee: ${quote.fee}`);
    });
```

## Versioning

The API uses URL versioning (`/api/v1/`). Future versions will be available at `/api/v2/`, etc.

## Deprecation Policy

- Deprecated endpoints will be marked with a deprecation header
- Deprecated endpoints will be supported for at least 6 months
- Migration guides will be provided for breaking changes 