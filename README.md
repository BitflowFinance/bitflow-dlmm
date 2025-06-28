# DLMM Simulator

A Python-based simulator for testing and analyzing DLMM (Decentralized Liquidity Market Maker) routing logic with an interactive visualization tool.

## Quick Start

### Prerequisites

- **Python 3.8+** (3.8, 3.9, 3.10, or 3.11 recommended)
- **Git** for cloning the repository
- **pip** for package management

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd bitflow-dlmm/dlmm-simulator
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Create virtual environment
   python3 -m venv .venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the visualization app:**
   ```bash
   streamlit run app.py --server.headless true
   ```

5. **Open your browser:**
   Navigate to `http://localhost:8502` (or the URL shown in the terminal)

### Troubleshooting

**Common Issues:**

1. **Python version issues:**
   ```bash
   # Check your Python version
   python3 --version
   
   # If you need to install Python 3.8+
   # On macOS with Homebrew:
   brew install python@3.11
   
   # On Ubuntu/Debian:
   sudo apt update
   sudo apt install python3.11 python3.11-venv
   ```

2. **Streamlit not found:**
   ```bash
   # Make sure you're in the virtual environment
   which python
   # Should show path to .venv/bin/python
   
   # Reinstall streamlit if needed
   pip install streamlit
   ```

3. **Port already in use:**
   ```bash
   # Use a different port
   streamlit run app.py --server.port 8503 --server.headless true
   ```

4. **Permission issues on macOS:**
   ```bash
   # Install Xcode command line tools (needed for some packages)
   xcode-select --install
   
   # Install watchdog for better performance
   pip install watchdog
   ```

### Development Setup

For development work:

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_routing.py -v

# Run with coverage
pip install pytest-cov
python -m pytest tests/ --cov=src --cov-report=html
```

### Package Versions

The following key packages are used:

- **Streamlit**: 1.28.0+ (for visualization)
- **Plotly**: 5.17.0+ (for interactive charts)
- **Pandas**: 2.0.0+ (for data manipulation)
- **NumPy**: 1.24.0+ (for numerical operations)
- **Pytest**: 7.0.0+ (for testing)

### File Structure

```
dlmm-simulator/
├── app.py                 # Main Streamlit visualization app
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── src/                  # Core simulation code
│   ├── __init__.py
│   ├── pool.py          # Pool data structures and mock data
│   ├── routing.py       # Routing algorithms
│   ├── math.py          # Mathematical formulas and calculations
│   └── utils.py         # Utility functions
├── tests/               # Test files
│   ├── __init__.py
│   ├── test_pool.py
│   ├── test_routing.py
│   └── test_quotes.py
└── examples/            # Example scripts
    ├── basic_routing.py
    └── multi_pool_routing.py
