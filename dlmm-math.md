# DLMM Mathematical Formulas

## Overview

This document describes the mathematical formulas used in DLMM (Decentralized Liquidity Market Maker) and how they are implemented in the simulator.

## Simulator Implementation

### Key Design Decisions

#### 1. **Simple Float Arithmetic**
- **No 1e18 scaling**: All calculations use human-readable floats
- **Direct price representation**: $50,000 instead of 50000000000000000000000
- **Easy debugging**: Clear, readable values throughout
- **Consistent math**: DLMMMath module handles all calculations

#### 2. **Realistic Market Data**
- **BTC price**: ~$50,000 USDC
- **ETH price**: ~$3,000 USDC  
- **SOL price**: ~$150 USDC
- **Bin steps**: 25, 50, 100 basis points
- **Fee structure**: 10 basis points (0.1%)

#### 3. **Implementation in `src/math.py`**
```python
class DLMMMath:
    @staticmethod
    def calculate_bin_price(active_price: float, bin_step: float, bin_id: int, active_bin_id: int) -> float:
        """Calculate bin price using P_i = P_active * (1 + s)^(i-active_bin_id)"""
        return active_price * ((1 + bin_step) ** (bin_id - active_bin_id))
    
    @staticmethod
    def swap_within_bin(bin_data: BinData, amount_in: float, is_x_to_y: bool) -> Tuple[float, float]:
        """Calculate swap within a single bin (constant sum AMM)"""
        if is_x_to_y:
            # Swapping X for Y: Δy = min(P_i * Δx, y_i)
            max_x_usable = bin_data.y_amount / bin_data.price
            x_to_use = min(amount_in, max_x_usable)
            y_out = x_to_use * bin_data.price
            return y_out, amount_in - x_to_use
        else:
            # Swapping Y for X: Δx = min(Δy / P_i, x_i)
            max_y_usable = bin_data.x_amount * bin_data.price
            y_to_use = min(amount_in, max_y_usable)
            x_out = y_to_use / bin_data.price
            return x_out, amount_in - y_to_use
```

---

## DLMM Variables and Formulas

### Variables
$N$ - Number of bins in the pool  
$P_0$ - Lowest priced bin  
$P_{n-1}$ - Highest priced bin  
$s$ - Bin step (distance between bins, measured in bps)  
$X$ - Token X (BTC)  
$Y$ - Token Y (USDC)  
$P_i$ - Price of the $i$-th bin:
$$
P_i = P_0 \times (1 + s)^i
$$
$x_i$ - Amount of token X in bin $i$  
$y_i$ - Amount of token Y in bin $i$  
$\Delta x_i$ - Amount of token X being added to bin $i$  
$\Delta y_i$ - Amount of token Y being added to bin $i$  
$L_i$ - Liquidity in bin $i$  
$c_i$ - Composition factor in bin $i$ (percentage of bin liquidity composed of $Y$):
$$
c_i = \frac{y_i}{L_i}
$$

### Formulas

#### Price of the $i$-th Bin
$$
P_i = P_0 \times (1 + s)^i
$$

#### Liquidity in Bin $i$
$$
L_i = x_i + \frac{y_i}{P_i}
$$

#### Total TVL Across All Bins (Invariant)
$$
K = \sum_{i=0}^{N-1} \left( x_i + \frac{y_i}{P_i} \right)
$$

#### Change in LP Tokens from Liquidity Added Across Bins
$$
\Delta_{LP} = \sum_{i=0}^{N-1} \left( \Delta x_i + \frac{\Delta y_i}{P_i} \right)
$$

#### Composition Factor and Bin Reserves
$$
c_i = \frac{y_i}{L_i}
$$
$$
y_i = c_i L_i
$$
$$
x_i = \left(1 - c_i\right) \frac{L_i}{P_i}
$$

### Swap Price Quotes

#### Swapping Within a Single Bin

**Swap X for Y (within bin $i$):**
The price is fixed at $P_i$ for all trades within the bin until the bin is depleted.
$$
\text{If you swap } \Delta x \text{ of X, you receive:} \qquad \Delta y = \min\left(P_i \cdot \Delta x,\, y_i\right)
$$

**Swap Y for X (within bin $i$):**
$$
\text{If you swap } \Delta y \text{ of Y, you receive:} \qquad \Delta x = \min\left(\frac{\Delta y}{P_i},\, x_i\right)
$$

#### Swapping Across Multiple Bins

When the swap amount exceeds the available liquidity in the active bin, the swap continues into the next bin(s), each with its own fixed price $P_j$.

**Swap X for Y (across bins):**
For a total input $\Delta x$, the output is the sum of outputs from each bin traversed:
$$
\Delta y_{\text{total}} = \sum_{j} \min\left(P_j \cdot \Delta x_j,\, y_j\right)
$$
where $\Delta x_j$ is the amount of X swapped in bin $j$, and $P_j = P_0 (1 + s)^j$.

**Swap Y for X (across bins):**
$$
\Delta x_{\text{total}} = \sum_{j} \min\left(\frac{\Delta y_j}{P_j},\, x_j\right)
$$
where $\Delta y_j$ is the amount of Y swapped in bin $j$.

### Notes

- All bins except for the active one contain just one type of token (X or Y) because they have been depleted or are waiting to be used. Only the active bin earns trading fees.
- The price $P_i$ is uniform within each bin and does not depend on the reserve amounts.
- The composition of reserves, $x$ and $y$, are independent of both price and liquidity. The composition factor $c$ describes the percentage of bin liquidity in $y$.

## Simulator vs Contract Implementation

### Simulator (Python)
- **Float arithmetic**: Direct calculations with human-readable values
- **No scaling**: Prices and amounts stored as floats
- **Easy debugging**: Clear, readable output
- **Fast development**: Quick iteration and testing

### Contract (Clarity)
- **Integer arithmetic**: All values scaled by 1e18 for precision
- **Fixed-point math**: Avoids floating-point precision issues
- **Gas optimization**: Efficient integer operations
- **Production ready**: Handles real token amounts

### Conversion Between Formats
```python
# Simulator to Contract
contract_amount = int(simulator_amount * 1e18)

# Contract to Simulator  
simulator_amount = contract_amount / 1e18
```