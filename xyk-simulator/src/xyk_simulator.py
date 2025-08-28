"""
XYK Simulator - Constant Product AMM Price Slippage Analysis

This module implements the mathematical foundation for constant product AMMs
following the X*Y=K formula, with focus on price slippage analysis.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class SlippageResult:
    """Result of a slippage calculation"""
    trade_size: float
    price_before: float
    price_after: float
    price_impact: float
    slippage_percentage: float
    output_amount: float
    input_amount: float


@dataclass
class TVLRequirement:
    """TVL requirement for a specific slippage threshold"""
    trade_size: float
    max_slippage: float
    required_tvl: float
    required_reserve_x: float
    required_reserve_y: float


class XYKSimulator:
    """
    Simulator for constant product AMMs (X*Y=K)
    
    This class implements the mathematical foundation for understanding
    price slippage in Uniswap v2-style AMMs.
    """
    
    def __init__(self, total_value_locked: float, initial_price: float = 1.0):
        """
        Initialize the XYK simulator
        
        Args:
            total_value_locked: Total value locked in the pool (in USD)
            initial_price: Initial price of token Y in terms of token X
        """
        self.total_value_locked = total_value_locked
        self.initial_price = initial_price
        
        # Calculate initial reserves to achieve the desired TVL
        # For simplicity, we'll assume equal value distribution
        # If price = Y/X, then Y = price * X
        # TVL = X + Y = X + price * X = X * (1 + price)
        # So X = TVL / (1 + price)
        
        self.reserve_x = total_value_locked / (1 + initial_price)
        self.reserve_y = self.reserve_x * initial_price
        
        # Calculate the constant K
        self.constant_k = self.reserve_x * self.reserve_y
        
        print(f"Pool initialized:")
        print(f"  TVL: ${total_value_locked:,.2f}")
        print(f"  Reserve X: {self.reserve_x:,.2f}")
        print(f"  Reserve Y: {self.reserve_y:,.2f}")
        print(f"  Initial Price: {initial_price:.4f}")
        print(f"  Constant K: {self.constant_k:,.2f}")
    
    def get_spot_price(self) -> float:
        """Get current spot price (Y/X)"""
        return self.reserve_y / self.reserve_x
    
    def get_tvl(self) -> float:
        """Get current total value locked"""
        return self.reserve_x + self.reserve_y
    
    def calculate_output_for_input(self, input_amount: float, input_is_x: bool = True) -> float:
        """
        Calculate output amount for a given input amount
        
        Args:
            input_amount: Amount of input token
            input_is_x: True if input is token X, False if token Y
            
        Returns:
            Output amount of the other token
        """
        if input_is_x:
            # Swapping X for Y - using Clarity formula: dy = (y * dx) / (x + dx)
            dx = input_amount  # No fees in this implementation
            updated_x_balance = self.reserve_x + dx
            dy = (self.reserve_y * dx) / updated_x_balance
            output_amount = dy
        else:
            # Swapping Y for X - using Clarity formula: dx = (x * dy) / (y + dy)
            dy = input_amount  # No fees in this implementation
            updated_y_balance = self.reserve_y + dy
            dx = (self.reserve_x * dy) / updated_y_balance
            output_amount = dx
        
        return max(0, output_amount)
    
    def calculate_price_impact(self, input_amount: float, input_is_x: bool = True) -> SlippageResult:
        """
        Calculate the price impact of a trade
        
        Args:
            input_amount: Amount of input token
            input_is_x: True if input is token X, False if token Y
            
        Returns:
            SlippageResult with detailed trade information
        """
        price_before = self.get_spot_price()
        
        if input_is_x:
            # Swapping X for Y - using Clarity formula: dy = (y * dx) / (x + dx)
            dx = input_amount  # No fees in this implementation
            updated_x_balance = self.reserve_x + dx
            dy = (self.reserve_y * dx) / updated_x_balance
            
            # Calculate new reserves
            new_reserve_x = updated_x_balance
            new_reserve_y = self.reserve_y - dy
            
            # Calculate new price
            price_after = new_reserve_y / new_reserve_x
            
            # Calculate price impact
            price_impact = price_after - price_before
            slippage_percentage = (price_impact / price_before) * 100
            
            return SlippageResult(
                trade_size=input_amount,
                price_before=price_before,
                price_after=price_after,
                price_impact=price_impact,
                slippage_percentage=slippage_percentage,
                output_amount=dy,
                input_amount=input_amount
            )
        else:
            # Swapping Y for X - using Clarity formula: dx = (x * dy) / (y + dy)
            dy = input_amount  # No fees in this implementation
            updated_y_balance = self.reserve_y + dy
            dx = (self.reserve_x * dy) / updated_y_balance
            
            # Calculate new reserves
            new_reserve_y = updated_y_balance
            new_reserve_x = self.reserve_x - dx
            
            # Calculate new price
            price_after = new_reserve_y / new_reserve_x
            
            # Calculate price impact
            price_impact = price_after - price_before
            slippage_percentage = (price_impact / price_before) * 100
            
            return SlippageResult(
                trade_size=input_amount,
                price_before=price_before,
                price_after=price_after,
                price_impact=price_impact,
                slippage_percentage=slippage_percentage,
                output_amount=dx,
                input_amount=input_amount
            )
    
    def analyze_slippage_range(self, trade_sizes: List[float], input_is_x: bool = True) -> pd.DataFrame:
        """
        Analyze slippage for a range of trade sizes
        
        Args:
            trade_sizes: List of trade sizes to analyze
            input_is_x: True if input is token X, False if token Y
            
        Returns:
            DataFrame with slippage analysis results
        """
        results = []
        
        for trade_size in trade_sizes:
            result = self.calculate_price_impact(trade_size, input_is_x)
            results.append({
                'Trade Size': f"${trade_size:,.0f}",
                'Price Before': f"${result.price_before:.4f}",
                'Price After': f"${result.price_after:.4f}",
                'Price Impact': f"${result.price_impact:.6f}",
                'Slippage %': f"{result.slippage_percentage:.4f}%",
                'Output Amount': f"${result.output_amount:,.2f}",
                'Trade Size % of Pool': f"{(trade_size / self.get_tvl()) * 100:.2f}%"
            })
        
        return pd.DataFrame(results)
    
    def find_tvl_for_slippage(self, trade_size: float, max_slippage: float, 
                             input_is_x: bool = True) -> TVLRequirement:
        """
        Find the minimum TVL required to achieve a target slippage
        
        Args:
            trade_size: Size of the trade
            max_slippage: Maximum allowed slippage (as decimal, e.g., 0.01 for 1%)
            input_is_x: True if input is token X, False if token Y
            
        Returns:
            TVLRequirement with required pool parameters
        """
        # For a given trade size and max slippage, we can calculate required reserves
        # Using the slippage formula: slippage = (ΔX / X) / (1 + ΔX / X)
        # Rearranging: X = ΔX * (1 - slippage) / slippage
        
        if input_is_x:
            # Swapping X for Y
            required_reserve_x = trade_size * (1 - max_slippage) / max_slippage
            required_reserve_y = required_reserve_x * self.initial_price
        else:
            # Swapping Y for X
            required_reserve_y = trade_size * (1 - max_slippage) / max_slippage
            required_reserve_x = required_reserve_y / self.initial_price
        
        required_tvl = required_reserve_x + required_reserve_y
        
        return TVLRequirement(
            trade_size=trade_size,
            max_slippage=max_slippage,
            required_tvl=required_tvl,
            required_reserve_x=required_reserve_x,
            required_reserve_y=required_reserve_y
        )
    
    def reset_pool(self):
        """Reset the pool to initial state"""
        self.reserve_x = self.total_value_locked / (1 + self.initial_price)
        self.reserve_y = self.reserve_x * self.initial_price
        self.constant_k = self.reserve_x * self.reserve_y
        print("Pool reset to initial state")
    
    def get_pool_state(self) -> Dict[str, float]:
        """Get current pool state"""
        return {
            'reserve_x': self.reserve_x,
            'reserve_y': self.reserve_y,
            'spot_price': self.get_spot_price(),
            'tvl': self.get_tvl(),
            'constant_k': self.constant_k
        }
    
    def execute_trade(self, input_amount: float, input_is_x: bool = True) -> SlippageResult:
        """
        Execute a trade and update pool state (like swap-x-for-y in Clarity)
        
        Args:
            input_amount: Amount of input token
            input_is_x: True if input is token X, False if token Y
            
        Returns:
            SlippageResult with trade details
        """
        result = self.calculate_price_impact(input_amount, input_is_x)
        
        # Update pool state
        if input_is_x:
            # Swapping X for Y
            self.reserve_x += input_amount
            self.reserve_y -= result.output_amount
        else:
            # Swapping Y for X
            self.reserve_y += input_amount
            self.reserve_x -= result.output_amount
        
        # Update constant K (should remain the same, but recalculate for precision)
        self.constant_k = self.reserve_x * self.reserve_y
        
        return result
    
    def calculate_lp_tokens(self, x_amount: float, y_amount: float) -> float:
        """
        Calculate LP tokens to mint (Uniswap v2 standard like Clarity)
        Uses sqrt(x * y) formula
        """
        import math
        return math.sqrt(x_amount * y_amount)
