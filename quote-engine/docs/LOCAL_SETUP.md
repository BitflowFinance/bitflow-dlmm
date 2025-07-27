# Local Setup Guide

This guide will walk you through setting up the DLMM Quote Engine locally for development and testing.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** (recommended: Python 3.11)
- **Redis** (version 6.0+)
- **Git** (for cloning the repository)
- **Docker** (optional, for running Redis in a container)

## Step 1: Clone and Navigate to the Repository

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd bitflow-dlmm

# Navigate to the quote engine directory
cd quote-engine
```

## Step 2: Set Up Python Environment

### Option A: Using the Existing Virtual Environment

The project uses a shared virtual environment in the root directory:

```bash
# Activate the virtual environment
source ../.venv/bin/activate

# Verify Python version
python --version  # Should be 3.8+
```

### Option B: Create a New Virtual Environment

If you prefer a separate environment for the quote engine:

```bash
# Create a new virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

**Required packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `redis` - Redis client
- `networkx` - Graph operations
- `pydantic` - Data validation
- `python-dotenv` - Environment variables

## Step 4: Set Up Redis

### Option A: Using Docker (Recommended)

```bash
# Pull and run Redis container
docker run -d \
  --name redis-dlmm \
  -p 6379:6379 \
  redis:7-alpine

# Verify Redis is running
docker ps | grep redis
```

### Option B: Using Homebrew (macOS)

```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

### Option C: Using System Package Manager

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**CentOS/RHEL:**
```bash
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

### Option D: Building from Source

```bash
# Download and build Redis
wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
make
sudo make install

# Start Redis server
redis-server
```

## Step 5: Verify Redis Connection

```bash
# Test Redis connection
redis-cli ping

# Check Redis info
redis-cli info server
```

## Step 6: Populate Test Data

The quote engine needs test data to function. Run the population script:

```bash
# Populate Redis with test data
python infrastructure/scripts/populate_test_data.py
```

**Expected output:**
```
🚀 Starting Redis data population...
Clearing existing data...
Populating pool data...
Populating bin data...
Added bins for pool: BTC-USDC-25
Added bins for pool: BTC-USDC-50
Added bins for pool: ETH-USDC-25
Added bins for pool: SOL-USDC-25
Populating token graph...
Added token graph
✅ Redis data population completed successfully!
Verifying data...
Found 4 pools
Token graph has 6 pairs
🎉 Ready for testing!
```

## Step 7: Start the Quote Engine

```bash
# Start the FastAPI server
python main.py
```

**Expected output:**
```
🚀 DLMM Quote Engine starting up...
📋 Following Grok's modular design:
   - build_token_graph() - NetworkX-based routing
   - enumerate_paths() - Simple path discovery
   - pre_fetch_shared_data() - Batch Redis operations
   - compute_quote() - Decimal-precise simulation
   - find_best_route() - Multi-hop optimization
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Step 8: Verify the Setup

### Test Health Endpoint

```bash
# Test health check
curl http://localhost:8000/api/v1/health
```

**Expected response:**
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

### Test Quote Endpoint

```bash
# Test a simple quote
curl -X POST http://localhost:8000/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{
    "input_token": "BTC",
    "output_token": "USDC",
    "amount_in": "100000000"
  }'
```

**Expected response:**
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

## Step 9: Access API Documentation

Open your browser and navigate to:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

### Environment Variables

Create a `.env` file in the `quote-engine` directory:

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

### Customizing Pool Configuration

Edit `infrastructure/scripts/populate_test_data.py` to modify:

- Pool parameters (fees, bin steps)
- Token configurations
- Liquidity amounts
- Price ranges

## Troubleshooting

### Common Issues

#### 1. Redis Connection Error

**Error:** `redis_connected: false`

**Solutions:**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis if needed
docker run -d -p 6379:6379 redis:7-alpine
# OR
brew services start redis
```

#### 2. Missing Dependencies

**Error:** `ModuleNotFoundError: No module named 'networkx'`

**Solution:**
```bash
# Install missing packages
pip install networkx redis fastapi uvicorn pydantic python-dotenv
```

#### 3. Port Already in Use

**Error:** `Address already in use`

**Solutions:**
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# OR change the port in .env
PORT=8001
```

#### 4. No Test Data

**Error:** `No viable route found`

**Solution:**
```bash
# Repopulate test data
python infrastructure/scripts/populate_test_data.py
```

#### 5. Virtual Environment Issues

**Error:** `python: command not found`

**Solution:**
```bash
# Ensure virtual environment is activated
source ../.venv/bin/activate

# Verify Python is available
which python
python --version
```

### Debug Mode

Enable debug mode for more detailed logs:

```bash
# Set debug environment variable
export DEBUG=true

# Start server with debug logging
python main.py
```

### Redis Debugging

```bash
# Connect to Redis CLI
redis-cli

# Check keys
KEYS *

# Check specific pool data
HGETALL pool:BTC-USDC-25

# Check bin data
HGETALL bin:BTC-USDC-25:500

# Monitor Redis operations
MONITOR
```

## Development Workflow

### Making Changes

1. **Edit code** in the `src/` directory
2. **Restart the server** (Ctrl+C, then `python main.py`)
3. **Test changes** using curl or the API docs
4. **Check logs** for any errors

### Adding New Features

1. **Update code** in appropriate modules
2. **Add tests** if applicable
3. **Update documentation** in `docs/`
4. **Test thoroughly** with different scenarios

### Database Changes

If you modify the Redis schema:

1. **Update schemas** in `src/redis/schemas.py`
2. **Update population script** in `infrastructure/scripts/populate_test_data.py`
3. **Clear and repopulate** test data
4. **Test all endpoints**

## Performance Testing

### Load Testing

```bash
# Install Apache Bench (if not available)
# macOS: brew install httpd
# Ubuntu: sudo apt install apache2-utils

# Test quote endpoint performance
ab -n 100 -c 10 -p quote_request.json -T application/json http://localhost:8000/api/v1/quote
```

### Memory Usage

```bash
# Monitor memory usage
top -p $(pgrep -f "python main.py")

# Check Redis memory
redis-cli info memory
```

## Next Steps

Once the local setup is working:

1. **Explore the API** using the Swagger UI
2. **Test different scenarios** (small/large swaps, multi-hop routes)
3. **Review the code** to understand the implementation
4. **Make modifications** as needed for your use case
5. **Deploy to production** when ready

## Support

If you encounter issues:

1. **Check the logs** for error messages
2. **Verify Redis connection** and data population
3. **Review this guide** for common solutions
4. **Check the main README** for additional information
5. **Open an issue** in the repository if needed 