# Agent Guide: DLMM Quote Engine Repository

## 🎯 Repository Overview

This repository contains a **Distributed Liquidity Market Maker (DLMM) Quote Engine** with optimized performance, Redis integration, and a complete web interface. The system simulates DeFi liquidity pools with dynamic pricing and multi-bin routing.

### Key Components
- **Quote Engine**: Optimized with caching and graph-based routing
- **Redis Integration**: Real-time data management with fallback
- **API Server**: FastAPI-based REST API
- **Streamlit App**: Web interface for quote testing
- **Performance Benchmarks**: Comprehensive testing suite

## 🏗️ Architecture

### Core Modules
```
src/
├── quote_engine.py          # Main quote engine (optimized)
├── quote_engine_legacy.py   # Original implementation
├── pool.py                  # Pool and bin data structures
├── routing.py               # Single pool router
├── math.py                  # DLMM mathematical functions
└── redis/                   # Redis integration
    ├── __init__.py
    ├── client.py            # Redis client wrapper
    ├── data_manager.py      # Data management
    ├── cache_manager.py     # Graph cache management
    └── schemas.py           # Data schemas
```

### Key Classes
- **QuoteEngine**: Main quote calculation engine
- **LiquidityGraph**: Graph-based pathfinding with caching
- **MockRedisClient**: Fallback Redis client
- **DataManager**: Redis data management
- **SinglePoolRouter**: Pool-specific routing logic

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Navigate to project root
cd /Users/dylanfloyd/Documents/Bitflow/git/bitflow-dlmm

# Activate virtual environment
source .venv/bin/activate

# Navigate to simulator
cd dlmm-simulator
```

### 2. Start Redis (Required for Full Functionality)
```bash
# Option A: Use the setup script (recommended)
python3 scripts/redis_setup.py setup

# Option B: Manual setup
# Install Redis (if not already installed)
brew install redis

# Start Redis service
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### 3. Populate Redis with Sample Data
```bash
# Option A: Use the setup script (recommended)
python3 scripts/redis_setup.py populate

# Option B: Manual population
python3 -c "
from src.redis import RedisConfig, create_redis_client
from src.quote_engine import MockRedisClient

# Create Redis client
config = RedisConfig(host='localhost', port=6379, ssl=False)
client = create_redis_client(config)

# Create mock client with sample data
mock_client = MockRedisClient()

# Copy sample data to Redis
print('📦 Copying sample data to Redis...')
for key in mock_client.keys('*'):
    value = mock_client.get(key)
    if value:
        client.set(key, value)
        print(f'  ✅ {key}')

print(f'🎉 Sample data copied! Total keys: {len(client.keys(\"*\"))}')
"
```

### 4. Start Services
```bash
# Start API server (port 8000)
python3 api_server.py &

# Start Streamlit app (port 8501)
streamlit run app.py --server.port 8501
```

### 5. Test System
```bash
# Test Redis connection
python3 -c "from src.redis import RedisConfig, create_redis_client; config = RedisConfig(); client = create_redis_client(config); print('✅ Redis connection:', client.ping()); print('✅ Health check:', client.health_check())"

# Test quote engine with Redis
python3 -c "from src.redis import RedisConfig, create_redis_client; from src.quote_engine import QuoteEngine; config = RedisConfig(host='localhost', port=6379, ssl=False); client = create_redis_client(config); engine = QuoteEngine(client); quote = engine.get_quote('BTC', 'USDC', 1.0); print('✅ Quote engine with Redis:', quote.success, quote.amount_out)"

# Test API
curl -X POST http://localhost:8000/quote -H "Content-Type: application/json" -d '{"token_in": "BTC", "token_out": "USDC", "amount_in": 1.0}'
```

## 🧪 Testing Redis Integration

### **Verify Redis is Being Used**

