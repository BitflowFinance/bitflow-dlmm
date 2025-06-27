"""
Tests for the pool module.
"""

import pytest
from src.pool import MockPool, PoolConfig, BinData


class TestPoolConfig:
    """Test PoolConfig class."""
    
    def test_default_config(self):
        """Test default pool configuration."""
        config = PoolConfig()
        assert config.active_bin_id == 500
        assert config.active_price == 50000.0
        assert config.bin_step == 0.001
        assert config.num_bins == 1001
        assert config.x_token == "BTC"
        assert config.y_token == "USDC"
    
    def test_custom_config(self):
        """Test custom pool configuration."""
        config = PoolConfig(
            active_bin_id=400,
            active_price=1000.0,
            bin_step=0.002,
            x_token="ETH",
            y_token="USDT"
        )
        assert config.active_bin_id == 400
        assert config.active_price == 1000.0
        assert config.bin_step == 0.002
        assert config.x_token == "ETH"
        assert config.y_token == "USDT"


class TestMockPool:
    """Test MockPool class."""
    
    def test_create_bell_curve_pool(self):
        """Test creating a pool with bell curve liquidity."""
        pool = MockPool.create_bell_curve_pool()
        assert pool.config.active_bin_id == 500
        assert len(pool.bins) == 1001
        
        # Check that active bin exists
        active_bin = pool.get_active_bin()
        assert active_bin.bin_id == 500
        assert active_bin.is_active == True
    
    def test_bin_price_calculation(self):
        """Test bin price calculation."""
        pool = MockPool.create_bell_curve_pool()
        
        # Test active bin price
        active_bin = pool.get_active_bin()
        assert abs(active_bin.price - 50000.0) < 0.01
        
        # Test left bin (lower price)
        left_bin = pool.get_bin(499)
        assert left_bin.price < active_bin.price
        
        # Test right bin (higher price)
        right_bin = pool.get_bin(501)
        assert right_bin.price > active_bin.price
    
    def test_liquidity_distribution(self):
        """Test that liquidity follows expected distribution."""
        pool = MockPool.create_bell_curve_pool()
        
        # Active bin should have both tokens
        active_bin = pool.get_active_bin()
        assert active_bin.x_amount > 0
        assert active_bin.y_amount > 0
        
        # Left bins should have only Y tokens
        left_bin = pool.get_bin(499)
        assert left_bin.x_amount == 0
        assert left_bin.y_amount > 0
        
        # Right bins should have only X tokens
        right_bin = pool.get_bin(501)
        assert right_bin.x_amount > 0
        assert right_bin.y_amount == 0
    
    def test_get_bin_range(self):
        """Test getting a range of bins."""
        pool = MockPool.create_bell_curve_pool()
        
        # Get range around active bin
        bins = pool.get_bin_range(498, 502)
        assert len(bins) == 5
        
        # Check bin IDs are correct
        bin_ids = [bin_data.bin_id for bin_data in bins]
        assert bin_ids == [498, 499, 500, 501, 502]
    
    def test_custom_pool_config(self):
        """Test creating pool with custom configuration."""
        config = PoolConfig(
            active_bin_id=400,
            active_price=1000.0,
            bin_step=0.002,
            x_token="ETH",
            y_token="USDT"
        )
        pool = MockPool(config)
        
        assert pool.config.active_bin_id == 400
        assert pool.config.active_price == 1000.0
        assert pool.config.x_token == "ETH"
        assert pool.config.y_token == "USDT"
        
        # Check active bin
        active_bin = pool.get_active_bin()
        assert active_bin.bin_id == 400
        assert abs(active_bin.price - 1000.0) < 0.01


class TestBinData:
    """Test BinData class."""
    
    def test_bin_data_creation(self):
        """Test creating BinData."""
        bin_data = BinData(
            bin_id=500,
            price=50000.0,
            x_amount=10.0,
            y_amount=500000.0,
            total_liquidity=1000000.0,
            is_active=True
        )
        
        assert bin_data.bin_id == 500
        assert bin_data.price == 50000.0
        assert bin_data.x_amount == 10.0
        assert bin_data.y_amount == 500000.0
        assert bin_data.total_liquidity == 1000000.0
        assert bin_data.is_active == True 