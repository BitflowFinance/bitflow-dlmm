# DLMM Quote Engine - Agent Onboarding

## Project Overview

**Project Name**: Bitflow DLMM (Distributed Liquidity Market Maker) Quote Engine  
**Repository**: `/Users/dylanfloyd/Documents/Bitflow/git/bitflow-dlmm`  
**Type**: DeFi Liquidity Pool Simulator with Quote Engine  
**Status**: Production Ready (with MockRedisClient fallback)  
**Version**: 2.0 (Optimized)

## 🚨 CRITICAL RULE - NEVER BREAK

**⚠️ THE NUMBER ONE RULE ABOVE ALL ELSE THAT CAN NEVER BE BROKEN:**
**Files inside of the "clarity" folder can NEVER be changed.**

This rule is absolute and non-negotiable. The Clarity smart contracts are production-ready blockchain code and must remain untouched.

## 🎯 Core Purpose

This is a **high-performance Python-based Distributed Liquidity Market Maker (DLMM) Quote Engine** that simulates DeFi liquidity pools with:
- **Dynamic pricing** based on bin-based liquidity distribution
- **Multi-hop routing** through complex liquidity networks
- **Real-time quote calculations** with detailed step breakdowns
- **Graph-based pathfinding** for optimal swap routes
- **Redis integration** for data management (with fallback)
- **Complete web interface** for testing and visualization

## 🏗️ Architecture Overview

### Dual Implementation
The project contains **two implementations**:

1. **Python Simulator** (`dlmm-simulator/`) - For testing, development, and API services
2. **Clarity Smart Contracts** (`clarity/`) - For blockchain deployment on Stacks

### Key Components

#### Python Simulator
```
dlmm-simulator/
├── src/
│   ├── quote_engine.py          # Main optimized quote engine
│   ├── quote_engine_legacy.py   # Original implementation
│   ├── pool.py                  # Pool and bin data structures
│   ├── routing.py               # Single pool router
│   ├── math.py                  # DLMM mathematical functions
│   └── redis/                   # Redis integration
├── api_server.py                # FastAPI REST API
├── app.py                       # Streamlit web interface
└── docs/                        # Comprehensive documentation
```

#### Clarity Smart Contracts
```
clarity/contracts/
├── dlmm-core-v-1-1.clar         # Main core contract
├── dlmm-pool-trait-v-1-1.clar   # Pool interface
├── dlmm-pool-sbtc-usdc-v-1-1.clar # Example pool implementation
└── dlmm-router-v-1-1.clar       # Router for complex swaps
```

## 🔧 Technical Implementation

### Core Design Principles

#### 1. **Simple Float Arithmetic**
- **No 1e18 scaling** - All calculations use human-readable floats
- **Direct price representation** - $50,000 instead of 50000000000000000000000
- **Easy debugging** - Clear, readable values throughout
- **Consistent math** - DLMMMath module handles all calculations

#### 2. **Realistic Market Data**
- **BTC price**: ~$50,000 USDC
- **ETH price**: ~$3,000 USDC  
- **SOL price**: ~$150 USDC
- **Bin steps**: 25, 50, 100 basis points
- **Fee structure**: 10 basis points (0.1%)

#### 3. **Performance Optimizations**
- **48.4% latency reduction** compared to legacy implementation
- **1.94x speedup** for quote calculations
- **1.7x improvement** with caching enabled
- **Graph-based pathfinding** with pre-computed routes

### Mathematical Foundation

#### DLMM Variables
- $N$ - Number of bins in the pool
- $P_i$ - Price of the $i$-th bin: $P_i = P_0 \times (1 + s)^i$
- $s$ - Bin step (distance between bins, measured in bps)
- $x_i, y_i$ - Amounts of tokens X and Y in bin $i$
- $L_i$ - Liquidity in bin $i$: $L_i = x_i + \frac{y_i}{P_i}$

#### Swap Calculations
**Within a single bin (constant sum AMM):**
- **X → Y**: $\Delta y = \min(P_i \cdot \Delta x, y_i)$
- **Y → X**: $\Delta x = \min(\frac{\Delta y}{P_i}, x_i)$

**Across multiple bins:**
- Sum of outputs from each bin traversed
- Each bin has its own fixed price $P_j$

