"""
Integration tests for Redis integration
Tests the complete Redis integration with quote engine.
"""

import sys
import os
import time
import json
import pytest
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.redis import RedisConfig, create_redis_client, DataManager
from src.quote_engine import QuoteEngine


class TestRedisIntegration:
    """Test Redis integration with quote engine"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment"""
        self.config = RedisConfig(
            host="localhost",
            port=6379,
            db=0,
            fallback_to_mock=True  # Use mock if Redis not available
        )
        
        try:
            self.redis_client = create_redis_client(self.config, fallback_to_mock=True)
            self.data_manager = DataManager(self.redis_client, update_interval=1)
            self.quote_engine = QuoteEngine(self.redis_client)
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
    
    def test_redis_connection(self):
        """Test Redis connection"""
        assert self.redis_client.ping()
        
        # Test health check
        health_info = self.redis_client.health_check()
        assert "connected" in health_info
        assert health_info["connected"] is True
    
    def test_data_population(self):
        """Test data population in Redis"""
        # Populate initial data
        self.data_manager.populate_initial_data()
        
        # Check metadata
        metadata = self.data_manager.get_metadata()
        assert metadata is not None
        assert metadata.total_pools > 0
        assert metadata.total_bins > 0
        
        # Check pool data
        pool_data = self.data_manager.get_pool_data("BTC-USDC-25")
        assert pool_data is not None
        assert pool_data["pool_id"] == "BTC-USDC-25"
        assert pool_data["token_x"] == "BTC"
        assert pool_data["token_y"] == "USDC"
        
        # Check bin data
        bins = self.data_manager.get_pool_bins("BTC-USDC-25")
        assert len(bins) > 0
        
        # Check specific bin
        bin_500 = bins.get(500)
        assert bin_500 is not None
        assert bin_500["pool_id"] == "BTC-USDC-25"
        assert bin_500["bin_id"] == 500
    
    def test_quote_engine_with_redis(self):
        """Test quote engine with Redis data"""
        # Populate data first
        self.data_manager.populate_initial_data()
        
        # Test simple quote
        quote = self.quote_engine.get_quote("BTC", "USDC", 1.0)
        assert quote.success
        assert quote.amount_out > 0
        assert quote.token_in == "BTC"
        assert quote.token_out == "USDC"
        assert quote.amount_in == 1.0
        
        # Test SOL quote
        quote = self.quote_engine.get_quote("SOL", "USDC", 100.0)
        assert quote.success
        assert quote.amount_out > 0
        assert quote.token_in == "SOL"
        assert quote.token_out == "USDC"
    
    def test_data_update_simulation(self):
        """Test data update simulation"""
        # Populate initial data
        self.data_manager.populate_initial_data()
        
        # Get initial active bin
        pool_data = self.data_manager.get_pool_data("BTC-USDC-25")
        initial_active_bin = pool_data["active_bin_id"]
        
        # Simulate data update
        self.data_manager._simulate_active_bin_movement("BTC-USDC-25")
        
        # Check if active bin changed
        updated_pool_data = self.data_manager.get_pool_data("BTC-USDC-25")
        new_active_bin = updated_pool_data["active_bin_id"]
        
        # Active bin should have moved
        assert new_active_bin != initial_active_bin
        
        # Quote should still work
        quote = self.quote_engine.get_quote("BTC", "USDC", 1.0)
        assert quote.success
    
    def test_cache_strategy(self):
        """Test cache strategy implementation"""
        # Populate data
        self.data_manager.populate_initial_data()
        
        # Test that bin data is always fetched from Redis
        # (no caching of bin data)
        bins1 = self.data_manager.get_pool_bins("BTC-USDC-25")
        bins2 = self.data_manager.get_pool_bins("BTC-USDC-25")
        
        # Both calls should return the same data (from Redis)
        assert len(bins1) == len(bins2)
        
        # Test graph cache (should be cached)
        # This is tested implicitly through quote performance
        start_time = time.time()
        quote1 = self.quote_engine.get_quote("BTC", "USDC", 1.0)
        time1 = time.time() - start_time
        
        start_time = time.time()
        quote2 = self.quote_engine.get_quote("BTC", "USDC", 1.0)
        time2 = time.time() - start_time
        
        # Second quote should be faster due to graph cache
        assert time2 <= time1
        assert quote1.success and quote2.success
    
    def test_error_handling(self):
        """Test error handling"""
        # Test with non-existent pool
        quote = self.quote_engine.get_quote("INVALID", "USDC", 1.0)
        assert not quote.success
        assert "No routes found" in quote.error
        
        # Test with non-existent bin
        bins = self.data_manager.get_pool_bins("NONEXISTENT-POOL")
        assert len(bins) == 0
    
    def test_performance(self):
        """Test performance characteristics"""
        # Populate data
        self.data_manager.populate_initial_data()
        
        # Test quote performance
        start_time = time.time()
        for _ in range(10):
            quote = self.quote_engine.get_quote("BTC", "USDC", 1.0)
            assert quote.success
        
        total_time = time.time() - start_time
        avg_time = total_time / 10
        
        # Average quote time should be reasonable (< 100ms)
        assert avg_time < 0.1, f"Average quote time {avg_time:.3f}s is too slow"
        
        print(f"Average quote time: {avg_time*1000:.2f}ms")
    
    def test_concurrent_access(self):
        """Test concurrent access to Redis"""
        import threading
        
        # Populate data
        self.data_manager.populate_initial_data()
        
        results = []
        errors = []
        
        def quote_worker():
            try:
                quote = self.quote_engine.get_quote("BTC", "USDC", 1.0)
                results.append(quote.success)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=quote_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors in concurrent access: {errors}"
        assert len(results) == 5
        assert all(results), "Some quotes failed in concurrent access"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 