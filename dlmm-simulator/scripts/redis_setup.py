#!/usr/bin/env python3
"""
Redis Setup and Testing Script for DLMM Quote Engine
Provides easy commands for Redis setup, data population, and testing.
"""

import sys
import subprocess
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.redis import RedisConfig, create_redis_client
from src.quote_engine import MockRedisClient


def check_redis_running():
    """Check if Redis is running"""
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        return result.stdout.strip() == 'PONG'
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_redis():
    """Start Redis service"""
    print("🚀 Starting Redis...")
    try:
        # Try Homebrew services first
        result = subprocess.run(['brew', 'services', 'start', 'redis'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Redis started via Homebrew services")
            return True
    except FileNotFoundError:
        pass
    
    try:
        # Try systemctl
        result = subprocess.run(['sudo', 'systemctl', 'start', 'redis'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Redis started via systemctl")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Could not start Redis automatically")
    print("   Please start Redis manually:")
    print("   - macOS: brew services start redis")
    print("   - Linux: sudo systemctl start redis")
    print("   - Manual: redis-server")
    return False


def populate_redis_data():
    """Populate Redis with sample data"""
    print("📦 Populating Redis with sample data...")
    
    try:
        # Create Redis client
        config = RedisConfig(host='localhost', port=6379, ssl=False)
        client = create_redis_client(config)
        
        # Create mock client with sample data
        mock_client = MockRedisClient()
        
        # Copy sample data to Redis
        count = 0
        for key in mock_client.keys('*'):
            value = mock_client.get(key)
            if value:
                client.set(key, value)
                count += 1
                if count <= 5:  # Show first 5 keys
                    print(f"  ✅ {key}")
                elif count == 6:
                    print("  ...")
        
        print(f"🎉 Sample data copied! Total keys: {len(client.keys('*'))}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to populate Redis: {e}")
        return False


def test_redis_connection():
    """Test Redis connection and health"""
    print("🧪 Testing Redis connection...")
    
    try:
        config = RedisConfig(host='localhost', port=6379, ssl=False)
        client = create_redis_client(config)
        
        ping_result = client.ping()
        health = client.health_check()
        
        print(f"✅ Redis connection: {ping_result}")
        print(f"✅ Health check: {json.dumps(health, indent=2)}")
        
        if 'fallback' in health:
            print("⚠️  Using MockRedisClient fallback")
            return False
        else:
            print("🚀 Using real Redis instance")
            return True
            
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def test_quote_engine():
    """Test quote engine with Redis"""
    print("🧪 Testing quote engine with Redis...")
    
    try:
        from src.quote_engine import QuoteEngine
        
        config = RedisConfig(host='localhost', port=6379, ssl=False)
        client = create_redis_client(config)
        engine = QuoteEngine(client)
        
        quote = engine.get_quote('BTC', 'USDC', 1.0)
        
        print(f"✅ Quote engine test:")
        print(f"   Success: {quote.success}")
        print(f"   Amount Out: {quote.amount_out}")
        print(f"   Route Type: {quote.route_type.value}")
        
        return quote.success
        
    except Exception as e:
        print(f"❌ Quote engine test failed: {e}")
        return False


def test_api_server():
    """Test API server with Redis"""
    print("🧪 Testing API server with Redis...")
    
    try:
        import requests
        
        response = requests.post(
            'http://localhost:8000/quote',
            json={'token_in': 'BTC', 'token_out': 'USDC', 'amount_in': 1.0},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API server test:")
            print(f"   Success: {data['success']}")
            print(f"   Amount Out: {data['amount_out']}")
            print(f"   Route Type: {data['route_type']}")
            return data['success']
        else:
            print(f"❌ API server returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ API server not running (start with: python3 api_server.py)")
        return False
    except Exception as e:
        print(f"❌ API server test failed: {e}")
        return False


def show_redis_data():
    """Show Redis data statistics"""
    print("📊 Redis data statistics...")
    
    try:
        config = RedisConfig(host='localhost', port=6379, ssl=False)
        client = create_redis_client(config)
        
        # Get all keys
        all_keys = client.keys('*')
        pool_keys = client.keys('pool:*')
        bin_keys = client.keys('bin:*')
        pair_keys = client.keys('pairs:*')
        
        print(f"✅ Total keys: {len(all_keys)}")
        print(f"✅ Pool keys: {len(pool_keys)}")
        print(f"✅ Bin keys: {len(bin_keys)}")
        print(f"✅ Pair keys: {len(pair_keys)}")
        
        # Show sample pool data
        if pool_keys:
            sample_pool = client.get(pool_keys[0])
            if sample_pool:
                pool_data = json.loads(sample_pool)
                print(f"✅ Sample pool: {pool_data['pool_id']} ({pool_data['token_x']}-{pool_data['token_y']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to get Redis data: {e}")
        return False


def monitor_redis():
    """Monitor Redis commands in real-time"""
    print("👀 Starting Redis monitor...")
    print("   Press Ctrl+C to stop monitoring")
    
    try:
        subprocess.run(['redis-cli', 'monitor'])
    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped")
    except Exception as e:
        print(f"❌ Failed to start monitor: {e}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("DLMM Redis Setup and Testing Script")
        print()
        print("Usage:")
        print("  python3 scripts/redis_setup.py <command>")
        print()
        print("Commands:")
        print("  check     - Check if Redis is running")
        print("  start     - Start Redis service")
        print("  populate  - Populate Redis with sample data")
        print("  test      - Test Redis connection and quote engine")
        print("  data      - Show Redis data statistics")
        print("  monitor   - Monitor Redis commands in real-time")
        print("  setup     - Complete setup (start + populate + test)")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'check':
        if check_redis_running():
            print("✅ Redis is running")
        else:
            print("❌ Redis is not running")
    
    elif command == 'start':
        if not check_redis_running():
            start_redis()
        else:
            print("✅ Redis is already running")
    
    elif command == 'populate':
        if check_redis_running():
            populate_redis_data()
        else:
            print("❌ Redis is not running. Start it first with: python3 scripts/redis_setup.py start")
    
    elif command == 'test':
        if check_redis_running():
            test_redis_connection()
            print()
            test_quote_engine()
            print()
            test_api_server()
        else:
            print("❌ Redis is not running. Start it first with: python3 scripts/redis_setup.py start")
    
    elif command == 'data':
        if check_redis_running():
            show_redis_data()
        else:
            print("❌ Redis is not running. Start it first with: python3 scripts/redis_setup.py start")
    
    elif command == 'monitor':
        if check_redis_running():
            monitor_redis()
        else:
            print("❌ Redis is not running. Start it first with: python3 scripts/redis_setup.py start")
    
    elif command == 'setup':
        print("🚀 Complete Redis setup...")
        
        # Start Redis
        if not check_redis_running():
            if not start_redis():
                return
        
        # Wait a moment for Redis to start
        import time
        time.sleep(2)
        
        # Populate data
        if not populate_redis_data():
            return
        
        print()
        
        # Test everything
        test_redis_connection()
        print()
        test_quote_engine()
        print()
        test_api_server()
        print()
        show_redis_data()
        
        print("\n🎉 Redis setup complete!")
        print("   You can now use the quote engine with real Redis data.")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use: check, start, populate, test, data, monitor, or setup")


if __name__ == "__main__":
    main() 