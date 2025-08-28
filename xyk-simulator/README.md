# XYK Simulator - Price Slippage Analysis

## Overview

The XYK Simulator is a tool for understanding price slippage in constant product AMMs (Automated Market Makers) that follow the X*Y=K formula, such as Uniswap v2.

## Purpose

This simulator helps analyze the relationship between:
- **Trade size** and **price impact**
- **Liquidity depth** and **slippage tolerance**
- **TVL requirements** for specific slippage thresholds

## Key Features

- **Constant Product AMM Math**: Implements X*Y=K formula with zero fees
- **Slippage Calculator**: Analyzes price impact for various trade sizes
- **TVL Analysis**: Determines liquidity requirements for target slippage
- **Visualization**: Charts and tables showing slippage relationships

## Mathematical Foundation

### Constant Product Formula
The core AMM formula is: `X * Y = K`

Where:
- `X` = Reserve of token X
- `Y` = Reserve of token Y  
- `K` = Constant product (invariant)

### Price Calculation
- **Spot Price**: `P = Y / X`
- **Price Impact**: Change in price after a trade
- **Slippage**: Percentage price change due to trade

### Trade Execution (Uniswap v2 / Clarity Standard)
When swapping ΔX for ΔY:
1. **Quote Formula**: `ΔY = (Y * ΔX) / (X + ΔX)`
2. **New reserves**: `X' = X + ΔX`, `Y' = Y - ΔY`
3. **Constant maintained**: `X' * Y' = K`

### LP Token Calculation
- **Initial LP tokens**: `sqrt(X * Y)` (Uniswap v2 standard)
- **Used for**: Pool creation and liquidity provision

## Usage

### Basic Slippage Analysis
```python
from src.xyk_simulator import XYKSimulator

# Create simulator with $1M TVL pool
simulator = XYKSimulator(total_value_locked=1_000_000)

# Analyze slippage for different trade sizes
results = simulator.analyze_slippage_range(
    trade_sizes=[1000, 10000, 100000, 1000000]
)
```

### TVL Requirements
```python
# Find TVL needed for <1% slippage on $100K trade
required_tvl = simulator.find_tvl_for_slippage(
    trade_size=100_000,
    max_slippage=0.01
)
```

## Installation

```bash
cd xyk-simulator
pip install -r requirements.txt
```

## Running the Simulator

```bash
# Run slippage analysis
python src/main.py

# Run with Streamlit interface
streamlit run src/app.py
```

## Key Insights

- **Slippage increases exponentially** with trade size relative to pool size
- **Larger pools** provide better slippage protection for big trades
- **Price impact** is symmetric for equal-sized trades in opposite directions
- **Optimal trade sizing** balances execution cost vs. slippage impact
