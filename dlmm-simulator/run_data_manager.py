#!/usr/bin/env python3
"""
Data Manager Runner
Runs the DataManager in the foreground to keep it alive.
"""

import sys
import os
import time
import signal
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.redis import RedisConfig, create_redis_client, DataManager

def signal_handler(signum, frame):
    print("\n🛑 Shutting down Data Manager...")
    sys.exit(0)

def main():
    print("🚀 Starting Data Manager...")
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create Redis client
        config = RedisConfig(host="localhost", port=6379, ssl=False)
        redis_client = create_redis_client(config, fallback_to_mock=False)
        
        if not redis_client.ping():
            print("❌ Cannot connect to Redis")
            sys.exit(1)
        
        print("✅ Connected to Redis")
        
        # Create and start data manager
        data_manager = DataManager(redis_client, update_interval=5)
        
        # Populate initial data if needed
        print("🗃️  Checking if data exists...")
        metadata = data_manager.get_metadata()
        if not metadata:
            print("📊 Populating initial data...")
            data_manager.populate_initial_data()
            print("✅ Initial data populated")
        else:
            print(f"✅ Data already exists: {metadata.total_pools} pools, {metadata.total_bins} bins")
        
        # Start the data manager
        print("🔄 Starting data manager with 5-second updates...")
        data_manager.start()
        
        print("✅ Data Manager is running! Press Ctrl+C to stop.")
        
        # Keep the process alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 