```

## Features

- Mock pool data generation with bell curve liquidity distribution
- Single-pool multi-bin routing simulation
- Multi-pool routing with pathfinding algorithms
- Price impact calculations
- Quote generation and optimization

## Mathematical Formulas

### Core DLMM Formulas

#### Bin Price Calculation
The price at bin $i$ is calculated using:
$$P_i = P_{active} \times (1 + s)^{(i - i_{active})}$$

Where:
- $P_i$ = Price at bin $i$
- $P_{active}$ = Price at the active bin
- $s$ = Bin step size (in bps)
- $i$ = Bin ID
- $i_{active}$ = Active bin ID (usually 500)

#### Bin Liquidity
Total liquidity in a bin:
$$L_i = x_i + \frac{y_i}{P_i}$$

Where:
- $L_i$ = Total liquidity in bin $i$
- $x_i$ = Amount of token X in bin $i$
- $y_i$ = Amount of token Y in bin $i$
- $P_i$ = Price at bin $i$

### Quote Functions

#### 1. Single Bin Quote (get-x-for-y)

**Formula:**
$$\Delta y = \min(P_i \cdot \Delta x, y_i)$$

**Where:**
- $\Delta x$ = Input amount of token X
- $\Delta y$ = Output amount of token Y
- $P_i$ = Price at bin $i$
- $y_i$ = Available Y tokens in bin $i$

**Algorithm:**
1. Calculate available X tokens in the bin: $x_i$
2. Use amount: $x_{used} = \min(\Delta x, x_i)$
3. Output: $\Delta y = \min(P_i \cdot x_{used}, y_i)$ (using bin price)
4. Remaining: $\Delta x_{remaining} = \Delta x - x_{used}$

#### 2. Single Bin Quote (get-y-for-x)

**Formula:**
$$\Delta x = \min\left(\frac{\Delta y}{P_i}, x_i\right)$$

**Where:**
- $\Delta y$ = Input amount of token Y
- $\Delta x$ = Output amount of token X
- $P_i$ = Price at bin $i$
- $x_i$ = Available X tokens in bin $i$

**Algorithm:**
1. Calculate available Y tokens in the bin: $y_i$
2. Use amount: $y_{used} = \min(\Delta y, y_i)$
3. Output: $\Delta x = \min\left(\frac{y_{used}}{P_i}, x_i\right)$ (using bin price)
4. Remaining: $\Delta y_{remaining} = \Delta y - y_{used}$

#### 3. Multi-Bin Quote (Single Pool)

**Formula:**
$$\Delta y_{total} = \sum_{j \in \text{bins}} \min(P_j \cdot \Delta x_j, y_j)$$

**Where:**
- $\Delta x_j$ = Amount of X used in bin $j$
- $P_j$ = Price at bin $j$
- $y_j$ = Available Y tokens in bin $j$
- $\text{bins}$ = Sequence of bins traversed

**Algorithm for X→Y:**
1. Start from active bin, move right (higher prices, higher bin IDs)
2. For each bin $j$ in sequence:
   - Calculate available Y tokens in the bin: $y_j$
   - Calculate max X that can be used: $x_{max,j} = y_j / P_j$ (using bin price)
   - Use amount: $x_{used,j} = \min(\Delta x_{remaining}, x_{max,j})$
   - Output: $\Delta y_j = x_{used,j} \cdot P_j$ (using bin price)
   - Update remaining: $\Delta x_{remaining} = \Delta x_{remaining} - x_{used,j}$
3. Total output: $\Delta y_{total} = \sum_j \Delta y_j$

**Algorithm for Y→X:**
1. Start from active bin, move left (lower prices, lower bin IDs)
2. For each bin $j$ in sequence:
   - Calculate available X tokens in the bin: $x_j$
   - Calculate max Y that can be used: $y_{max,j} = x_j \cdot P_j$ (using bin price)
   - Use amount: $y_{used,j} = \min(\Delta y_{remaining}, y_{max,j})$
   - Output: $\Delta x_j = y_{used,j} / P_j$ (using bin price)
   - Update remaining: $\Delta y_{remaining} = \Delta y_{remaining} - y_{used,j}$
3. Total output: $\Delta x_{total} = \sum_j \Delta x_j$

#### 4. Multi-Pool Quote (Same Trading Pair)

**Formula:**
$$\Delta y_{total} = \sum_{p \in \text{pools}} \sum_{j \in \text{bins}_p} \min(P_{p,j} \cdot \Delta x_{p,j}, y_{p,j})$$

**Where:**
- $\text{pools}$ = Set of pools for the same trading pair
- $\text{bins}_p$ = Bins in pool $p$
- $P_{p,j}$ = Price at bin $j$ of pool $p$
- $\Delta x_{p,j}$ = Amount used in bin $j$ of pool $p$
- $y_{p,j}$ = Available Y tokens in bin $j$ of pool $p$

**Algorithm:**
1. Find all pools for the trading pair
2. For each pool $p$:
   - Apply single-pool multi-bin algorithm
   - Track total output: $\Delta y_p$
3. Total output: $\Delta y_{total} = \sum_p \Delta y_p$

#### 5. Cross-Pair Quote (Multiple Trading Pairs)

**Formula:**
$$\Delta y_{final} = \prod_{h \in \text{hops}} \left(\sum_{j \in \text{bins}_h} \min(P_{h,j} \cdot \Delta x_{h,j}, y_{h,j})\right)$$

**Where:**
- $\text{hops}$ = Sequence of pool hops
- $\text{bins}_h$ = Bins in hop $h$
- $P_{h,j}$ = Price at bin $j$ of hop $h$
- $\Delta x_{h,j}$ = Amount used in bin $j$ of hop $h$
- $y_{h,j}$ = Available tokens in bin $j$ of hop $h$

**Algorithm:**
1. Find all possible paths between tokens
2. For each path:
   - Apply multi-bin algorithm for each hop
   - Chain outputs: $\Delta y_{h+1} = \Delta y_h$ (output becomes input for next hop)
3. Select path with maximum final output

### Price Impact Calculation

**Formula:**
$$\text{Price Impact} = \frac{|P_{effective} - P_{active}|}{P_{active}} \times 100\%$$

**Where:**
- $P_{effective} = \frac{\Delta y_{total}}{\Delta x_{total}}$ (for X→Y)
- $P_{effective} = \frac{\Delta x_{total}}{\Delta y_{total}}$ (for Y→X)
- $P_{active}$ = Price at the active bin

### Slippage Calculation

**Formula:**
$$\text{Slippage} = \frac{|\Delta y_{expected} - \Delta y_{actual}|}{\Delta y_{expected}} \times 100\%$$

**Where:**
- $\Delta y_{expected} = \Delta x \times P_{active}$ (for X→Y)
- $\Delta y_{actual}$ = Actual output received

## Current Implementation Status

### ✅ Completed Features

1. **Single Bin Quotes**
   - X for Y swaps within active bin
   - Y for X swaps within active bin
   - Correct constant sum AMM using bin prices

2. **Multi-Bin Quotes (Single Pool)**
   - X for Y swaps across multiple bins (rightward traversal)
   - Y for X swaps across multiple bins (leftward traversal)
   - Correct bin sequence validation
   - Price impact calculations

3. **Insufficient Liquidity Handling**
   - Proper error messages when liquidity is exhausted
   - Partial swap execution with remaining amount reporting

4. **Multi-Pool Same Pair (Different Bin Steps)**
   - Basic multi-pool routing for same trading pair
   - Different bin step configurations

### 🔄 In Progress / Needs Work

1. **Multi-Pool Same Pair (Same Bin Step)**
   - Router not properly distributing swaps across multiple pools
   - Need to implement optimal pool selection logic

2. **Cross-Pair Quotes**
   - Pathfinding between different token pairs not working
   - Need to implement proper multi-hop routing logic

### 📋 Test Coverage

- **11 passing tests** out of 15 total tests
- Single bin, multi-bin, and insufficient liquidity tests all passing
- Multi-pool and cross-pair tests need fixes

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest tests/
```

