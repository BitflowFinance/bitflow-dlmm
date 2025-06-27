"""
Pool data structures and mock data generation for DLMM simulator.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class BinData:
    """Data structure for a single bin in a pool."""
    bin_id: int
    price: float
    x_amount: float
    y_amount: float
    total_liquidity: float
    is_active: bool = False


@dataclass
class PoolConfig:
    """Configuration for a DLMM pool."""
    active_bin_id: int = 500
    active_price: float = 50000.0  # $50,000 per BTC
    bin_step: float = 0.001        # 0.1% (10 bps) between bins
    num_bins: int = 1001           # 0-1000
    x_token: str = "BTC"
    y_token: str = "USDC"


class MockPool:
    """Mock pool with bell curve liquidity distribution."""
    
    def __init__(self, config: PoolConfig):
        self.config = config
        self.bins: Dict[int, BinData] = {}
        self._generate_liquidity()
    
    @classmethod
    def create_bell_curve_pool(cls, config: Optional[PoolConfig] = None) -> 'MockPool':
        """Create a pool with bell curve liquidity distribution."""
        if config is None:
            config = PoolConfig()
        return cls(config)
    
    def _generate_liquidity(self):
        """Generate mock liquidity data following a bell curve around the active bin."""
        for bin_id in range(self.config.num_bins):
            # Calculate distance from active bin
            distance = abs(bin_id - self.config.active_bin_id)
            
            # Bell curve: peak at active bin, decreasing as we move away
            sigma = 50  # Standard deviation - controls spread of liquidity
            liquidity = math.exp(-(distance ** 2) / (2 * sigma ** 2))
            
            # Scale liquidity to reasonable amounts
            base_liquidity = 1000000  # 1M USDC equivalent
            scaled_liquidity = liquidity * base_liquidity
            
            # Calculate price for this bin
            price = self._calculate_bin_price(bin_id)
            
            # Determine token composition based on bin position
            if bin_id < self.config.active_bin_id:
                # Left bins: only X tokens (BTC)
                x_amount = scaled_liquidity / price
                y_amount = 0
            elif bin_id > self.config.active_bin_id:
                # Right bins: only Y tokens (USDC)
                x_amount = 0
                y_amount = scaled_liquidity
            else:
                # Active bin: both tokens (roughly 50/50 split)
                x_amount = scaled_liquidity / (2 * price)
                y_amount = scaled_liquidity / 2
            
            self.bins[bin_id] = BinData(
                bin_id=bin_id,
                price=price,
                x_amount=x_amount,
                y_amount=y_amount,
                total_liquidity=scaled_liquidity,
                is_active=(bin_id == self.config.active_bin_id)
            )
    
    def _calculate_bin_price(self, bin_id: int) -> float:
        """Calculate the price at a given bin using the formula P_i = P_active * (1 + s)^(i-500)."""
        active_price = self.config.active_price
        bin_step = self.config.bin_step
        active_bin = self.config.active_bin_id
        
        price = active_price * ((1 + bin_step) ** (bin_id - active_bin))
        return price
    
    def get_bin(self, bin_id: int) -> Optional[BinData]:
        """Get bin data by bin ID."""
        return self.bins.get(bin_id)
    
    def get_active_bin(self) -> BinData:
        """Get the active bin data."""
        return self.bins[self.config.active_bin_id]
    
    def get_bin_range(self, start_bin: int, end_bin: int) -> List[BinData]:
        """Get a range of bins."""
        return [self.bins[bin_id] for bin_id in range(start_bin, end_bin + 1) if bin_id in self.bins]
    
    def print_bin_prices(self, start_bin: Optional[int] = None, end_bin: Optional[int] = None):
        """Print bin numbers and their corresponding prices."""
        if start_bin is None:
            start_bin = 0
        if end_bin is None:
            end_bin = self.config.num_bins - 1
        
        print(f"Pool State: {self.config.x_token}/{self.config.y_token}")
        print(f"Active Bin: {self.config.active_bin_id} at ${self.config.active_price:,.2f}")
        print(f"Bin Step: {self.config.bin_step:.3f} ({self.config.bin_step*10000:.0f} bps)")
        print("-" * 80)
        print(f"{'Bin':<6} {'Price (USD)':<15} {'X Amount':<12} {'Y Amount':<12} {'Active':<8}")
        print("-" * 80)
        
        for bin_id in range(start_bin, end_bin + 1):
            if bin_id in self.bins:
                data = self.bins[bin_id]
                active_marker = "✓" if data.is_active else ""
                
                print(f"{bin_id:<6} ${data.price:<14,.2f} {data.x_amount:<11,.2f} {data.y_amount:<11,.2f} {active_marker:<8}")
    
    def print_active_bin_details(self):
        """Print detailed information about the active bin."""
        active_data = self.get_active_bin()
        
        print(f"\n=== Active Bin Details ===")
        print(f"Bin ID: {active_data.bin_id}")
        print(f"Price: ${active_data.price:,.2f}")
        print(f"X Amount ({self.config.x_token}): {active_data.x_amount:,.6f}")
        print(f"Y Amount ({self.config.y_token}): {active_data.y_amount:,.2f}")
        print(f"Total Liquidity: ${active_data.total_liquidity:,.2f}")


if __name__ == "__main__":
    # Example usage
    pool = MockPool.create_bell_curve_pool()
    
    # Print all bins
    pool.print_bin_prices()
    
    # Print active bin details
    pool.print_active_bin_details()
    
    # Print just a range around the active bin
    print(f"\n=== Bins Around Active Bin (495-505) ===")
    pool.print_bin_prices(495, 505) 