**Test 1: Check Redis Connection**
```bash
python3 -c "
from src.redis import RedisConfig, create_redis_client
config = RedisConfig(host='localhost', port=6379, ssl=False)
client = create_redis_client(config)
print('✅ Redis connection:', client.ping())
print('✅ Health check:', client.health_check())
"
```

**Expected Output (Real Redis):**
```
✅ Redis connection: True
✅ Health check: {
  'connected': True, 
  'ping_time_ms': 0.11, 
  'redis_version': '8.0.3', 
  'used_memory_human': '890.36K', 
  'connected_clients': 1
}
```

**Expected Output (MockRedisClient fallback):**
```
✅ Redis connection: True
✅ Health check: {
  'connected': True, 
  'fallback': True, 
  'mock_client': True
}
```

**Test 2: Verify Quote Engine Data Source**
```bash
# Test with real Redis
python3 -c "
from src.redis import RedisConfig, create_redis_client
from src.quote_engine import QuoteEngine
config = RedisConfig(host='localhost', port=6379, ssl=False)
client = create_redis_client(config)
engine = QuoteEngine(client)
quote = engine.get_quote('BTC', 'USDC', 1.0)
print('🚀 Real Redis:')
print(f'   Success: {quote.success}')
print(f'   Amount Out: {quote.amount_out}')
"

# Test with MockRedisClient
python3 -c "
from src.quote_engine import QuoteEngine, MockRedisClient
redis_client = MockRedisClient()
engine = QuoteEngine(redis_client)
quote = engine.get_quote('BTC', 'USDC', 1.0)
print('🔧 MockRedisClient:')
print(f'   Success: {quote.success}')
print(f'   Amount Out: {quote.amount_out}')
"
```

**Test 3: Monitor Redis Data Access**
```bash
# Monitor Redis commands in real-time
redis-cli monitor &

# In another terminal, run a quote
curl -s -X POST http://localhost:8000/quote \
  -H "Content-Type: application/json" \
  -d '{"token_in": "BTC", "token_out": "USDC", "amount_in": 1.0}' > /dev/null

# Stop monitoring
pkill -f "redis-cli monitor"
```

**Expected Output (Redis monitor):**
```
1751871281.624347 [0 127.0.0.1:6379] "KEYS" "pool:*"
1751871281.624348 [0 127.0.0.1:6379] "GET" "pool:BTC-USDC-25"
1751871281.624349 [0 127.0.0.1:6379] "KEYS" "bin:BTC-USDC-25:*"
1751871281.624350 [0 127.0.0.1:6379] "GET" "bin:BTC-USDC-25:500"
...
```

### **Verify Redis Data**
```bash
# Check total keys in Redis
redis-cli dbsize

# List all pools
redis-cli keys "pool:*"

# View pool data
redis-cli get "pool:BTC-USDC-25" | python3 -m json.tool

# List bins for a pool
redis-cli keys "bin:BTC-USDC-25:*" | head -10

# View bin data
redis-cli get "bin:BTC-USDC-25:500" | python3 -m json.tool
```

## 📊 Current System Status

### ✅ Working Components
- **Quote Engine**: Fully optimized with 1.7x performance improvement
- **Redis Integration**: Working with MockRedisClient fallback
- **API Server**: Running on port 8000
- **Graph Routing**: Multi-path discovery working
- **Caching**: Path and quote caching operational

### 🔧 Known Issues
- **Redis Connection**: SSL parameter issue (using fallback)
- **Streamlit Port Conflicts**: Sometimes port 8501 conflicts
- **Import Issues**: Some relative imports in Redis integration

### 📈 Performance Metrics
- **Quote Response Time**: ~4.5ms (first), ~2.6ms (cached)
- **Supported Pools**: 3 (BTC-USDC-25, BTC-USDC-50, SOL-USDC-25)
- **Route Types**: Single-bin, Multi-bin, Multi-pool
- **Cache Hit Rate**: ~60% for repeated requests