3. Run examples:
```bash
python examples/basic_routing.py
```

## Usage

```python
from src.pool import MockPool
from src.routing import SinglePoolRouter

# Create a mock pool
pool = MockPool.create_bell_curve_pool()

# Create router
router = SinglePoolRouter(pool)

# Get quote
quote = router.get_quote(token_in="BTC", amount_in=1.0, token_out="USDC")
print(f"Quote: {quote}")
```

## Test Coverage

The simulator includes comprehensive tests for:

1. **Single Bin Quotes**
   - X for Y swaps within active bin
   - Y for X swaps within active bin
   - Constant sum AMM validation (1:1 ratio)

2. **Multi-Bin Quotes**
   - X for Y swaps across multiple bins
   - Y for X swaps across multiple bins
   - Price impact validation
   - Bin sequence verification

3. **Multi-Pool Same Pair Quotes**
   - Routing across multiple pools for same trading pair
   - Optimal pool selection
   - Liquidity aggregation

4. **Cross-Pair Quotes**
   - Routing across multiple trading pairs
   - Path optimization
   - Multi-hop validation

5. **Edge Cases**
   - Insufficient liquidity
   - Minimum output requirements
   - Invalid token pairs
   - Same token swaps 

## Quote Calculation Pseudocode

### Overview
The quote function calculates the maximum output amount a user can receive for a given input amount, assuming no other swaps occur before their swap. This is based on the current state of bins across all relevant pools.

