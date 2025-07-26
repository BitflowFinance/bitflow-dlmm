# Task 001: Redis Schema Update - Onboarding

## Task Overview

**Task ID**: 001  
**Task Name**: Redis Schema Update  
**Created**: January 2024  
**Status**: Planning Phase  
**Priority**: High

## 🎯 Task Objective

Update the Redis schema to match the new infrastructure requirements specified by the user. The current schema needs to be restructured to use Redis Hash and ZSET data structures instead of JSON objects.

## 📋 Requirements

### New Schema Structure

**Pool Data:**
```
"pool:{pool_id}": {
    "token0": "String (from PoolCreated) [HSET / HGET]",
    "token1": "String (from PoolCreated) [HSET / HGET]",
    "bin_step": "Float (from PoolCreated) [HSET / HGET]",
    "active_bin": "Integer (from PoolCreated or Swap) [HSET / HGET]",
    "active": "Boolean (from PoolActivated/PoolDeactivated) [HSET / HGET]",
    "x_protocol_fee": "Integer (from PoolCreated) [HSET / HGET]",
    "x_provider_fee": "Integer (from PoolCreated) [HSET / HGET]",
    "x_variable_fee": "Integer (from PoolCreated) [HSET / HGET]",
    "y_protocol_fee": "Integer (from PoolCreated) [HSET / HGET]",
    "y_provider_fee": "Integer (from PoolCreated) [HSET / HGET]",
    "y_variable_fee": "Integer (from PoolCreated) [HSET / HGET]"
}
```

**Note**: The original `fee_bps` field was incorrect. The actual fee structure has 6 different fee types:
- **X-direction fees** (for swap-x-for-y): protocol, provider, variable
- **Y-direction fees** (for swap-y-for-x): protocol, provider, variable
- All fees are applied to the **input amount** of the swap
- Fees can be updated at any time and need to be stored in Redis

**Bin Price Index:**
```
"pool:{pool_id}:bins": {
    "type": "ZSET (from PoolCreated) [ZADD / ZRANGE / ZREVRANGE]",
    "member": "bin_id (Integer) (from PoolCreated) [ZADD]",
    "score": "price (Float, derived) (from PoolCreated) [ZADD]"
}
```

**Bin Reserves:**
```
"bin:{pool_id}:{bin_id}": {
    "reserve_x": "Integer (from AddLiquidity/RemoveLiquidity/Swap) [HINCRBY / HGETALL]",
    "reserve_y": "Integer (from AddLiquidity/RemoveLiquidity/Swap) [HINCRBY / HGETALL]",
    "liquidity": "Integer (from AddLiquidity/RemoveLiquidity) [HINCRBY / HGETALL]"
}
```

**Token Graph:**
```
"token_graph:{version}": {
    "key": "tokenA->tokenB (from PoolCreated) [HSET / HGET]",
    "value": "List of pool IDs (Array of Strings) (from PoolCreated) [HSET / HGET]"
}
```

## 🔍 Current State Analysis

### Current Schema (What we have now):

**Pool Data:**
```
"pool:{pool_id}" -> JSON object with fields:
- pool_id, token_x, token_y, bin_step, initial_active_bin_id, active_bin_id, active_bin_price, status, total_tvl, created_at, last_updated
```

**Bin Data:**
```
"bin:{pool_id}:{bin_id}" -> JSON object with fields:
- pool_id, bin_id, x_amount, y_amount, price, total_liquidity, is_active, last_updated
```

**Pair Index:**
```
"pairs:{token_x}:{token_y}" -> JSON object with pools array
```

### Key Differences:

1. **Data Structure**: JSON → Redis Hash (HSET/HGET)
2. **Field Names**: 
   - `token_x` → `token0`
   - `token_y` → `token1`
   - `active_bin_id` → `active_bin`
   - `status` → `active` (boolean)
   - `x_amount` → `reserve_x`
   - `y_amount` → `reserve_y`
   - `total_liquidity` → `liquidity`
