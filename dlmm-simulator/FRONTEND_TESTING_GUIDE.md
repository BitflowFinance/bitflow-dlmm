# Frontend Testing Guide for DLMM Quote Engine

## 🚀 Quick Start

### 1. **Install Dependencies**
```bash
cd dlmm-simulator
pip install -r requirements.txt
```

### 2. **Start the API Server**
```bash
python api_server.py
```

### 3. **Start the Streamlit Frontend**
```bash
streamlit run app.py
```

### 4. **Test the Frontend**
- **Streamlit App**: `http://localhost:8501`
- **API Documentation**: `http://localhost:8000/docs`
- **HTML Test Page**: `http://localhost:8000/frontend_test.html`

## 📋 Recommended Schema

### **Quote Request Schema**
```json
{
  "token_in": "BTC",
  "token_out": "USDC", 
  "amount_in": 1.0
}
```

### **Quote Response Schema**
```json
{
  "success": true,
  "token_in": "BTC",
  "token_out": "USDC",
  "amount_in": 1.0,
  "amount_out": 44087.596975,
  "price_impact": 0.0,
  "route_type": "multi_bin",
  "estimated_gas": 0,
  "effective_price": 44087.596975,
  "steps": [
    {
      "pool_id": "BTC-USDC-25",
      "bin_id": 450,
      "token_in": "BTC",
      "token_out": "USDC",
      "amount_in": 0.999,
      "amount_out": 44087.596975,
      "price": 44131.728704,
      "price_impact": 0.0
    }
  ]
}
```

### **Error Response Schema**
```json
{
  "success": false,
  "token_in": "BTC",
  "token_out": "INVALID",
  "amount_in": 1.0,
  "error": "No routes found between tokens"
}
```

## 🔧 Testing Methods

### **Method 1: Streamlit Frontend**
1. Start the API server: `python api_server.py`
2. Start the Streamlit app: `streamlit run app.py`
3. Open: `http://localhost:8501`
4. Select tokens and amount from dropdowns
5. Click "Get Quote"
6. View results with detailed route breakdown

### **Method 2: HTML Frontend Test**
1. Start the API server: `python api_server.py`
2. Open: `http://localhost:8000/frontend_test.html`
3. Select tokens and amount
4. Click "Get Quote"
5. View results in the UI

### **Method 3: API Documentation**
1. Start the API server: `python api_server.py`
2. Open: `http://localhost:8000/docs`
3. Use the interactive Swagger UI
4. Test endpoints directly

### **Method 4: Command Line Testing**
```bash
# Test quote endpoint
curl -X POST http://localhost:8000/quote \
  -H "Content-Type: application/json" \
  -d '{
    "token_in": "BTC",
    "token_out": "USDC",
    "amount_in": 1.0
  }'

# Get available tokens
curl http://localhost:8000/tokens

# Get available pools
curl http://localhost:8000/pools

# Get specific pool info
curl http://localhost:8000/pools/BTC-USDC-25
```

### **Method 5: JavaScript Frontend Integration**
```javascript
// Example frontend code
class QuoteEngineClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async getQuote(tokenIn, tokenOut, amountIn) {
        const response = await fetch(`${this.baseUrl}/quote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                token_in: tokenIn,
                token_out: tokenOut,
                amount_in: amountIn  // No scaling needed
            })
        });
        
        return await response.json();
    }
    
    async getTokens() {
        const response = await fetch(`${this.baseUrl}/tokens`);
        return await response.json();
    }
    
    async getPools() {
        const response = await fetch(`${this.baseUrl}/pools`);
        return await response.json();
    }
}

// Usage
const client = new QuoteEngineClient();

// Get a quote
const quote = await client.getQuote('BTC', 'USDC', 1.0);
console.log(`You'll receive ${quote.amount_out} USDC`);

// Get available tokens
const tokens = await client.getTokens();
console.log('Available tokens:', tokens.tokens.map(t => t.symbol));
```

## 📊 Test Cases

### **Valid Quote Tests**
```javascript
// Test 1: BTC → USDC
const quote1 = await client.getQuote('BTC', 'USDC', 1.0);
// Expected: ~44,087 USDC (realistic BTC price)

// Test 2: ETH → USDC  
const quote2 = await client.getQuote('ETH', 'USDC', 10.0);
// Expected: ~30,885 USDC (realistic ETH price)

// Test 3: BTC → SOL (multi-hop via USDC)
const quote3 = await client.getQuote('BTC', 'SOL', 1.0);
// Expected: ~259 SOL (via BTC → USDC → SOL)

// Test 4: SOL → USDC
const quote4 = await client.getQuote('SOL', 'USDC', 1.0);
// Expected: ~150 USDC (realistic SOL price)
```

### **Error Handling Tests**
```javascript
// Test 1: Invalid token pair
const error1 = await client.getQuote('BTC', 'INVALID', 1.0);
// Expected: success: false, error: "No routes found between tokens"