### Single Pool Multi-Bin Quote Pseudocode

```
FUNCTION getQuote(tokenIn, amountIn, tokenOut, pool):
    // Validate tokens
    IF tokenIn NOT IN [pool.xToken, pool.yToken] OR tokenOut NOT IN [pool.xToken, pool.yToken]:
        RETURN error("Invalid token pair")
    
    IF tokenIn == tokenOut:
        RETURN { amountOut: amountIn, priceImpact: 0, success: true }
    
    // Determine swap direction
    isXtoY = (tokenIn == pool.xToken AND tokenOut == pool.yToken)
    
    // Initialize tracking variables
    remainingAmount = amountIn
    totalAmountOut = 0
    steps = []
    activePrice = pool.activeBinPrice
    
    // Determine bin traversal order
    IF isXtoY:
        // X->Y: start from active bin, then move right (higher bin IDs, higher prices)
        binSequence = [activeBinId] + range(activeBinId + 1, maxBinId + 1)
    ELSE:
        // Y->X: start from active bin, then move left (lower bin IDs, lower prices)  
        binSequence = [activeBinId] + range(activeBinId - 1, -1, -1)
    
    // Process each bin in sequence
    FOR binId IN binSequence:
        IF remainingAmount <= 0:
            BREAK
            
        binData = pool.getBin(binId)
        IF binData IS NULL:
            CONTINUE
            
        // Calculate swap within this bin
        IF isXtoY:
            // X->Y: Δy = min(P_i * Δx, y_i)
            // Max X we can use = y_amount / price
            maxXUsable = binData.yAmount / binData.price
            xToUse = min(remainingAmount, maxXUsable)
            yOut = xToUse * binData.price
            remainingAmount = remainingAmount - xToUse
        ELSE:
            // Y->X: Δx = min(Δy / P_i, x_i)
            // Max Y we can use = x_amount * price
            maxYUsable = binData.xAmount * binData.price
            yToUse = min(remainingAmount, maxYUsable)
            xOut = yToUse / binData.price
            remainingAmount = remainingAmount - yToUse
            
        // Only record step if we actually used liquidity
        IF xToUse > 0 AND yOut > 0:  // or yToUse > 0 AND xOut > 0
            totalAmountOut += yOut  // or xOut
            priceImpact = calculatePriceImpact(xToUse, yOut, isXtoY, activePrice)
            
            step = {
                poolId: pool.id,
                binId: binId,
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                amountIn: xToUse,  // or yToUse
                amountOut: yOut,   // or xOut
                price: binData.price,
                priceImpact: priceImpact
            }
            steps.append(step)
    
    // Check if we have insufficient liquidity
    IF remainingAmount > 0:
        RETURN {
            amountOut: totalAmountOut,
            steps: steps,
            success: false,
            error: "Insufficient liquidity: " + remainingAmount + " unswapped"
        }
    
    // Calculate total price impact
    totalPriceImpact = sum(step.priceImpact for step in steps)
    
    RETURN {
        amountOut: totalAmountOut,
        steps: steps,
        priceImpact: totalPriceImpact,
        success: true
    }
```

### Multi-Pool Same Trading Pair Quote Pseudocode