### Route Types Supported

| Type | Description | Status |
|------|-------------|--------|
| **Type 1** | Single pair, single pool, single bin | ✅ Complete |
| **Type 2** | Single pair, single pool, multi bin | ✅ Complete |
| **Type 3** | Single pair, multi pool, multi bin | ✅ Complete |
| **Type 4** | Multi pair, multi pool, multi bin | ✅ Complete |

## 🚀 System Components

### 1. Quote Engine (`src/quote_engine.py`)
**Core Features:**
- **Graph-based routing** with intelligent caching
- **Multi-path discovery** for optimal quotes
- **Performance optimized** with 48.4% latency reduction
- **MockRedisClient fallback** for development and testing

**Key Classes:**
- `QuoteEngine`: Main quote calculation engine
- `LiquidityGraph`: Graph-based pathfinding with caching
- `MockRedisClient`: Fallback Redis client with sample data
- `QuoteResult`: Complete quote result with steps
- `RouteType`: Enum for different route types

### 2. API Server (`api_server.py`)
**FastAPI-based REST API:**
- **Real-time quote calculations** with detailed step breakdowns
- **Health monitoring** and performance metrics
- **Comprehensive error handling**
- **CORS support** for frontend integration

**Key Endpoints:**
- `POST /quote` - Get quote for token swap
- `GET /pools` - List available pools
- `GET /pools/{pool_id}` - Get pool details
- `GET /tokens` - List supported tokens
- `GET /health` - Health check

### 3. Streamlit Frontend (`app.py`)
**Interactive web interface:**
- **Real-time visualization** of pool states
- **Multi-token support** (BTC, ETH, USDC, SOL)
- **Route visualization** with step-by-step breakdowns
- **TVL histograms** and price impact analysis

### 4. Redis Integration (`src/redis/`)
**Data management with fallback:**
- **Real Redis client** for production
- **MockRedisClient fallback** for development
- **Data schemas** for pool and bin data
- **Cache management** for graph paths

## 📊 Current System Status

### ✅ Working Components
- **Quote Engine**: Fully optimized with 1.7x performance improvement
- **Redis Integration**: Working with MockRedisClient fallback
- **API Server**: Running on port 8000
- **Graph Routing**: Multi-path discovery working
- **Caching**: Path and quote caching operational
- **Streamlit App**: Running on port 8501

### 🔧 Known Issues
- **Redis Connection**: SSL parameter issue (using fallback)
- **Streamlit Port Conflicts**: Sometimes port 8501 conflicts
- **Import Issues**: Some relative imports in Redis integration

### 📈 Performance Metrics
- **Quote Response Time**: ~4.5ms (first), ~2.6ms (cached)
- **Supported Pools**: 3 (BTC-USDC-25, BTC-USDC-50, SOL-USDC-25)
- **Route Types**: Single-bin, Multi-bin, Multi-pool
- **Cache Hit Rate**: ~60% for repeated requests

## 🛠️ Development Environment

### Prerequisites
- **Python 3.8+** (3.8, 3.9, 3.10, or 3.11 recommended)
- **Git** for cloning the repository
- **pip** for package management
- **Redis** (optional - system works with fallback)

### Setup Commands
```bash
# Navigate to project root
cd /Users/dylanfloyd/Documents/Bitflow/git/bitflow-dlmm

# Activate virtual environment
source .venv/bin/activate

# Navigate to simulator
cd dlmm-simulator

# Install dependencies
pip install -r requirements.txt

# Start Redis (optional)
brew services start redis

# Start services
python3 api_server.py &  # Port 8000
streamlit run app.py --server.port 8501  # Port 8501
```

### Key Dependencies
```
numpy>=1.24.0
matplotlib>=3.5.0
pandas>=2.0.0
streamlit>=1.28.0
plotly>=5.17.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
requests>=2.31.0
pytest>=7.0.0
```

## 🧪 Testing & Validation