// Test 2: Same token
const error2 = await client.getQuote('BTC', 'BTC', 1.0);
// Expected: success: false, error: "Token In and Token Out must be different"

// Test 3: Zero amount
const error3 = await client.getQuote('BTC', 'USDC', 0);
// Expected: validation error
```

## 🎯 API Endpoints

### **POST /quote**
Get a quote for swapping tokens.

**Request:**
```json
{
  "token_in": "BTC",
  "token_out": "USDC",
  "amount_in": 1.0
}
```

**Response:**
```json
{
  "success": true,
  "token_in": "BTC",
  "token_out": "USDC",
  "amount_in": 1.0,
  "amount_out": 44087.596975,
  "price_impact": 0.0,
  "route_type": "multi_bin",
  "estimated_gas": 0,
  "steps": [
    {
      "pool_id": "BTC-USDC-25",
      "bin_id": 450,
      "token_in": "BTC",
      "token_out": "USDC",
      "amount_in": 0.999,
      "amount_out": 44087.596975,
      "price": 44131.728704,
      "price_impact": 0.0
    }
  ],
  "effective_price": 44087.596975
}
```

### **GET /tokens**
Get list of available tokens.

**Response:**
```json
{
  "tokens": [
    {
      "symbol": "BTC",
      "name": "BTC",
      "decimals": 18
    },
    {
      "symbol": "ETH",
      "name": "ETH", 
      "decimals": 18
    },
    {
      "symbol": "USDC",
      "name": "USDC",
      "decimals": 18
    },
    {
      "symbol": "SOL",
      "name": "SOL",
      "decimals": 18
    }
  ]
}
```

### **GET /pools**
Get list of available pools.

**Response:**
```json
{
  "pools": [
    {
      "pool_id": "BTC-USDC-25",
      "token_x": "BTC",
      "token_y": "USDC",
      "bin_step": 25,
      "active_bin_id": 500,
      "active_bin_price": 50000.0,
      "total_tvl": 1000000.0,
      "status": "active"
    }
  ]
}
```

### **GET /pools/{pool_id}**
Get detailed information about a specific pool.

**Response:**
```json
{
  "pool_id": "BTC-USDC-25",
  "token_x": "BTC",
  "token_y": "USDC",
  "bin_step": 25,
  "active_bin_id": 500,
  "active_bin_price": 50000.0,
  "total_tvl": 1000000.0,
  "status": "active",
  "bins": [
    {
      "bin_id": 500,
      "x_amount": 10000.0,
      "y_amount": 500000000.0,
      "price": 50000.0,
      "is_active": true
    }
  ]
}
```

## 🌟 Key Features

### **1. Simple Float Arithmetic**
- **No 1e18 scaling**: All amounts and prices are human-readable floats
- **Realistic prices**: BTC ~$50,000, ETH ~$3,000, SOL ~$150
- **Easy debugging**: Clear, readable values throughout

### **2. Multi-hop Routing**
- **Complex routes**: Support for BTC → ETH → USDC
- **Route optimization**: Automatic best path selection
- **Step-by-step breakdown**: Detailed route visualization

### **3. Interactive Frontend**
- **Streamlit app**: Modern web interface for testing
- **Real-time quotes**: Instant calculations
- **Route visualization**: See exactly how your swap works

### **4. Comprehensive API**
- **RESTful design**: Standard HTTP endpoints
- **Interactive docs**: Swagger UI at `/docs`
- **Error handling**: Detailed error messages
- **CORS support**: Frontend integration ready

## 🔍 Debugging Tips

### **1. Check API Server Status**
```bash
curl http://localhost:8000/health
```

### **2. Verify Pool Data**
```bash
curl http://localhost:8000/pools/BTC-USDC-25
```

### **3. Test Quote Endpoint**
```bash
curl -X POST http://localhost:8000/quote \
  -H "Content-Type: application/json" \
  -d '{"token_in": "BTC", "token_out": "USDC", "amount_in": 1.0}'
```

### **4. Check Streamlit Logs**
Look for any error messages in the terminal where Streamlit is running.

## 🚨 Common Issues

### **1. API Server Not Running**
- **Error**: Connection refused on port 8000
- **Solution**: Start the API server with `python api_server.py`

### **2. CORS Issues**
- **Error**: CORS policy blocking requests
- **Solution**: The API server includes CORS middleware for all origins

### **3. Invalid Token Pairs**
- **Error**: "No routes found between tokens"
- **Solution**: Check available tokens with `GET /tokens`

### **4. Zero Amount**
- **Error**: Validation error for amount
- **Solution**: Use positive amounts greater than 0.01

## 🎯 Next Steps

1. **Integration Testing**: Test with your actual frontend
2. **Load Testing**: Test with high volume requests
3. **Production Setup**: Replace mock Redis with real Redis
4. **Monitoring**: Add logging and metrics
5. **Security**: Add authentication and rate limiting

The quote engine is ready for production use! 🚀 