```
FUNCTION getQuoteMultiPool(tokenIn, amountIn, tokenOut, pools):
    // Find all pools supporting this trading pair
    matchingPools = []
    FOR pool IN pools:
        IF (pool.xToken == tokenIn AND pool.yToken == tokenOut) OR 
           (pool.yToken == tokenIn AND pool.xToken == tokenOut):
            matchingPools.append(pool)
    
    IF matchingPools.length == 0:
        RETURN error("No pools found for trading pair")
    
    IF matchingPools.length == 1:
        RETURN getQuote(tokenIn, amountIn, tokenOut, matchingPools[0])
    
    // Try different split ratios across multiple pools
    bestResult = null
    bestTotalOutput = 0
    
    FOR ratio IN [0.5, 0.6, 0.7, 0.8, 0.9]:
        amount1 = amountIn * ratio
        amount2 = amountIn * (1 - ratio)
        
        quote1 = getQuote(tokenIn, amount1, tokenOut, matchingPools[0])
        quote2 = getQuote(tokenIn, amount2, tokenOut, matchingPools[1])
        
        IF quote1.success AND quote2.success:
            totalOutput = quote1.amountOut + quote2.amountOut
            totalPriceImpact = (quote1.priceImpact + quote2.priceImpact) / 2
            
            // Combine steps from both pools
            allSteps = []
            FOR step IN quote1.steps:
                step.poolId = matchingPools[0].id
                allSteps.append(step)
            
            FOR step IN quote2.steps:
                step.poolId = matchingPools[1].id
                allSteps.append(step)
            
            result = {
                amountOut: totalOutput,
                steps: allSteps,
                priceImpact: totalPriceImpact,
                success: true
            }
            
            IF totalOutput > bestTotalOutput:
                bestResult = result
                bestTotalOutput = totalOutput
    
    // Fallback to single pool if no successful split
    IF bestResult IS NULL:
        FOR pool IN matchingPools:
            quote = getQuote(tokenIn, amountIn, tokenOut, pool)
            IF quote.success AND quote.amountOut > bestTotalOutput:
                bestResult = quote
                bestTotalOutput = quote.amountOut
    
    RETURN bestResult
```

### Price Impact Calculation Pseudocode

```
FUNCTION calculatePriceImpact(amountIn, amountOut, isXtoY, activePrice):
    IF amountIn == 0 OR amountOut == 0:
        RETURN 0
    
    IF isXtoY:
        // X->Y: effective price = amountOut / amountIn (USDC per BTC)
        effectivePrice = amountOut / amountIn
        priceImpact = abs(effectivePrice - activePrice) / activePrice
    ELSE:
        // Y->X: effective price = amountIn / amountOut (USDC per BTC)
        effectivePrice = amountIn / amountOut
        priceImpact = abs(effectivePrice - activePrice) / activePrice
    
    RETURN priceImpact * 100  // Convert to percentage
```

### Key Assumptions for Quote Calculation

1. **No Slippage from Other Trades**: The quote assumes no other swaps occur before the user's swap
2. **Current Bin State**: Uses the current liquidity distribution across all bins
3. **Sequential Processing**: Processes bins in order (active bin first, then left/right)
4. **Constant Sum Within Bins**: Each bin uses constant sum AMM logic
5. **Price Impact**: Calculated as percentage deviation of average execution price from active bin price
6. **Insufficient Liquidity**: Returns partial results if liquidity is exhausted

### Quote Output Format

```
{
    "totalAmountIn": 10.0,           // Input amount
    "totalAmountOut": 499500.0,      // Output amount
    "totalPriceImpact": 0.1,         // Total price impact (%)
    "success": true,                 // Whether quote succeeded
    "steps": [                       // Detailed steps
        {
            "poolId": "BTC-USDC",
            "binId": 500,
            "tokenIn": "BTC",
            "tokenOut": "USDC", 
            "amountIn": 5.0,
            "amountOut": 250000.0,
            "price": 50000.0,
            "priceImpact": 0.05
        },
        {
            "poolId": "BTC-USDC",
            "binId": 501,
            "tokenIn": "BTC",
            "tokenOut": "USDC",
            "amountIn": 5.0,
            "amountOut": 249500.0,
            "price": 49900.0,
            "priceImpact": 0.05
        }
    ]
}
``` 