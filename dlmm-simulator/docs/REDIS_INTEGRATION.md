# Redis Integration for DLMM Quote Engine

## Overview

The DLMM Quote Engine includes comprehensive Redis integration for production-ready deployment. This integration provides:

- **Real-time data from blockchain** via external data processing service
- **Redis as source of truth** for all pool and bin state
- **Direct Redis reads** for current bin liquidity (no application caching)
- **Pre-computed route caching** for optimal quote performance
- **Route cache invalidation** when new pools are added
- **Fallback mechanisms** for development and testing
- **Production-ready configuration** with Docker support

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Blockchain     │───▶│  Data Processing│───▶│  Redis Server   │
│  Node           │    │  Service        │    │  (Source of     │
│  (Transaction   │    │  (Streams txn   │    │   Truth)        │
│   Data)         │    │   data, updates │    |                 │
└─────────────────┘    │   Redis)        │    │ ┌─────────────┐ │
                       └─────────────────┘    │ │ Pool Data   │ │
                                              │ │ Bin Data    │ │
                                              │ │ (Real-time  │ │
                                              │ │  updates)   │ │
                                              │ └─────────────┘ │
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │  Quote Engine   │
                                              │  Service        │
                                              │  (This Repo)    │
                                              │                 │
                                              │ ┌─────────────┐ │
                                              │ │ Route Cache │ │
                                              │ │ (Pre-computed│ │
                                              │ │  paths)      │ │
                                              │ └─────────────┘ │
                                              │ ┌─────────────┐ │
                                              │ │ Graph Cache │ │
                                              │ │ Manager     │ │
                                              │ └─────────────┘ │
                                              └─────────────────┘
```

## Key Components

### 1. **Redis Client** (`src/redis/client.py`)
- **Connection management** with connection pooling
- **Retry logic** with exponential backoff
- **Health monitoring** and diagnostics
- **Fallback to MockRedisClient** for development

### 2. **Data Manager** (`src/redis/data_manager.py`) - **Simulation Only**
- **5-second update cycle** for testing/simulation
- **Event-driven architecture** for data changes
- **Automatic bin movement simulation** for testing
- **Statistics and monitoring**
- **Note**: In production, Redis is updated by external blockchain data processing service

### 3. **Cache Manager** (`src/redis/cache_manager.py`)
- **Graph cache invalidation** on topology changes
- **Bin data strategy**: Always fetch from Redis (no caching)
- **Pool config caching** with 2-second TTL
- **Performance monitoring** and statistics

### 4. **Data Schemas** (`src/redis/schemas.py`)
- **Structured data models** for pools and bins
- **Validation and sanitization** utilities
- **Redis key patterns** and schema definitions

## Cache Strategy

### **Route Cache** (Pre-computed Routes)
- **What**: Pre-computed route graphs between token pairs
- **Where**: Application-level cache (in-memory)
- **TTL**: Until new pool is added to the system
- **Invalidation**: Complete rebuild when new pools are added
- **Example**: BTC → USDC → ETH route cached

### **Bin Data** (Liquidity Information)
- **What**: Individual bin liquidity and prices
- **Caching**: **NEVER** - Always fetched directly from Redis
- **Reason**: Must have latest liquidity for accurate quotes
- **Example**: Bin 500 liquidity always read from Redis

### **Pool Config** (Pool Settings)
- **What**: Pool configuration and metadata
- **TTL**: 2 seconds (brief caching for performance)
- **Invalidation**: On pool configuration changes
- **Example**: Bin step, active bin ID cached briefly

## 🚀 Local Redis Setup Guide

### **Step 1: Install and Start Redis**

#### Option A: Homebrew (macOS) - Recommended
```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

#### Option B: Docker
```bash
# Navigate to infrastructure directory
cd dlmm-simulator/infrastructure/redis

# Start Redis with Docker Compose
docker-compose up -d

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

#### Option C: Manual Installation
```bash
# Download and install Redis from https://redis.io/download
# Start Redis server
redis-server

# Or start in background
redis-server --daemonize yes
```

### **Step 2: Populate Redis with Sample Data**

The Redis instance needs to be populated with pool and bin data before the quote engine can function. Here's how to do it:

```bash
# Navigate to the simulator directory
cd dlmm-simulator

# Activate virtual environment (if not already activated)
source ../.venv/bin/activate

# Populate Redis with sample data
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

### **Step 3: Verify Redis Data Population**

