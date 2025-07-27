# DLMM Quote Engine

A high-performance quote engine for Distributed Liquidity Market Maker (DLMM) pools, built with FastAPI and Redis.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- Virtual environment (recommended)

### Local Setup

1. **Navigate to the quote engine directory:**
   ```bash
   cd quote-engine
   ```

2. **Activate the virtual environment:**
   ```bash
   source ../.venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Redis (if not already running):**
   ```bash
   # Using Docker (recommended)
   docker run -d -p 6379:6379 redis:7-alpine
   
   # Or using Homebrew on macOS
   brew services start redis
   ```

5. **Populate test data:**
   ```bash
   python infrastructure/scripts/populate_test_data.py
   ```

6. **Start the quote engine:**
   ```bash
   python main.py
   ```

7. **Access the API documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## 📋 API Endpoints

### Core Endpoints

#### `POST /api/v1/quote`
Get a quote for swapping tokens.

**Request:**
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
  "execution_path": [...],
  "fee": "100000",
  "price_impact_bps": 0
}
```

#### `GET /api/v1/health`
Check system health and Redis connection.

#### `GET /api/v1/pools`
List all available pools.

#### `GET /api/v1/tokens`
List all supported tokens.

## 🏗️ Architecture

### Core Components

1. **Graph-based Routing** (`src/core/graph.py`)
   - NetworkX-based token graph
   - Path enumeration for multi-hop routes
   - Support for multiple pools per token pair

2. **Quote Computation** (`src/core/quote.py`)
   - DLMM bin traversal logic
   - Fee calculation and application
   - Execution path generation for router contracts

3. **Data Management** (`src/core/data.py`)
   - Batch Redis operations
   - Pre-fetching shared data
   - Efficient bin reserve loading

4. **Redis Integration** (`src/redis/`)
   - Pool and bin data schemas
   - Client wrapper for Redis operations
   - Health monitoring

### Key Features

- ✅ **Multi-hop Routing**: Support for complex token paths (e.g., BTC→USDC→SOL)
- ✅ **Multiple Pools**: Automatic selection of best pool per token pair
- ✅ **Fee Calculation**: Directional fees with protocol, provider, and variable components
- ✅ **DLMM Mechanics**: Correct bin traversal based on smart contract design
- ✅ **Router Integration**: Execution paths for on-chain router contracts
- ✅ **Decimal Precision**: High-precision financial calculations
- ✅ **Batch Operations**: Efficient Redis data loading

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the quote-engine directory:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Environment
ENVIRONMENT=local
```

### Pool Configuration

Pools are configured in `infrastructure/scripts/populate_test_data.py`:

```python
pool_configs = [
    {
        "pool_id": "BTC-USDC-25",
        "active_bin": 500,
        "base_price": 100000.0,  # $100,000 per BTC
        "bin_step": 0.0025,     # 25 bps bin step
        "base_reserve_x": 1000 * 100000000,  # 1000 BTC
        "base_reserve_y": 100000000 * 1000000  # 100M USDC
    }
]
```

## 📊 Supported Tokens

### Current Tokens
- **BTC** (Bitcoin) - 8 decimal places
- **ETH** (Ethereum) - 18 decimal places  
- **SOL** (Solana) - 9 decimal places
- **USDC** (USD Coin) - 6 decimal places

### Pool Types
- **BTC-USDC-25**: 25 bps bin step
- **BTC-USDC-50**: 50 bps bin step
- **ETH-USDC-25**: 25 bps bin step
- **SOL-USDC-25**: 25 bps bin step

## 🔍 DLMM Mechanics

### Bin Traversal Logic

The quote engine implements correct DLMM bin traversal:

- **X tokens** are on the **RIGHT** (higher bin numbers, higher prices)
- **Y tokens** are on the **LEFT** (lower bin numbers, lower prices)

**Swap Directions:**
- **X→Y swaps**: Traverse LEFT to find Y tokens
- **Y→X swaps**: Traverse RIGHT to find X tokens

### Fee Structure

Each pool has directional fees:
- **Protocol fee**: 2 bps (0.02%)
- **Provider fee**: 3 bps (0.03%)
- **Variable fee**: 5 bps (0.05%)
- **Total**: 10 bps (0.1%)

Fees are applied upfront based on swap direction.

## 🧪 Testing

### Manual Testing

Test the API endpoints:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get quote
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{"input_token": "BTC", "output_token": "USDC", "amount_in": "100000000"}'

# List pools
curl http://localhost:8000/api/v1/pools
```

### Example Quotes

**Small BTC→USDC swap (1 BTC):**
```bash
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{"input_token": "BTC", "output_token": "USDC", "amount_in": "100000000"}'
```

**Large BTC→USDC swap (500 BTC):**
```bash
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{"input_token": "BTC", "output_token": "USDC", "amount_in": "500000000000"}'
```

**Cross-token swap (BTC→SOL):**
```bash
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{"input_token": "BTC", "output_token": "SOL", "amount_in": "100000000"}'
```

## 🚨 Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check if Redis is running
   redis-cli ping
   
   # Start Redis if needed
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Missing Dependencies**
   ```bash
   # Install missing packages
   pip install networkx redis fastapi uvicorn
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Kill the process or change port in .env
   ```

4. **No Test Data**
   ```bash
   # Repopulate test data
   python infrastructure/scripts/populate_test_data.py
   ```

### Logs

Check the server logs for detailed error information:
```bash
python main.py
```

## 📈 Performance

### Optimizations

- **Batch Redis Operations**: All bin reserves loaded in single pipeline
- **Pre-fetching**: Shared data loaded upfront
- **Sequential Traversal**: No repeated Redis calls during bin traversal
- **Decimal Precision**: High-precision calculations without floating-point errors

### Benchmarks

- **Quote Response Time**: ~2-5ms
- **Multi-hop Support**: Up to 3 hops (e.g., BTC→USDC→SOL)
- **Pool Selection**: Automatic best pool selection
- **Memory Efficiency**: Minimal memory footprint

## 🔗 Integration

### Router Contract Integration

The quote engine generates execution paths for on-chain router contracts:

```json
{
  "execution_path": [
    {
      "pool_trait": "dlmm-pool-btc-usdc-v-1-1",
      "x_token_trait": "sbtc-trait",
      "y_token_trait": "usdc-trait", 
      "bin_id": 500,
      "function_name": "swap-x-for-y",
      "x_amount": "100000000"
    }
  ]
}
```

### Trait Mappings

Hardcoded trait mappings in `src/utils/traits.py`:
- Pool traits for on-chain identification
- Token traits for contract integration
- Function names for swap directions

## 📝 Development

### Project Structure

```
quote-engine/
├── src/
│   ├── core/           # Core quote logic
│   ├── api/            # FastAPI endpoints
│   ├── redis/          # Redis integration
│   └── utils/          # Utilities and traits
├── infrastructure/     # Redis setup and scripts
├── docs/              # Documentation
├── main.py            # Application entry point
└── requirements.txt   # Dependencies
```

### Adding New Tokens

1. Update `src/utils/traits.py` with new token traits
2. Add pool configuration in `infrastructure/scripts/populate_test_data.py`
3. Update token graph with new pools
4. Test with API endpoints

### Adding New Pools

1. Add pool configuration to `pool_configs` in populate script
2. Update token graph with new pool mappings
3. Run populate script to add data to Redis
4. Test pool selection logic

## 📄 License

This project is part of the Bitflow DLMM system.

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure Redis schema compatibility
5. Test with multiple token pairs 