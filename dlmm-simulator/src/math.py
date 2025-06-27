"""
Mathematical formulas and calculations for DLMM.
"""

import math
from typing import Tuple, Optional
from .pool import BinData


class DLMMMath:
    """
    Mathematical operations for DLMM calculations.
    
    This class implements the constant sum AMM (Automated Market Maker) logic for DLMM:
    
    Key Concepts:
    - Each bin has a fixed price P_i
    - Within a bin, swaps use constant sum: total liquidity value remains constant
    - X→Y swaps: Δy = min(P_i * Δx, y_i) - swap input X for output Y at bin price
    - Y→X swaps: Δx = min(Δy / P_i, x_i) - swap input Y for output X at bin price
    
    Bin Distribution:
    - Left bins (lower indices): contain X tokens
    - Right bins (higher indices): contain Y tokens  
    - Active bin: contains both X and Y tokens
    
    Traversal Logic:
    - X→Y swaps: traverse right (higher bin IDs) to find more Y tokens
    - Y→X swaps: traverse left (lower bin IDs) to find more X tokens
    """
    
    @staticmethod
    def calculate_bin_price(active_price: float, bin_step: float, bin_id: int, active_bin_id: int) -> float:
        """
        Calculate the price at a given bin using the formula P_i = P_active * (1 + s)^(i-500).
        
        Args:
            active_price: Price at the active bin
            bin_step: Distance between bins in bps
            bin_id: Target bin ID
            active_bin_id: Active bin ID (usually 500)
        
        Returns:
            Price at the target bin
        """
        return active_price * ((1 + bin_step) ** (bin_id - active_bin_id))
    
    @staticmethod
    def calculate_bin_liquidity(x_amount: float, y_amount: float, price: float) -> float:
        """
        Calculate liquidity in a bin using the formula L_i = x_i + y_i/P_i.
        
        Args:
            x_amount: Amount of token X in the bin
            y_amount: Amount of token Y in the bin
            price: Price at this bin
        
        Returns:
            Total liquidity in the bin
        """
        return x_amount + (y_amount / price)
    
    @staticmethod
    def calculate_composition_factor(y_amount: float, total_liquidity: float) -> float:
        """
        Calculate composition factor: percentage of bin liquidity composed of Y.
        
        Args:
            y_amount: Amount of token Y in the bin
            total_liquidity: Total liquidity in the bin
        
        Returns:
            Composition factor (0 to 1)
        """
        if total_liquidity == 0:
            return 0
        return y_amount / total_liquidity
    
    @staticmethod
    def swap_within_bin(bin_data: BinData, amount_in: float, is_x_to_y: bool) -> Tuple[float, float]:
        """
        Calculate swap within a single bin (constant sum AMM).
        
        Args:
            bin_data: Data for the bin
            amount_in: Amount of input token
            is_x_to_y: True if swapping X for Y, False if Y for X
        
        Returns:
            Tuple of (amount_out, remaining_amount_in)
        """
        if is_x_to_y:
            # Swapping X for Y: Δy = min(P_i * Δx, y_i)
            # In right bins, X in bin may be zero, but you can still swap input X for Y up to y_amount
            if bin_data.y_amount == 0:
                return 0, amount_in
            # Max X you can use in this bin is y_amount / price
            max_x_usable = bin_data.y_amount / bin_data.price
            x_to_use = min(amount_in, max_x_usable)
            y_out = x_to_use * bin_data.price
            remaining_amount = amount_in - x_to_use
            return y_out, remaining_amount
        else:
            # Swapping Y for X: Δx = min(Δy / P_i, x_i)
            # In left bins, Y in bin may be zero, but you can still swap input Y for X up to x_amount
            if bin_data.x_amount == 0:
                return 0, amount_in
            max_y_usable = bin_data.x_amount * bin_data.price
            y_to_use = min(amount_in, max_y_usable)
            x_out = y_to_use / bin_data.price
            remaining_amount = amount_in - y_to_use
            return x_out, remaining_amount
    
    @staticmethod
    def calculate_price_impact(amount_in: float, amount_out: float, is_x_to_y: bool, active_price: float) -> float:
        """
        Calculate price impact of a swap.
        
        Args:
            amount_in: Amount of input token
            amount_out: Amount of output token
            is_x_to_y: True if swapping X for Y, False if Y for X
            active_price: Current active bin price
        
        Returns:
            Price impact as a percentage
        """
        if amount_in == 0 or amount_out == 0:
            return 0
        
        if is_x_to_y:
            # X to Y: effective price = amount_out / amount_in
            effective_price = amount_out / amount_in
            price_impact = abs(effective_price - active_price) / active_price
        else:
            # Y to X: effective price = amount_in / amount_out
            effective_price = amount_in / amount_out
            price_impact = abs(effective_price - active_price) / active_price
        
        return price_impact * 100  # Convert to percentage
    
    @staticmethod
    def calculate_slippage(amount_in: float, amount_out: float, expected_amount_out: float) -> float:
        """
        Calculate slippage as percentage difference between expected and actual output.
        
        Args:
            amount_in: Amount of input token
            amount_out: Actual amount of output token received
            expected_amount_out: Expected amount of output token
        
        Returns:
            Slippage as a percentage
        """
        if expected_amount_out == 0:
            return 0
        
        slippage = abs(expected_amount_out - amount_out) / expected_amount_out
        return slippage * 100  # Convert to percentage
    
    @staticmethod
    def calculate_tvl(pool_bins: dict) -> float:
        """
        Calculate Total Value Locked (TVL) across all bins.
        
        Args:
            pool_bins: Dictionary of bin_id -> BinData
        
        Returns:
            Total TVL in USD
        """
        tvl = 0
        for bin_data in pool_bins.values():
            # Calculate value of X tokens in USD
            x_value = bin_data.x_amount * bin_data.price
            # Y tokens are already in USD (assuming USDC)
            y_value = bin_data.y_amount
            tvl += x_value + y_value
        
        return tvl
    
    @staticmethod
    def calculate_bin_distribution(pool_bins: dict, active_bin_id: int) -> dict:
        """
        Calculate distribution of liquidity across bins.
        
        Args:
            pool_bins: Dictionary of bin_id -> BinData
            active_bin_id: ID of the active bin
        
        Returns:
            Dictionary with distribution statistics
        """
        left_bins = []
        right_bins = []
        active_bin = None
        
        for bin_data in pool_bins.values():
            if bin_data.bin_id < active_bin_id:
                left_bins.append(bin_data)
            elif bin_data.bin_id > active_bin_id:
                right_bins.append(bin_data)
            else:
                active_bin = bin_data
        
        # Calculate total liquidity in each region
        left_liquidity = sum(bin.total_liquidity for bin in left_bins)
        right_liquidity = sum(bin.total_liquidity for bin in right_bins)
        active_liquidity = active_bin.total_liquidity if active_bin else 0
        total_liquidity = left_liquidity + right_liquidity + active_liquidity
        
        return {
            'left_bins_count': len(left_bins),
            'right_bins_count': len(right_bins),
            'left_liquidity': left_liquidity,
            'right_liquidity': right_liquidity,
            'active_liquidity': active_liquidity,
            'total_liquidity': total_liquidity,
            'left_percentage': (left_liquidity / total_liquidity * 100) if total_liquidity > 0 else 0,
            'right_percentage': (right_liquidity / total_liquidity * 100) if total_liquidity > 0 else 0,
            'active_percentage': (active_liquidity / total_liquidity * 100) if total_liquidity > 0 else 0
        } 