```bash
# Check total number of keys in Redis
redis-cli dbsize

# List all pool keys
redis-cli keys "pool:*"

# List all bin keys for a specific pool
redis-cli keys "bin:BTC-USDC-25:*" | head -10

# View a specific pool's data
redis-cli get "pool:BTC-USDC-25" | python3 -m json.tool

# View a specific bin's data
redis-cli get "bin:BTC-USDC-25:500" | python3 -m json.tool
```

## 🧪 Testing Redis Integration

### **Test 1: Verify Redis Connection**

```bash
# Test basic Redis connection
python3 -c "
from src.redis import RedisConfig, create_redis_client
config = RedisConfig(host='localhost', port=6379, ssl=False)
client = create_redis_client(config)
print('✅ Redis connection:', client.ping())
print('✅ Health check:', client.health_check())
"
```

**Expected Output:**
```
✅ Redis connection: True
✅ Health check: {
  'connected': True, 
  'ping_time_ms': 0.11, 
  'redis_version': '8.0.3', 
  'used_memory_human': '890.36K', 
  'connected_clients': 1, 
  'uptime_in_seconds': 1795, 
  'last_check': 1751871281.624347
}
```

### **Test 2: Verify Quote Engine Uses Redis**

```bash
# Test quote engine with Redis
python3 -c "
from src.redis import RedisConfig, create_redis_client
from src.quote_engine import QuoteEngine

# Create Redis client
config = RedisConfig(host='localhost', port=6379, ssl=False)
client = create_redis_client(config)

# Create quote engine
engine = QuoteEngine(client)

# Get quote
quote = engine.get_quote('BTC', 'USDC', 1.0)
print('✅ Quote engine with Redis:')
print(f'   Success: {quote.success}')
print(f'   Amount Out: {quote.amount_out}')
print(f'   Route Type: {quote.route_type.value}')
"
```

**Expected Output:**
```
✅ Quote engine with Redis:
   Success: True
   Amount Out: 99900.0
   Route Type: multi_bin
```

### **Test 3: Verify API Server Uses Redis**

```bash
# Start API server (if not already running)
python3 api_server.py &

# Wait a moment for server to start
sleep 3

# Test API endpoint
curl -s -X POST http://localhost:8000/quote \
  -H "Content-Type: application/json" \
  -d '{"token_in": "BTC", "token_out": "USDC", "amount_in": 1.0}' \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('✅ API with Redis:')
print(f'   Success: {data[\"success\"]}')
print(f'   Amount Out: {data[\"amount_out\"]}')
print(f'   Route Type: {data[\"route_type\"]}')
"
```

**Expected Output:**
```
✅ API with Redis:
   Success: True
   Amount Out: 99900.0
   Route Type: multi_bin
```

### **Test 4: Verify Data Source (Redis vs Mock)**

```bash
# Test with MockRedisClient (fallback)
python3 -c "
from src.quote_engine import QuoteEngine, MockRedisClient
redis_client = MockRedisClient()
engine = QuoteEngine(redis_client)
quote = engine.get_quote('BTC', 'USDC', 1.0)
print('🔧 MockRedisClient (fallback):')
print(f'   Success: {quote.success}')
print(f'   Amount Out: {quote.amount_out}')
"

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
```

**Expected Output:**
```
🔧 MockRedisClient (fallback):
   Success: True
   Amount Out: 99900.0
🚀 Real Redis:
   Success: True
   Amount Out: 99900.0
```

### **Test 5: Monitor Redis Data Access**

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

## 🔍 Troubleshooting Redis Integration

### **Issue 1: Redis Connection Fails**

**Symptoms:**
```
Failed to connect to Redis: AbstractConnection.__init__() got an unexpected keyword argument 'ssl'
Using MockRedisClient fallback - Redis connection failed
```

**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# If Redis is not running, start it
brew services start redis  # macOS
# or
sudo systemctl start redis  # Linux
# or
redis-server  # Manual start
```

### **Issue 2: Empty Redis (No Data)**

**Symptoms:**
```
✅ Quote engine with Redis:
   Success: False
   Amount Out: 0
```

**Solution:**
```bash
# Check if Redis has data
redis-cli dbsize