3. **Fee Structure**: Replace simple fee with 6 directional fee fields:
   - `x_protocol_fee`, `x_provider_fee`, `x_variable_fee`
   - `y_protocol_fee`, `y_provider_fee`, `y_variable_fee`
4. **New ZSET**: For bin price indexing
5. **Removed Fields**: `price`, `is_active`, `total_tvl`, timestamps
6. **Token Graph**: New structure for routing

## 🛠️ Implementation Plan

### Phase 1: Schema Updates
1. **Update `dlmm-simulator/src/redis/schemas.py`**
   - New data classes for PoolData, BinData
   - Updated validation logic
   - New Redis key patterns

2. **Update `dlmm-simulator/src/redis/data_manager.py`**
   - New data storage/retrieval methods
   - ZSET operations for bin prices
   - Hash operations for pool/bin data

3. **Update `dlmm-simulator/src/quote_engine.py` MockRedisClient**
   - New schema compatibility
   - Updated sample data generation

### Phase 2: Data Migration
1. **Create migration utilities**
   - Convert existing JSON data to Redis Hash/ZSET
   - Validate data integrity
   - Handle field mapping

2. **Update sample data**
   - Generate data matching new schema
   - Test with realistic scenarios

### Phase 3: Code Updates
1. **Update quote engine data access**
   - New Redis operations (HGET, ZRANGE, etc.)
   - Updated bin retrieval logic
   - Price calculation from ZSET

2. **Update API server**
   - New response formats
   - Updated data serialization

3. **Update tests**
   - New schema validation
   - Updated test data

### Phase 4: Performance Optimization
1. **Leverage ZSET for price queries**
2. **Optimize routing with token graph**
3. **Improve caching with new structures**

## 🔧 Technical Considerations

### Data Type Mapping
- **Integers**: `active_bin`, `reserve_x`, `reserve_y`, `liquidity`, `x_protocol_fee`, `x_provider_fee`, `x_variable_fee`, `y_protocol_fee`, `y_provider_fee`, `y_variable_fee`
- **Floats**: `bin_step`, price (in ZSET)
- **Strings**: `token0`, `token1`
- **Booleans**: `active`

### Redis Operations
- **HSET/HGET**: Pool and bin data
- **ZADD/ZRANGE/ZREVRANGE**: Bin price indexing
- **HINCRBY**: Reserve updates during swaps
- **HGETALL**: Complete bin data retrieval

### Backward Compatibility
- **API Responses**: Maintain existing format
- **Internal Data**: Use new schema
- **Migration Path**: Support both during transition

## ❓ Open Questions

1. **Fee Structure**: ✅ RESOLVED - Use 6 directional fee fields (x/y protocol, provider, variable)
2. **Price Storage**: ✅ RESOLVED - Use ZSET for bin price indexing (member: bin_id, score: price)
3. **Token Graph Version**: ✅ RESOLVED - Use "token_graph:1"
4. **Data Migration**: ✅ RESOLVED - Start fresh but use existing data as reference
5. **Performance Impact**: ✅ RESOLVED - Build with performance in mind, optimize later
6. **Fee Defaults**: ✅ RESOLVED - Protocol: 4 bps, Provider: 6 bps, Variable: 0 bps (both directions)

## 🎯 Implementation Ready

**All open questions resolved!** Ready to begin Phase 1: Schema Updates.

## 📋 Implementation Decisions Summary

### ✅ Resolved Questions & Decisions

1. **Fee Structure**: 
   - ✅ Use 6 directional fee fields: `x_protocol_fee`, `x_provider_fee`, `x_variable_fee`, `y_protocol_fee`, `y_provider_fee`, `y_variable_fee`
   - ✅ All fees are integers (basis points)
   - ✅ Fees apply to input amount of swap direction

2. **Price Storage**: 
   - ✅ Use Redis ZSET for bin price indexing: `"pool:{pool_id}:bins"`
   - ✅ Member: `bin_id` (Integer), Score: `price` (Float)
   - ✅ Remove `price` field from individual bin data
   - ✅ Calculate prices using: `P_i = P_active * (1 + bin_step)^(i-active_bin)`

