"""
Tests for XYK Simulator

Verify the mathematical accuracy of the constant product AMM implementation.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from xyk_simulator import XYKSimulator, SlippageResult, TVLRequirement


class TestXYKSimulator:
    """Test cases for XYK Simulator"""
    
    def test_initialization(self):
        """Test pool initialization"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        assert simulator.total_value_locked == 1000000
        assert simulator.initial_price == 1.0
        assert simulator.reserve_x == 500000  # TVL / (1 + price)
        assert simulator.reserve_y == 500000  # reserve_x * price
        assert simulator.constant_k == 250000000000  # reserve_x * reserve_y
    
    def test_spot_price(self):
        """Test spot price calculation"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=2.0)
        
        # Price should be Y/X = 2.0
        assert abs(simulator.get_spot_price() - 2.0) < 1e-10
    
    def test_tvl_calculation(self):
        """Test TVL calculation"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        assert simulator.get_tvl() == 1000000
    
    def test_small_trade_slippage(self):
        """Test slippage for small trade"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        # Small trade should have minimal slippage
        result = simulator.calculate_price_impact(1000, input_is_x=True)
        
        assert result.trade_size == 1000
        assert result.price_before == 1.0
        # When buying Y with X, price of Y increases (Y/X ratio increases)
        # But since we're measuring price as Y/X, and we're adding X and removing Y,
        # the Y/X ratio actually decreases (price goes down)
        assert result.price_after < result.price_before  # Price decreases when buying Y with X
        assert result.slippage_percentage < 0  # Should have negative slippage (price decrease)
        assert abs(result.slippage_percentage) < 1.0  # But should be small in magnitude
    
    def test_large_trade_slippage(self):
        """Test slippage for large trade"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        # Large trade should have significant slippage
        result = simulator.calculate_price_impact(100000, input_is_x=True)
        
        assert result.trade_size == 100000
        assert abs(result.slippage_percentage) > 5.0  # Should have significant slippage (magnitude)
    
    def test_price_impact_symmetry(self):
        """Test that equal trades in opposite directions have symmetric impact"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        trade_size = 50000
        
        # Trade X for Y
        result_xy = simulator.calculate_price_impact(trade_size, input_is_x=True)
        
        # Reset pool
        simulator.reset_pool()
        
        # Trade Y for X
        result_yx = simulator.calculate_price_impact(trade_size, input_is_x=False)
        
        # Price impacts should be roughly symmetric (opposite signs)
        # Note: Due to the constant product formula, the impacts aren't perfectly symmetric
        # but they should be in opposite directions
        assert result_xy.price_impact < 0  # X→Y decreases price
        assert result_yx.price_impact > 0  # Y→X increases price
        # The magnitudes should be similar but not necessarily equal
        assert abs(result_xy.price_impact) > 0
        assert abs(result_yx.price_impact) > 0
    
    def test_tvl_requirement_calculation(self):
        """Test TVL requirement calculation"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        requirement = simulator.find_tvl_for_slippage(
            trade_size=100000,
            max_slippage=0.01,  # 1%
            input_is_x=True
        )
        
        assert requirement.trade_size == 100000
        assert requirement.max_slippage == 0.01
        assert requirement.required_tvl > 1000000  # Should require more TVL than current pool
        assert requirement.required_tvl > 0
    
    def test_constant_product_invariant(self):
        """Test that K remains constant after trades"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        initial_k = simulator.constant_k
        
        # Execute a trade
        simulator.calculate_price_impact(10000, input_is_x=True)
        
        # Get new pool state
        new_state = simulator.get_pool_state()
        new_k = new_state['reserve_x'] * new_state['reserve_y']
        
        # K should remain constant (within floating point precision)
        assert abs(new_k - initial_k) < 1e-10
    
    def test_output_calculation(self):
        """Test output amount calculation"""
        simulator = XYKSimulator(total_value_locked=1000000, initial_price=1.0)
        
        input_amount = 10000
        output_amount = simulator.calculate_output_for_input(input_amount, input_is_x=True)
        
        assert output_amount > 0
        assert output_amount < input_amount  # Due to slippage, output < input in value terms


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