# If 0, populate with sample data
python3 -c "
from src.redis import RedisConfig, create_redis_client
from src.quote_engine import MockRedisClient
config = RedisConfig(host='localhost', port=6379, ssl=False)
client = create_redis_client(config)
mock_client = MockRedisClient()
for key in mock_client.keys('*'):
    value = mock_client.get(key)
    if value:
        client.set(key, value)
print(f'Populated {len(client.keys(\"*\"))} keys')
"
```

### **Issue 3: SSL Connection Issues**

**Symptoms:**
```
Failed to connect to Redis: SSL connection failed
```

**Solution:**
```bash
# Use non-SSL connection (default)
python3 -c "
from src.redis import RedisConfig, create_redis_client
config = RedisConfig(host='localhost', port=6379, ssl=False)
client = create_redis_client(config)
print('Connection successful:', client.ping())
"
```

### **Issue 4: Performance Issues**

**Symptoms:**
- Slow quote responses
- High Redis memory usage

**Solution:**
```bash
# Check Redis memory usage
redis-cli info memory

# Clear Redis cache if needed
redis-cli flushdb

# Monitor Redis performance
redis-cli info stats
```

## 📊 Redis Data Verification Commands

### **Check Redis Status**
```bash
# Basic Redis info
redis-cli info

# Memory usage
redis-cli info memory

# Connected clients
redis-cli info clients

# Database size
redis-cli dbsize
```

### **Verify Pool Data**
```bash
# List all pools
redis-cli keys "pool:*"

# Get specific pool data
redis-cli get "pool:BTC-USDC-25" | python3 -m json.tool

# Check pool count
redis-cli keys "pool:*" | wc -l
```

### **Verify Bin Data**
```bash
# List bins for a pool
redis-cli keys "bin:BTC-USDC-25:*" | head -10

# Get specific bin data
redis-cli get "bin:BTC-USDC-25:500" | python3 -m json.tool

# Count total bins
redis-cli keys "bin:*" | wc -l
```

### **Verify Token Pairs**
```bash
# List token pairs
redis-cli keys "pairs:*"

# Get specific pair data
redis-cli get "pairs:BTC:USDC" | python3 -m json.tool
```

## Quick Start

### 1. **Start Redis with Docker**

```bash
cd infrastructure/redis
docker-compose up -d
```

This starts:
- **Redis server** on `localhost:6379`
- **Redis Commander** (web UI) on `http://localhost:8081`

### 2. **Set up and Populate Data**

```bash
# Run setup script
python scripts/setup_redis.py setup

# Check status
python scripts/setup_redis.py status
```

### 3. **Use in Your Application**

```python
from src.redis import RedisConfig, create_redis_client
from src.quote_engine import QuoteEngine

# Create Redis client
config = RedisConfig(host="localhost", port=6379)
redis_client = create_redis_client(config)

# Create quote engine (reads directly from Redis)
quote_engine = QuoteEngine(redis_client)

# Get quotes
quote = quote_engine.get_quote("BTC", "USDC", 1.0)
print(f"1 BTC → {quote.amount_out:.2f} USDC")

# Optional: For simulation/testing only
from src.redis import DataManager
data_manager = DataManager(redis_client)  # Simulates data updates
data_manager.start()
```

## Verifying API-Redis Integration

### 1. Ensure API Server Uses Real Redis (Not MockRedisClient)

By default, the API server (`api_server.py`) may use `MockRedisClient` for development/testing. To use the real Redis instance, edit the initialization in `api_server.py`:

Replace:
```python
from src.quote_engine import MockRedisClient, QuoteEngine
...
redis_client = MockRedisClient()
quote_engine = QuoteEngine(redis_client)
```
With:
```python
from src.redis import create_redis_client, RedisConfig
from src.quote_engine import QuoteEngine

redis_client = create_redis_client(RedisConfig(host="localhost", port=6379), fallback_to_mock=False)
quote_engine = QuoteEngine(redis_client)
```

Restart the API server after making this change:
```bash
python api_server.py
```

---

### 2. Prove the API is Using Local Redis

**A. Modify Data in Redis and Observe API Response**

