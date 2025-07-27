"""
Graph operations for the quote engine.
Implements build_token_graph and enumerate_paths functions following Grok's design.
"""

import networkx as nx
import ast
import logging
from typing import List, Dict, Any
from ..redis.client import RedisClient
from ..redis.schemas import TokenGraphData

logger = logging.getLogger(__name__)


def build_token_graph(redis_client: RedisClient) -> nx.Graph:
    """
    Build token graph from Redis data.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        NetworkX graph with token pairs as edges and pools as edge attributes
    """
    try:
        graph = nx.Graph()
        
        # Get token graph from Redis
        token_graph_data = redis_client.get_token_graph("1")
        
        if not token_graph_data:
            logger.warning("No token graph data found in Redis")
            return graph
        
        # Build graph from token pairs
        for pair_str, pools_str in token_graph_data.token_pairs.items():
            try:
                # Parse token pair (e.g., "BTC->USDC")
                token_a, token_b = pair_str.split("->")
                
                # Parse pools list
                if isinstance(pools_str, str):
                    pools = ast.literal_eval(pools_str)
                else:
                    pools = pools_str
                
                # Add edge with pools as attribute
                graph.add_edge(token_a, token_b, pools=pools)
                
                logger.debug(f"Added edge {token_a} -> {token_b} with pools: {pools}")
                
            except Exception as e:
                logger.error(f"Error processing token pair {pair_str}: {e}")
                continue
        
        logger.info(f"Built token graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph
        
    except Exception as e:
        logger.error(f"Error building token graph: {e}")
        return nx.Graph()


def enumerate_paths(graph: nx.Graph, input_token: str, output_token: str, max_hops: int = 3) -> List[List[str]]:
    """
    Enumerate simple paths between tokens.
    
    Args:
        graph: NetworkX graph
        input_token: Starting token
        output_token: Ending token
        max_hops: Maximum number of hops (default: 3)
        
    Returns:
        List of token paths
    """
    try:
        # Check if tokens exist in graph
        if input_token not in graph.nodes or output_token not in graph.nodes:
            logger.warning(f"Tokens not found in graph: {input_token} or {output_token}")
            return []
        
        # Get all simple paths up to max_hops
        paths = list(nx.all_simple_paths(graph, input_token, output_token, cutoff=max_hops))
        
        # Filter out single-node paths (no hops)
        valid_paths = [path for path in paths if len(path) > 1]
        
        logger.info(f"Found {len(valid_paths)} valid paths from {input_token} to {output_token}")
        
        return valid_paths
        
    except Exception as e:
        logger.error(f"Error enumerating paths: {e}")
        return []


def get_pools_for_token_pair(graph: nx.Graph, token_a: str, token_b: str) -> List[str]:
    """
    Get available pools for a token pair.
    
    Args:
        graph: NetworkX graph
        token_a: First token
        token_b: Second token
        
    Returns:
        List of pool IDs for the token pair
    """
    try:
        if graph.has_edge(token_a, token_b):
            return graph[token_a][token_b].get('pools', [])
        return []
    except Exception as e:
        logger.error(f"Error getting pools for {token_a} -> {token_b}: {e}")
        return []


def validate_graph(graph: nx.Graph) -> bool:
    """
    Validate the token graph structure.
    
    Args:
        graph: NetworkX graph to validate
        
    Returns:
        True if graph is valid, False otherwise
    """
    try:
        # Check if graph has nodes
        if graph.number_of_nodes() == 0:
            logger.warning("Graph has no nodes")
            return False
        
        # Check if graph has edges
        if graph.number_of_edges() == 0:
            logger.warning("Graph has no edges")
            return False
        
        # Check that all edges have pools attribute
        for edge in graph.edges(data=True):
            if 'pools' not in edge[2]:
                logger.error(f"Edge {edge[0]} -> {edge[1]} missing pools attribute")
                return False
            
            if not isinstance(edge[2]['pools'], list):
                logger.error(f"Edge {edge[0]} -> {edge[1]} pools attribute is not a list")
                return False
        
        logger.info("Graph validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Graph validation error: {e}")
        return False 