### Quick Tests
```bash
# Test Redis connection
python3 -c "from src.redis import RedisConfig, create_redis_client; config = RedisConfig(); client = create_redis_client(config); print('✅ Redis connection:', client.ping())"

# Test quote engine
python3 -c "from src.quote_engine import QuoteEngine, MockRedisClient; redis_client = MockRedisClient(); engine = QuoteEngine(redis_client); quote = engine.get_quote('BTC', 'USDC', 1.0); print('✅ Quote:', quote.success, quote.amount_out)"

# Test API
curl -X POST http://localhost:8000/quote -H "Content-Type: application/json" -d '{"token_in": "BTC", "token_out": "USDC", "amount_in": 1.0}'
```

### Sample Data
The system includes realistic sample data:
- **BTC-USDC-25**: 25 bps fee, ~$50,000 BTC price, $1M TVL
- **BTC-USDC-50**: 50 bps fee, ~$50,000 BTC price, $500K TVL  
- **ETH-USDC-25**: 25 bps fee, ~$3,000 ETH price, $800K TVL
- **BTC-ETH-25**: 25 bps fee, ~16.67 ETH per BTC, $600K TVL
- **SOL-USDC-25**: 25 bps fee, ~$150 SOL price, $100K TVL

## 📚 Key Documentation

### Architecture Documents
- `dlmm-architecture.md` - Complete architecture overview
- `dlmm-math.md` - Mathematical formulas and implementation
- `dlmm-simulator/docs/AGENT.md` - Development guide
- `dlmm-simulator/docs/QUOTE_ENGINE_IMPLEMENTATION.md` - Core engine details
- `dlmm-simulator/docs/REDIS_INTEGRATION.md` - Redis setup and usage
- `dlmm-simulator/docs/PERFORMANCE_ANALYSIS.md` - Performance benchmarks

### Code Structure
- `src/quote_engine.py` - Main engine logic (627 lines)
- `src/math.py` - DLMM mathematical functions (215 lines)
- `src/pool.py` - Pool and bin data structures (203 lines)
- `src/routing.py` - Single pool router (543 lines)
- `api_server.py` - FastAPI server (335 lines)
- `app.py` - Streamlit interface (615 lines)

## 🎯 Common Tasks & Workflows

### Adding New Features
1. **Create feature branch**: `git checkout -b feature/new-feature`
2. **Implement in src/**: Follow existing patterns
3. **Add tests**: Place in `tests/` directory
4. **Update docs**: Update relevant documentation
5. **Test thoroughly**: Run all test suites

### Debugging
```bash
# Check running processes
lsof -i :8000  # API server
lsof -i :8501  # Streamlit

# Kill processes
pkill -f "streamlit run app.py"
pkill -f "api_server.py"

# Check Redis
redis-cli ping

# Monitor API
curl -s http://localhost:8000/health
```

### Performance Monitoring
- **Quote Latency**: Monitor response times
- **Cache Hit Rate**: Track cache effectiveness
- **Memory Usage**: Monitor system resources
- **Error Rates**: Track API error rates

## 🔮 Future Development

### Planned Features
1. **Real Redis Integration**: Fix SSL issues and connect to real Redis
2. **WebSocket Support**: Real-time quote updates
3. **Advanced Routing**: Multi-hop path optimization
4. **Fee Optimization**: Dynamic fee calculation
5. **Analytics Dashboard**: Performance monitoring

### Technical Debt
1. **Redis SSL Issue**: Fix connection parameters
2. **Import Structure**: Clean up relative imports
3. **Error Handling**: Improve error messages
4. **Testing Coverage**: Add more integration tests

## 🚨 Emergency Procedures

### System Down
1. **Check processes**: `lsof -i :8000 :8501`
2. **Restart services**: Kill and restart API/Streamlit
3. **Check logs**: Review `logs/` directory
4. **Fallback mode**: System works with MockRedisClient

### Data Issues
1. **Reset Redis**: Clear Redis cache if needed
2. **Reinitialize**: Run data initialization
3. **Check schemas**: Verify data structure integrity

## 📞 Success Metrics

- **Quote Success Rate**: >99%
- **Response Time**: <10ms average
- **Cache Hit Rate**: >50%
- **System Uptime**: >99.9%

---

**Onboarding Date**: January 2024  
**Agent Status**: Fully Onboarded  
**Next Action**: Ready for task assignment  
**Repository State**: Production Ready (with MockRedisClient) 