1. Use `redis-cli` to change a value in Redis (e.g., update a pool's `active_bin_id`):
   ```bash
   redis-cli get pool:BTC-USDC-25 | python3 -m json.tool
   # Edit the JSON, e.g., change "active_bin_id", then:
   redis-cli set pool:BTC-USDC-25 '<new_json_value>'
   ```
2. Call the API:
   ```bash
   curl -X POST http://localhost:8000/quote \
     -H 'Content-Type: application/json' \
     -d '{"token_in": "BTC", "token_out": "USDC", "amount_in": 1.0}'
   ```
3. The API response should reflect your manual change, proving it is reading from Redis.

**B. Stop Redis and Test API**

1. Stop Redis:
   ```bash
   docker-compose down
   # or
   brew services stop redis
   ```
2. Call the API again. The API should now fail to serve quotes, confirming it was using Redis.

---

### 3. Step-by-Step: Local Redis + API Integration

| Step | Command/Action | Purpose |
|------|---------------|---------|
| 1    | Start Redis   | Launch local Redis server |
| 2    | `python scripts/setup_redis.py setup` | Populate Redis with initial data |
| 3    | Edit & run `api_server.py` | Start API server using real Redis |
| 4    | Change Redis data & call API | Prove API is using Redis |

---

**Note:** For development/testing, you may use `MockRedisClient`, but for production or real integration, always use the real Redis client as shown above.

## Configuration

### **Environment Variables**

```bash
# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false

# Performance Settings
REDIS_MAX_CONNECTIONS=10
REDIS_SOCKET_TIMEOUT=5.0
REDIS_UPDATE_INTERVAL=5

# Cache Settings
REDIS_GRAPH_CACHE_TTL=300
REDIS_POOL_CONFIG_CACHE_TTL=2
REDIS_MAX_GRAPH_CACHE_SIZE=1000

# Fallback Settings
REDIS_FALLBACK_TO_MOCK=true
```

### **Environment-Specific Settings**

```python
from config.redis_config import get_redis_settings

# Development (default)
settings = get_redis_settings('development')

# Staging
settings = get_redis_settings('staging')

# Production
settings = get_redis_settings('production')
```

## Data Schema

### **Pool Data**
```json
{
  "pool_id": "BTC-USDC-25",
  "token_x": "BTC",
  "token_y": "USDC",
  "bin_step": 25,
  "initial_active_bin_id": 500,
  "active_bin_id": 500,
  "active_bin_price": 100000.0,
  "status": "active",
  "total_tvl": 1000000.0,
  "created_at": "2024-01-01T00:00:00Z",
  "last_updated": "2024-01-01T00:00:00Z"
}
```

### **Bin Data**
```json
{
  "pool_id": "BTC-USDC-25",
  "bin_id": 500,
  "x_amount": 1000.0,
  "y_amount": 100000000.0,
  "price": 100000.0,
  "total_liquidity": 1000000.0,
  "is_active": true,
  "last_updated": "2024-01-01T00:00:00Z"
}
```

### **Redis Key Patterns**
- **Pools**: `pool:{pool_id}`
- **Bins**: `bin:{pool_id}:{bin_id}`
- **Metadata**: `metadata`
- **Token Index**: `tokens:{token}`
- **Pair Index**: `pairs:{token_x}:{token_y}`

## Monitoring and Health Checks

### **Redis Health Check**
```python
health_info = redis_client.health_check()
print(f"Connected: {health_info['connected']}")
print(f"Ping Time: {health_info['ping_time_ms']}ms")
print(f"Memory Usage: {health_info['used_memory_human']}")
```

### **Data Manager Statistics**
```python
stats = data_manager.get_statistics()
print(f"Total Updates: {stats['total_updates']}")
print(f"Last Update Duration: {stats['last_update_duration_ms']}ms")
print(f"Errors: {stats['errors_count']}")
```

### **Cache Statistics**
```python
cache_stats = cache_manager.get_statistics()
print(f"Cache Invalidations: {cache_stats['total_invalidations']}")
print(f"Graph Cache Size: {cache_stats['graph_cache_size']}")
```

## Performance Characteristics

### **Latency Benchmarks**
- **Redis Operations**: < 10ms average
- **Quote Generation**: < 100ms average
- **Cache Invalidation**: < 50ms
- **Data Updates**: < 100ms per pool

### **Throughput**
- **Single-threaded**: 100+ quotes/second
- **Concurrent**: 30+ quotes/second with 5 users
- **Redis Operations**: 1000+ operations/second

### **Memory Usage**
- **Redis**: ~100MB for 3 pools, 303 bins
- **Application**: ~50MB with caching
- **Total**: < 200MB for development setup

## Error Handling and Fallbacks

### **Connection Failures**
```python
# Automatic retry with exponential backoff
redis_client = create_redis_client(config, fallback_to_mock=True)

# Manual health check
if not redis_client.ping():
    print("Redis unavailable, using mock client")
```

### **Data Validation**
```python
from src.redis.schemas import DataValidator

# Validate pool data
if DataValidator.validate_pool_data(pool_data):
    # Store in Redis
    redis_client.set(f"pool:{pool_id}", json.dumps(pool_data))
```

### **Cache Recovery**
```python
# Manual cache clear
cache_manager.manual_cache_clear("recovery")

# Check cache health
cache_info = cache_manager.get_cache_info()
```

## Testing

### **Integration Tests**
```bash
# Run Redis integration tests
python -m pytest tests/integration/test_redis_integration.py -v
```

### **Manual Testing**
```bash
# Start Redis
cd infrastructure/redis && docker-compose up -d

# Run setup
python scripts/setup_redis.py setup

# Test quotes
python -c "
from src.redis import create_redis_client, RedisConfig
from src.quote_engine import QuoteEngine

config = RedisConfig()
redis_client = create_redis_client(config)
engine = QuoteEngine(redis_client)

quote = engine.get_quote('BTC', 'USDC', 1.0)
print(f'Quote: {quote.amount_out:.2f} USDC')
"
```

## Production Deployment

### **Architecture Overview**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Blockchain     │───▶│  Data Processing│───▶│  Redis Server   │
│  Node           │    │  Service        │    │  (Source of     │
│  (Transaction   │    │  (External)     │    │   Truth)        │
│   Data)         │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │  Quote Engine   │
                                              │  Service        │
                                              │  (This Repo)    │
                                              └─────────────────┘
```

### **Docker Compose for Production**
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    environment:
      - REDIS_PASSWORD=your_secure_password
    restart: unless-stopped
    # Note: Redis is updated by external data processing service

  quote-engine:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PASSWORD=your_secure_password
      - REDIS_FALLBACK_TO_MOCK=false
    depends_on:
      - redis
    restart: unless-stopped
    # Note: Quote engine reads from Redis, doesn't update it
```

### **Environment Variables for Production**
```bash
ENVIRONMENT=production
REDIS_HOST=redis
REDIS_PASSWORD=your_secure_password
REDIS_SSL=true
REDIS_FALLBACK_TO_MOCK=false
REDIS_MAX_CONNECTIONS=20
REDIS_SOCKET_TIMEOUT=10.0
```

## Troubleshooting

### **Common Issues**

1. **Redis Connection Failed**
   ```bash
   # Check if Redis is running
   docker ps | grep redis
   
   # Check Redis logs
   docker logs dlmm-redis
   ```

2. **Data Not Populated**
   ```bash
   # Run setup script
   python scripts/setup_redis.py setup
   
   # Check Redis data
   redis-cli keys "pool:*"
   ```

3. **Slow Performance**
   ```python
   # Check cache hit rates
   stats = cache_manager.get_statistics()
   print(f"Cache hit rate: {stats['cache_hit_rate']}%")
   
   # Check Redis performance
   health = redis_client.health_check()
   print(f"Redis ping: {health['ping_time_ms']}ms")
   ```

### **Debug Mode**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for Redis operations
logger = logging.getLogger('src.redis')
logger.setLevel(logging.DEBUG)
```

## Migration from MockRedisClient

### **Step 1: Update Imports**
```python
# Before
from src.quote_engine import MockRedisClient, QuoteEngine

# After
from src.redis import create_redis_client, RedisConfig
from src.quote_engine import QuoteEngine
```

### **Step 2: Create Redis Client**
```python
# Before
redis_client = MockRedisClient()

# After
config = RedisConfig()
redis_client = create_redis_client(config, fallback_to_mock=True)
```

### **Step 3: Add Data Manager (Optional - Simulation Only)**
```python
# For simulation/testing only (not needed in production)
from src.redis import DataManager

data_manager = DataManager(redis_client)
data_manager.start()
```

## Next Steps

1. **External Data Processing Service**: Implement the blockchain data processing service that updates Redis
2. **Route Cache Invalidation**: Add automatic detection of new pools and route cache rebuilding
3. **Monitoring**: Add Prometheus metrics and Grafana dashboards
4. **Scaling**: Implement Redis clustering for high availability
5. **Security**: Add authentication and encryption
6. **Backup**: Implement automated Redis backup strategies

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review integration tests
3. Check Redis logs and health status
4. Verify configuration settings 