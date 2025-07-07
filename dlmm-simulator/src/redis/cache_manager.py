"""
Cache Manager for Redis Integration
Handles graph cache invalidation when pool topology changes.
"""

import time
import threading
from typing import Dict, List, Optional, Any, Set
import logging
from dataclasses import dataclass

from .data_manager import DataUpdateEvent

logger = logging.getLogger(__name__)


@dataclass
class CacheInvalidationEvent:
    """Cache invalidation event"""
    event_type: str  # "graph_cache_cleared", "path_cache_cleared"
    reason: str
    timestamp: float
    affected_pools: Optional[List[str]] = None


class GraphCacheManager:
    """
    Manages graph cache invalidation when pool topology changes
    """
    
    def __init__(self, quote_engine):
        self.quote_engine = quote_engine
        self.graph = quote_engine.graph
        self.invalidation_callbacks: List[callable] = []
        self.last_invalidation_time = 0
        self.invalidation_lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "total_invalidations": 0,
            "last_invalidation_duration_ms": 0,
            "cache_hit_rate": 0.0,
            "cache_miss_rate": 0.0
        }
    
    def add_invalidation_callback(self, callback: callable):
        """Add callback for cache invalidation events"""
        self.invalidation_callbacks.append(callback)
    
    def handle_data_update_event(self, event: DataUpdateEvent):
        """Handle data update events and invalidate cache if needed"""
        try:
            if event.event_type in ["pool_added", "pool_removed"]:
                # Pool topology changed - clear all graph cache
                self._invalidate_graph_cache("pool_topology_change", [event.pool_id])
                
            elif event.event_type == "pool_updated":
                # Pool updated - check if topology changed
                if self._is_topology_change(event):
                    self._invalidate_graph_cache("pool_topology_change", [event.pool_id])
                else:
                    # Only bin data changed - no cache invalidation needed
                    logger.debug(f"Pool {event.pool_id} updated (bin data only) - no cache invalidation needed")
                    
        except Exception as e:
            logger.error(f"Error handling data update event: {e}")
    
    def _is_topology_change(self, event: DataUpdateEvent) -> bool:
        """Check if the update represents a topology change"""
        if not event.data:
            return False
        
        # Check if pool status changed
        if "status" in event.data:
            # Status change could affect routing
            return True
        
        # Check if tokens changed (shouldn't happen in normal updates)
        if "token_x" in event.data or "token_y" in event.data:
            return True
        
        # Active bin movement is not a topology change
        # Only bin_step, tokens, or status changes are topology changes
        return False
    
    def _invalidate_graph_cache(self, reason: str, affected_pools: Optional[List[str]] = None):
        """Invalidate graph cache"""
        with self.invalidation_lock:
            start_time = time.time()
            
            try:
                # Clear the graph cache
                self.graph._clear_cache()
                
                # Update statistics
                invalidation_duration = (time.time() - start_time) * 1000
                self.stats["last_invalidation_duration_ms"] = invalidation_duration
                self.stats["total_invalidations"] += 1
                self.last_invalidation_time = time.time()
                
                # Create invalidation event
                invalidation_event = CacheInvalidationEvent(
                    event_type="graph_cache_cleared",
                    reason=reason,
                    timestamp=time.time(),
                    affected_pools=affected_pools
                )
                
                # Trigger callbacks
                self._trigger_invalidation_callbacks(invalidation_event)
                
                logger.info(f"Graph cache invalidated: {reason} (duration: {invalidation_duration:.2f}ms)")
                
                if affected_pools:
                    logger.info(f"Affected pools: {', '.join(affected_pools)}")
                
            except Exception as e:
                logger.error(f"Error invalidating graph cache: {e}")
    
    def _trigger_invalidation_callbacks(self, event: CacheInvalidationEvent):
        """Trigger cache invalidation callbacks"""
        for callback in self.invalidation_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in cache invalidation callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache manager statistics"""
        return {
            **self.stats,
            "last_invalidation_time": self.last_invalidation_time,
            "graph_cache_size": len(self.graph.path_cache) if hasattr(self.graph, 'path_cache') else 0
        }
    
    def manual_cache_clear(self, reason: str = "manual_clear"):
        """Manually clear the graph cache"""
        self._invalidate_graph_cache(reason)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        try:
            graph_cache_size = len(self.graph.path_cache) if hasattr(self.graph, 'path_cache') else 0
            
            # Sample some cache keys
            cache_keys = list(self.graph.path_cache.keys())[:10] if hasattr(self.graph, 'path_cache') else []
            
            return {
                "graph_cache_size": graph_cache_size,
                "sample_cache_keys": cache_keys,
                "cache_ttl": 300,  # 5 minutes
                "max_cache_size": 1000
            }
            
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {}


class BinDataStrategy:
    """
    Implements the bin data strategy: always fetch from Redis, never cache
    """
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.stats = {
            "total_bin_fetches": 0,
            "total_bin_fetch_time_ms": 0,
            "avg_bin_fetch_time_ms": 0
        }
    
    def get_pool_bins(self, pool_id: str) -> Dict[int, Dict[str, Any]]:
        """
        ALWAYS fetch from Redis - no caching of bin data
        This ensures we always have the latest liquidity information
        """
        start_time = time.time()
        
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
            
            # Update statistics
            fetch_time = (time.time() - start_time) * 1000
            self.stats["total_bin_fetches"] += 1
            self.stats["total_bin_fetch_time_ms"] += fetch_time
            self.stats["avg_bin_fetch_time_ms"] = (
                self.stats["total_bin_fetch_time_ms"] / self.stats["total_bin_fetches"]
            )
            
            logger.debug(f"Fetched {len(bins)} bins for {pool_id} in {fetch_time:.2f}ms")
            
            return bins
            
        except Exception as e:
            logger.error(f"Error fetching bin data for {pool_id}: {e}")
            return {}
    
    def get_bins_for_quote(self, pool_id: str, bin_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Fetch specific bins needed for quote calculation
        Always from Redis, no caching
        """
        start_time = time.time()
        
        try:
            bins = {}
            
            for bin_id in bin_ids:
                bin_key = f"bin:{pool_id}:{bin_id}"
                bin_data_str = self.redis_client.get(bin_key)
                
                if bin_data_str:
                    bin_data = json.loads(bin_data_str)
                    bins[bin_id] = bin_data
            
            # Update statistics
            fetch_time = (time.time() - start_time) * 1000
            self.stats["total_bin_fetches"] += 1
            self.stats["total_bin_fetch_time_ms"] += fetch_time
            self.stats["avg_bin_fetch_time_ms"] = (
                self.stats["total_bin_fetch_time_ms"] / self.stats["total_bin_fetches"]
            )
            
            logger.debug(f"Fetched {len(bins)} specific bins for {pool_id} in {fetch_time:.2f}ms")
            
            return bins
            
        except Exception as e:
            logger.error(f"Error fetching specific bins for {pool_id}: {e}")
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get bin data strategy statistics"""
        return {
            **self.stats,
            "strategy": "always_fetch_from_redis",
            "caching": False
        }


class PoolConfigCache:
    """
    Brief caching for pool configurations (1-2 seconds)
    """
    
    def __init__(self, ttl: int = 2):
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "total_requests": 0
        }
    
    def get_pool_config(self, pool_id: str, redis_client) -> Optional[Dict[str, Any]]:
        """Get pool configuration with brief caching"""
        self.stats["total_requests"] += 1
        
        # Check cache
        if pool_id in self.cache:
            cache_time = self.cache_timestamps[pool_id]
            if time.time() - cache_time < self.ttl:
                self.stats["cache_hits"] += 1
                return self.cache[pool_id]
        
        # Cache miss - fetch from Redis
        self.stats["cache_misses"] += 1
        
        try:
            pool_key = f"pool:{pool_id}"
            pool_data_str = redis_client.get(pool_key)
            
            if pool_data_str:
                pool_data = json.loads(pool_data_str)
                
                # Cache the result
                self.cache[pool_id] = pool_data
                self.cache_timestamps[pool_id] = time.time()
                
                return pool_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching pool config for {pool_id}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the pool config cache"""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Pool config cache cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pool config cache statistics"""
        total_requests = self.stats["total_requests"]
        hit_rate = (self.stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate_percent": hit_rate,
            "cache_size": len(self.cache),
            "ttl_seconds": self.ttl
        }


# Import json at the top level
import json 