## 🛠️ Development Workflow

### Adding New Features
1. **Create feature branch**: `git checkout -b feature/new-feature`
2. **Implement in src/**: Follow existing patterns
3. **Add tests**: Place in `tests/` directory
4. **Update docs**: Update relevant documentation
5. **Test thoroughly**: Run all test suites

### Testing Strategy
```bash
# Run unit tests
python3 -m pytest tests/

# Run performance benchmarks
python3 benchmarks/benchmark_quote_engine.py

# Test API endpoints
python3 tests/test_api_integration.py

# Test Streamlit app
streamlit run app.py --server.port 8501
```

### Code Quality
- **Type Hints**: Required for all functions
- **Docstrings**: Comprehensive documentation
- **Error Handling**: Graceful fallbacks
- **Performance**: Caching and optimization

## 🔍 Debugging Guide

### Common Issues
1. **Port Conflicts**: Kill processes with `pkill -f streamlit`
2. **Import Errors**: Check virtual environment activation
3. **Redis Issues**: System falls back to MockRedisClient
4. **Performance**: Check cache hit rates and memory usage

### Debug Commands
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

## 📚 Key Documentation

### Architecture Documents
- `docs/QUOTE_ENGINE_IMPLEMENTATION.md`: Core engine details
- `docs/REDIS_INTEGRATION.md`: Redis setup and usage
- `docs/PERFORMANCE_ANALYSIS.md`: Performance benchmarks
- `docs/FRONTEND_TESTING_GUIDE.md`: UI testing guide

### Code Examples
- `examples/`: Sample usage and test cases
- `tests/`: Comprehensive test suite
- `benchmarks/`: Performance testing

## 🎯 Recent Changes

### Major Refactoring (Latest)
- **Optimized Quote Engine**: Replaced legacy with optimized version
- **Redis Integration**: Added complete Redis support with fallback
- **Performance Improvements**: 48.4% latency reduction
- **Documentation**: Comprehensive docs and guides

### Key Features Added
- **Graph-based Routing**: Multi-path discovery
- **Caching System**: Path and quote caching
- **Dynamic Pricing**: Real-time price calculations
- **Multi-bin Routing**: Complex swap routing
- **API Integration**: RESTful quote API

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

## 🎪 Repository Structure

```
bitflow-dlmm/
├── .venv/                   # Virtual environment
├── requirements.txt         # Python dependencies
├── README.md               # Main documentation
├── dlmm-simulator/         # Main application
│   ├── src/                # Source code
│   ├── tests/              # Test suite
│   ├── benchmarks/         # Performance tests
│   ├── docs/               # Documentation
│   ├── examples/           # Code examples
│   ├── scripts/            # Utility scripts
│   ├── logs/               # Application logs
│   ├── config/             # Configuration files
│   ├── infrastructure/     # Infrastructure setup
│   ├── api_server.py       # FastAPI server
│   └── app.py              # Streamlit app
```

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

### Performance Issues
1. **Clear caches**: Reset quote and path caches
2. **Monitor memory**: Check for memory leaks
3. **Optimize queries**: Review database queries

## 📞 Contact & Resources

### Key Files for Understanding
- `src/quote_engine.py`: Main engine logic
- `src/redis/client.py`: Redis integration
- `api_server.py`: API implementation
- `app.py`: Streamlit interface

### Performance Monitoring
- **Quote Latency**: Monitor response times
- **Cache Hit Rate**: Track cache effectiveness
- **Memory Usage**: Monitor system resources
- **Error Rates**: Track API error rates

### Success Metrics
- **Quote Success Rate**: >99%
- **Response Time**: <10ms average
- **Cache Hit Rate**: >50%
- **System Uptime**: >99.9%

---

**Last Updated**: January 2024
**Version**: 2.0 (Optimized)
**Status**: Production Ready (with MockRedisClient)
**Next Milestone**: Real Redis Integration 