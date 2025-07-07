"""
Data Manager for Redis Integration
Handles the 5-second update cycle and manages pool and bin data in Redis.
"""

import json
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
from dataclasses import dataclass
import random

from .client import RedisClient, RedisConfig
from .schemas import (
    PoolData, BinData, Metadata, RedisSchema, DataValidator,
    get_current_timestamp, create_metadata
)

logger = logging.getLogger(__name__)


@dataclass
class DataUpdateEvent:
    """Event data for data updates"""
    event_type: str  # "pool_added", "pool_updated", "pool_removed", "bin_updated"
    pool_id: str
    timestamp: float
    data: Optional[Dict[str, Any]] = None


class DataManager:
    """
    Manages pool and bin data in Redis with 5-second update cycle
    """
    
    def __init__(self, redis_client: RedisClient, update_interval: int = 5):
        self.redis_client = redis_client
        self.update_interval = update_interval
        self.running = False
        self.update_thread = None
        self.event_callbacks: List[Callable[[DataUpdateEvent], None]] = []
        self.last_update_time = 0
        self.update_lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "total_updates": 0,
            "last_update_duration_ms": 0,
            "errors_count": 0,
            "pools_updated": 0,
            "bins_updated": 0
        }
    
    def start(self):
        """Start the data update loop"""
        if self.running:
            logger.warning("Data manager is already running")
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info(f"Data manager started with {self.update_interval}s update interval")
    
    def stop(self):
        """Stop the data update loop"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=10)
        logger.info("Data manager stopped")
    
    def add_event_callback(self, callback: Callable[[DataUpdateEvent], None]):
        """Add callback for data update events"""
        self.event_callbacks.append(callback)
    
    def _update_loop(self):
        """Main update loop"""
        while self.running:
            try:
                start_time = time.time()
                
                # Perform data update
                self._perform_update()
                
                # Update statistics
                update_duration = (time.time() - start_time) * 1000
                self.stats["last_update_duration_ms"] = update_duration
                self.stats["total_updates"] += 1
                self.last_update_time = time.time()
                
                logger.debug(f"Data update completed in {update_duration:.2f}ms")
                
                # Wait for next update
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.stats["errors_count"] += 1
                logger.error(f"Error in data update loop: {e}")
                time.sleep(self.update_interval)
    
    def _perform_update(self):
        """Perform a single data update"""
        with self.update_lock:
            # This is where we would fetch data from external source
            # For now, we'll simulate updates with mock data
            self._simulate_data_update()
    
    def _simulate_data_update(self):
        """Simulate data updates for testing"""
        # Simulate pool updates
        pools_to_update = [
            "BTC-USDC-25",
            "BTC-USDC-50", 
            "SOL-USDC-25"
        ]
        
        for pool_id in pools_to_update:
            # Simulate actual swaps that may cause active bin movement
            self._simulate_swap_execution(pool_id)
    
    def _simulate_swap_execution(self, pool_id: str):
        """Simulate random bin state updates while maintaining DLMM invariants"""
        try:
            # Get current pool data
            pool_key = RedisSchema.get_pool_key(pool_id)
            pool_data_str = self.redis_client.get(pool_key)
            
            if not pool_data_str:
                logger.warning(f"Pool {pool_id} not found in Redis")
                return
            
            pool_data = json.loads(pool_data_str)
            current_active_bin = pool_data["active_bin_id"]
            
            # Randomly move active bin left or right
            direction = random.choice([-1, 1])
            new_active_bin = current_active_bin + direction
            
            # Keep active bin within reasonable bounds
            if new_active_bin < 450 or new_active_bin > 550:
                new_active_bin = current_active_bin  # Stay put if too far
            
            # Update pool data if active bin changed
            if new_active_bin != current_active_bin:
                pool_data["active_bin_id"] = new_active_bin
                pool_data["last_updated"] = get_current_timestamp()
                
                # Save to Redis
                self.redis_client.set(pool_key, json.dumps(pool_data))
                
                # Update bins for this pool with new active bin
                self._update_pool_bins(pool_id, new_active_bin)
                
                # Trigger event
                self._trigger_event(DataUpdateEvent(
                    event_type="pool_updated",
                    pool_id=pool_id,
                    timestamp=time.time(),
                    data=pool_data
                ))
                
                self.stats["pools_updated"] += 1
                logger.info(f"Active bin moved from {current_active_bin} to {new_active_bin} for pool {pool_id}")
            else:
                # Just update existing bins with random liquidity changes
                self._update_pool_bins(pool_id, current_active_bin)
            
        except Exception as e:
            logger.error(f"Error simulating bin state updates for {pool_id}: {e}")
            self.stats["errors_count"] += 1
    
    def _update_pool_bins(self, pool_id: str, new_active_bin_id: int):
        """Update bin data for a pool"""
        try:
            # Get pool configuration
            pool_key = RedisSchema.get_pool_key(pool_id)
            pool_data_str = self.redis_client.get(pool_key)
            
            if not pool_data_str:
                return
            
            pool_data = json.loads(pool_data_str)
            
            # Calculate new active bin price
            initial_active_bin_id = pool_data["initial_active_bin_id"]
            initial_active_price = float(pool_data["active_bin_price"])
            bin_step = pool_data["bin_step"] / 10000
            
            new_active_price = initial_active_price * ((1 + bin_step) ** (new_active_bin_id - initial_active_bin_id))
            
            # Update bins around the new active bin
            for bin_id in range(new_active_bin_id - 50, new_active_bin_id + 51):
                self._update_single_bin(pool_id, bin_id, new_active_bin_id, new_active_price, bin_step)
            
            self.stats["bins_updated"] += 101  # 101 bins per pool
            
        except Exception as e:
            logger.error(f"Error updating pool bins for {pool_id}: {e}")
            self.stats["errors_count"] += 1
    
    def _update_single_bin(self, pool_id: str, bin_id: int, active_bin_id: int, active_price: float, bin_step: float):
        """Update a single bin with random liquidity changes"""
        try:
            from src.math import DLMMMath
            
            # Calculate bin price
            bin_price = DLMMMath.calculate_bin_price(active_price, bin_step, bin_id, active_bin_id)
            
            # Calculate base liquidity distribution
            distance = abs(bin_id - active_bin_id)
            liquidity_factor = max(0.1, 1 - (distance / 50) ** 2)
            
            # Add random variation to liquidity (±20%)
            random_factor = random.uniform(0.8, 1.2)
            liquidity_factor *= random_factor
            
            # Determine token amounts based on bin position (DLMM invariant)
            if bin_id == active_bin_id:
                # Active bin: BOTH X and Y tokens
                x_amount = 1000 * liquidity_factor
                # Adjust Y amount based on token price to create balanced liquidity
                if active_price > 10000:  # BTC-like tokens
                    y_amount = 100000000 * liquidity_factor  # ~$100M USDC
                elif active_price > 100:  # SOL-like tokens  
                    y_amount = 200000 * liquidity_factor  # ~$40M USDC for SOL at $200
                else:  # Low-value tokens
                    y_amount = 1000000 * liquidity_factor  # Default
            elif bin_id < active_bin_id:
                # Bins to the left of active bin: only X tokens
                x_amount = 1000 * liquidity_factor
                y_amount = 0
            else:
                # Bins to the right of active bin: only Y tokens
                x_amount = 0
                # Adjust Y amount based on token price
                if active_price > 10000:  # BTC-like tokens
                    y_amount = 100000000 * liquidity_factor  # ~$100M USDC
                elif active_price > 100:  # SOL-like tokens
                    y_amount = 200000 * liquidity_factor  # ~$40M USDC for SOL at $200
                else:  # Low-value tokens
                    y_amount = 1000000 * liquidity_factor  # Default
            
            # Create bin data
            bin_data = {
                "pool_id": pool_id,
                "bin_id": bin_id,
                "x_amount": x_amount,
                "y_amount": y_amount,
                "price": bin_price,
                "total_liquidity": x_amount + y_amount,
                "is_active": bin_id == active_bin_id,
                "last_updated": get_current_timestamp()
            }
            
            # Save to Redis
            bin_key = RedisSchema.get_bin_key(pool_id, bin_id)
            self.redis_client.set(bin_key, json.dumps(bin_data))
            
        except Exception as e:
            logger.error(f"Error updating bin {pool_id}:{bin_id}: {e}")
    
    def _trigger_event(self, event: DataUpdateEvent):
        """Trigger event callbacks"""
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get data manager statistics"""
        return {
            **self.stats,
            "running": self.running,
            "last_update_time": self.last_update_time,
            "update_interval": self.update_interval
        }
    
    def populate_initial_data(self):
        """Populate Redis with initial data"""
        try:
            logger.info("Populating initial data in Redis...")
            
            # Sample pools
            pools = [
                {
                    "pool_id": "BTC-USDC-25",
                    "token_x": "BTC",
                    "token_y": "USDC",
                    "bin_step": 25,
                    "initial_active_bin_id": 500,
                    "active_bin_id": 500,
                    "active_bin_price": 100000.0,
                    "status": "active",
                    "total_tvl": 1000000.0,
                    "created_at": get_current_timestamp(),
                    "last_updated": get_current_timestamp()
                },
                {
                    "pool_id": "BTC-USDC-50",
                    "token_x": "BTC",
                    "token_y": "USDC",
                    "bin_step": 50,
                    "initial_active_bin_id": 500,
                    "active_bin_id": 500,
                    "active_bin_price": 100000.0,
                    "status": "active",
                    "total_tvl": 500000.0,
                    "created_at": get_current_timestamp(),
                    "last_updated": get_current_timestamp()
                },
                {
                    "pool_id": "SOL-USDC-25",
                    "token_x": "SOL",
                    "token_y": "USDC",
                    "bin_step": 25,
                    "initial_active_bin_id": 500,
                    "active_bin_id": 500,
                    "active_bin_price": 200.0,
                    "status": "active",
                    "total_tvl": 100000.0,
                    "created_at": get_current_timestamp(),
                    "last_updated": get_current_timestamp()
                }
            ]
            
            total_bins = 0
            
            # Store pools and create bins
            for pool in pools:
                # Store pool data
                pool_key = RedisSchema.get_pool_key(pool["pool_id"])
                self.redis_client.set(pool_key, json.dumps(pool))
                
                # Create bins for this pool
                bin_count = self._create_pool_bins(pool)
                total_bins += bin_count
                
                # Create token indices
                self._create_token_indices(pool)
                
                # Trigger event
                self._trigger_event(DataUpdateEvent(
                    event_type="pool_added",
                    pool_id=pool["pool_id"],
                    timestamp=time.time(),
                    data=pool
                ))
            
            # Create metadata
            metadata = create_metadata(
                total_pools=len(pools),
                total_tokens=4,  # BTC, USDC, SOL, ETH
                total_bins=total_bins
            )
            
            metadata_key = RedisSchema.get_metadata_key()
            self.redis_client.hmset(metadata_key, metadata.to_redis_hash())
            
            logger.info(f"Initial data populated: {len(pools)} pools, {total_bins} bins")
            
        except Exception as e:
            logger.error(f"Error populating initial data: {e}")
            raise
    
    def _create_pool_bins(self, pool: Dict[str, Any]) -> int:
        """Create bins for a pool"""
        pool_id = pool["pool_id"]
        active_bin_id = pool["active_bin_id"]
        active_price = float(pool["active_bin_price"])
        bin_step = pool["bin_step"] / 10000
        
        bin_count = 0
        
        # Create bins around active bin
        for bin_id in range(active_bin_id - 50, active_bin_id + 51):
            self._update_single_bin(pool_id, bin_id, active_bin_id, active_price, bin_step)
            bin_count += 1
        
        return bin_count
    
    def _create_token_indices(self, pool: Dict[str, Any]):
        """Create token indices for fast lookup"""
        pool_id = pool["pool_id"]
        token_x = pool["token_x"]
        token_y = pool["token_y"]
        
        # Add to token indices
        for token in [token_x, token_y]:
            token_key = RedisSchema.get_token_index_key(token)
            current_pools_str = self.redis_client.get(token_key)
            
            if current_pools_str:
                current_pools = json.loads(current_pools_str)
                if not isinstance(current_pools, list):
                    current_pools = []
            else:
                current_pools = []
            
            if pool_id not in current_pools:
                current_pools.append(pool_id)
                # Store as JSON array for now (Redis sets would be better)
                self.redis_client.set(token_key, json.dumps(current_pools))
        
        # Create pair index
        pair_key = RedisSchema.get_pair_index_key(token_x, token_y)
        current_pools_str = self.redis_client.get(pair_key)
        if current_pools_str:
            pools = json.loads(current_pools_str)
            if not isinstance(pools, list):
                pools = []
        else:
            pools = []
        
        if pool_id not in pools:
            pools.append(pool_id)
            self.redis_client.set(pair_key, json.dumps(pools))
    
    def get_pool_data(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get pool data from Redis"""
        try:
            pool_key = RedisSchema.get_pool_key(pool_id)
            pool_data_str = self.redis_client.get(pool_key)
            
            if pool_data_str:
                return json.loads(pool_data_str)
            return None
            
        except Exception as e:
            logger.error(f"Error getting pool data for {pool_id}: {e}")
            return None
    
    def get_pool_bins(self, pool_id: str) -> Dict[int, Dict[str, Any]]:
        """Get all bins for a pool"""
        try:
            bins = {}
            
            # Get bin keys for this pool
            bin_pattern = f"bin:{pool_id}:*"
            bin_keys = self.redis_client.keys(bin_pattern)
            
            for bin_key in bin_keys:
                bin_data_str = self.redis_client.get(bin_key)
                if bin_data_str:
                    bin_data = json.loads(bin_data_str)
                    bin_id = bin_data["bin_id"]
                    bins[bin_id] = bin_data
            
            return bins
            
        except Exception as e:
            logger.error(f"Error getting pool bins for {pool_id}: {e}")
            return {}
    
    def get_metadata(self) -> Optional[Metadata]:
        """Get metadata from Redis"""
        try:
            metadata_key = RedisSchema.get_metadata_key()
            metadata_hash = self.redis_client.hgetall(metadata_key)
            
            if metadata_hash:
                return Metadata.from_redis_hash(metadata_hash)
            return None
            
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return None 