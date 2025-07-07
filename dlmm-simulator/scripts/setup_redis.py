#!/usr/bin/env python3
"""
Redis Setup Script for DLMM Quote Engine
Initializes Redis and populates it with initial data.
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.redis import RedisConfig, create_redis_client, DataManager
from src.quote_engine import QuoteEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_redis():
    """Set up Redis and populate with initial data"""
    
    print("🚀 Setting up Redis for DLMM Quote Engine")
    print("=" * 50)
    
    # Create Redis configuration
    config = RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        max_connections=10,
        socket_timeout=5.0,
        socket_connect_timeout=5.0
    )
    
    try:
        # Create Redis client
        print("📡 Connecting to Redis...")
        redis_client = create_redis_client(config, fallback_to_mock=False)
        
        # Test connection
        if redis_client.ping():
            print("✅ Redis connection successful")
        else:
            print("❌ Redis connection failed")
            return False
        
        # Get Redis info
        health_info = redis_client.health_check()
        print(f"📊 Redis Info:")
        print(f"   Version: {health_info.get('redis_version', 'unknown')}")
        print(f"   Memory: {health_info.get('used_memory_human', 'unknown')}")
        print(f"   Connected clients: {health_info.get('connected_clients', 0)}")
        print(f"   Uptime: {health_info.get('uptime_in_seconds', 0)} seconds")
        
        # Create data manager
        print("\n📊 Creating data manager...")
        data_manager = DataManager(redis_client, update_interval=5)
        
        # Populate initial data
        print("🗃️  Populating initial data...")
        data_manager.populate_initial_data()
        
        # Verify data population
        print("🔍 Verifying data population...")
        metadata = data_manager.get_metadata()
        if metadata:
            print(f"✅ Data populated successfully:")
            print(f"   Total pools: {metadata.total_pools}")
            print(f"   Total tokens: {metadata.total_tokens}")
            print(f"   Total bins: {metadata.total_bins}")
            print(f"   Last update: {metadata.last_update}")
        else:
            print("❌ Failed to get metadata")
            return False
        
        # Test quote engine with Redis
        print("\n🧪 Testing quote engine with Redis...")
        quote_engine = QuoteEngine(redis_client)
        
        # Test a simple quote
        quote = quote_engine.get_quote("BTC", "USDC", 1.0)
        if quote.success:
            print(f"✅ Quote engine test successful: 1 BTC → {quote.amount_out:.2f} USDC")
        else:
            print(f"❌ Quote engine test failed: {quote.error}")
            return False
        
        # Start data manager
        print("\n🔄 Starting data manager...")
        data_manager.start()
        
        print("\n🎉 Redis setup completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Redis is running on localhost:6379")
        print("   2. Redis Commander is available at http://localhost:8081")
        print("   3. Data manager is running with 5-second updates")
        print("   4. Quote engine is ready to use with Redis")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis setup failed: {e}")
        logger.error(f"Redis setup error: {e}")
        return False


def check_redis_status():
    """Check Redis status"""
    
    print("🔍 Checking Redis status...")
    
    config = RedisConfig()
    
    try:
        redis_client = create_redis_client(config, fallback_to_mock=False)
        
        if redis_client.ping():
            health_info = redis_client.health_check()
            print("✅ Redis is running")
            print(f"   Version: {health_info.get('redis_version', 'unknown')}")
            print(f"   Memory: {health_info.get('used_memory_human', 'unknown')}")
            print(f"   Connected clients: {health_info.get('connected_clients', 0)}")
            
            # Check if data exists
            metadata_key = "metadata"
            metadata = redis_client.get(metadata_key)
            if metadata:
                print("✅ Data is populated")
            else:
                print("⚠️  No data found - run setup to populate")
            
            return True
        else:
            print("❌ Redis is not responding")
            return False
            
    except Exception as e:
        print(f"❌ Redis check failed: {e}")
        return False


def main():
    """Main function"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            success = setup_redis()
            sys.exit(0 if success else 1)
            
        elif command == "status":
            success = check_redis_status()
            sys.exit(0 if success else 1)
            
        elif command == "help":
            print("DLMM Redis Setup Script")
            print("=" * 30)
            print("Usage:")
            print("  python setup_redis.py setup    - Set up Redis and populate data")
            print("  python setup_redis.py status   - Check Redis status")
            print("  python setup_redis.py help     - Show this help")
            sys.exit(0)
            
        else:
            print(f"Unknown command: {command}")
            print("Use 'python setup_redis.py help' for usage information")
            sys.exit(1)
    
    else:
        # Default to setup
        success = setup_redis()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 