3. **Token Graph Version**: 
   - ✅ Use `"token_graph:1"` as Redis key
   - ✅ Structure: `{"BTC->USDC": ["BTC-USDC-25", "BTC-USDC-50"]}`

4. **Data Migration**: 
   - ✅ Start fresh with new sample data
   - ✅ Use existing data as reference for realistic values
   - ✅ Create migration utilities for future use

5. **Performance Impact**: 
   - ✅ Build with performance in mind, optimize later
   - ✅ Focus on correct implementation first

6. **Fee Defaults**: 
   - ✅ Protocol fees: 4 basis points (0.04%)
   - ✅ Provider fees: 6 basis points (0.06%)
   - ✅ Variable fees: 0 basis points (0.00%)
   - ✅ Same for both X and Y directions

### 🔧 Final Schema Structure

**Pool Data** (`"pool:{pool_id}"` Redis Hash):
```
token0: String
token1: String  
bin_step: Float
active_bin: Integer
active: Boolean
x_protocol_fee: Integer (4)
x_provider_fee: Integer (6)
x_variable_fee: Integer (0)
y_protocol_fee: Integer (4)
y_provider_fee: Integer (6)
y_variable_fee: Integer (0)
```

**Bin Price Index** (`"pool:{pool_id}:bins"` Redis ZSET):
```
member: bin_id (Integer)
score: price (Float)
```

**Bin Reserves** (`"bin:{pool_id}:{bin_id}"` Redis Hash):
```
reserve_x: Integer
reserve_y: Integer
liquidity: Integer
```

**Token Graph** (`"token_graph:1"` Redis Hash):
```
key: "tokenA->tokenB" (String)
value: List of pool IDs (Array of Strings)
```

## 🚀 Next Steps for Implementation

### Phase 1: Schema Updates (START HERE)

1. **Update `dlmm-simulator/src/redis/schemas.py`**
   - Create new `PoolData` class with 6 fee fields
   - Create new `BinData` class without price field
   - Update `RedisSchema` class with new key patterns
   - Update validation logic for new fields

2. **Update `dlmm-simulator/src/redis/data_manager.py`**
   - Add ZSET operations for bin prices
   - Add Hash operations for pool/bin data
   - Update data storage/retrieval methods
   - Add token graph management

3. **Update `dlmm-simulator/src/quote_engine.py` MockRedisClient**
   - Generate new sample data with correct schema
   - Use fee defaults: 4 bps protocol, 6 bps provider, 0 bps variable
   - Create ZSET for bin prices
   - Create token graph structure

### Phase 2: Code Updates
4. **Update quote engine data access**
5. **Update API server responses**
6. **Update tests**

### Phase 3: Testing & Validation
7. **Test all functionality**
8. **Verify performance**
9. **Update documentation**

## ⚠️ Important Notes for Implementation

- **Clarity folder**: NEVER modify files in clarity/ directory
- **API compatibility**: Maintain existing API response formats
- **Sample data**: Use realistic values from existing data as reference
- **Error handling**: Ensure graceful fallbacks
- **Testing**: All existing tests must pass with new schema

## 📊 Success Criteria

- [ ] All Redis operations use new Hash/ZSET structures
- [ ] Quote engine works with new schema
- [ ] API responses remain compatible
- [ ] Performance is maintained or improved
- [ ] All tests pass with new schema
- [ ] Sample data follows new structure
- [ ] Documentation updated

## 📚 Related Files

### Core Files to Modify:
- `dlmm-simulator/src/redis/schemas.py` - Schema definitions
- `dlmm-simulator/src/redis/data_manager.py` - Data management
- `dlmm-simulator/src/quote_engine.py` - MockRedisClient
- `dlmm-simulator/api_server.py` - API responses
- `dlmm-simulator/src/redis/client.py` - Redis operations

### Files to Test:
- `dlmm-simulator/tests/` - All test files
- `dlmm-simulator/examples/` - Example scripts
- `dlmm-simulator/scripts/redis_setup.py` - Setup scripts

---

**Task Status**: Ready for Implementation - All Questions Resolved  
**Assigned Agent**: AI Assistant  
**Last Updated**: January 2024 