"""
Quote computation for the quote engine.
Implements compute_quote and find_best_route functions following Grok's design.
"""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from ..redis.client import RedisClient
from ..redis.schemas import PoolData, BinData, RedisSchema
from ..utils.traits import TraitMappings
from .data import batch_load_bin_reserves
import networkx as nx

logger = logging.getLogger(__name__)


def get_token_decimals(redis_client: RedisClient, token_symbol: str) -> int:
    """Get token decimals from Redis"""
    try:
        key = RedisSchema.get_token_key(token_symbol)
        data = redis_client.client.hgetall(key)
        if data:
            return int(data.get('decimals', 18))
        return 18  # Default
    except:
        return 18


def convert_to_atomic(amount: Decimal, decimals: int) -> Decimal:
    """Convert raw amount to atomic units"""
    return amount * (Decimal('10') ** decimals)


def convert_from_atomic(amount: Decimal, decimals: int) -> Decimal:
    """Convert atomic units to raw amount"""
    return amount / (Decimal('10') ** decimals)


def compute_quote(pool_id: str, input_token: str, output_token: str, amount_in: Decimal, 
                 redis_client: RedisClient, shared_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute quote for a single pool swap.
    
    Args:
        pool_id: Pool identifier
        input_token: Input token symbol
        output_token: Output token symbol
        amount_in: Input amount (Decimal)
        redis_client: Redis client
        shared_data: Pre-fetched shared data
        
    Returns:
        Dict with amount_out, execution_path, fee_amount, etc.
    """
    try:
        # Get pool metadata
        pool_data = shared_data[pool_id]['metadata']
        token0 = pool_data.token0
        token1 = pool_data.token1
        
        # Get token decimals for the actual input and output tokens
        input_token_decimals = get_token_decimals(redis_client, input_token)
        output_token_decimals = get_token_decimals(redis_client, output_token)
        
        # Keep everything in raw units for consistency with reserves
        # amount_in is already in raw units (e.g., 1 BTC, not 100,000,000 satoshis)
        
        # Determine swap direction
        swap_for_y = input_token == token0
        
        # Calculate fee rate based on direction
        if swap_for_y:
            # X → Y swap: use x_fees
            fee_rate = (
                Decimal(str(pool_data.x_protocol_fee)) + 
                Decimal(str(pool_data.x_provider_fee)) + 
                Decimal(str(pool_data.x_variable_fee))
            ) / Decimal('10000')
        else:
            # Y → X swap: use y_fees
            fee_rate = (
                Decimal(str(pool_data.y_protocol_fee)) + 
                Decimal(str(pool_data.y_provider_fee)) + 
                Decimal(str(pool_data.y_variable_fee))
            ) / Decimal('10000')
        
        # Apply fees upfront (amount_in is in raw units)
        fee_amount = amount_in * fee_rate
        effective_amount_in = amount_in - fee_amount
        
        # Get active bin info for starting point
        active_bin_id = int(pool_data.active_bin)
        
        # Get active bin price to determine traversal direction
        active_bin_price = redis_client.get_bin_price(pool_id, active_bin_id)
        if not active_bin_price:
            return {
                'success': False,
                'amount_out': Decimal('0'),
                'execution_path': [],
                'fee_amount': fee_amount,
                'error': f'No active bin price found for pool {pool_id}'
            }
        
        # Batch load bins in the correct direction - start from active bin
        if swap_for_y:
            # X → Y: traverse LEFT (lower prices) to find Y tokens
            bin_list = redis_client.get_bin_prices_reverse_range(pool_id, active_bin_price, 0)
            bin_list.sort(key=lambda x: x[1], reverse=True)  # Sort by price descending (right to left)
        else:
            # Y → X: traverse RIGHT (higher prices) to find X tokens
            bin_list = redis_client.get_bin_prices_in_range(pool_id, active_bin_price, float('inf'))
            bin_list.sort(key=lambda x: x[1])  # Sort by price ascending (left to right)
        
        if not bin_list:
            logger.warning(f"No bins found for pool {pool_id}")
            return {
                'success': False,
                'amount_out': Decimal('0'),
                'execution_path': [],
                'fee_amount': fee_amount,
                'error': f'No bins found for pool {pool_id}'
            }
        
        logger.info(f"Found {len(bin_list)} bins for pool {pool_id}")
        
        # Batch load reserves for all bins
        bin_ids = [bin_id for bin_id, _ in bin_list]
        reserves_data = batch_load_bin_reserves(redis_client, pool_id, bin_ids)
        
        logger.info(f"Loaded reserves for {len(reserves_data)} bins")
        
        # Simulate swap traversal
        remaining = effective_amount_in
        amount_out = Decimal('0')
        execution_path = []
        
        logger.info(f"Starting swap traversal: remaining={remaining}, effective_amount_in={effective_amount_in}")
        
        for bin_id, price_float in bin_list:
            if remaining <= 0:
                break
                
            price = Decimal(str(price_float))
            reserves = reserves_data.get(bin_id)
            if reserves:
                reserve_x = Decimal(str(reserves.reserve_x))
                reserve_y = Decimal(str(reserves.reserve_y))
                logger.info(f"Bin {bin_id}: price={price}, reserves={reserve_x}/{reserve_y}")
            else:
                reserve_x = Decimal('0')
                reserve_y = Decimal('0')
                logger.warning(f"Bin {bin_id}: No data found")
            
            if swap_for_y:
                # X → Y swap
                # The limiting factor is how much Y (output) is available
                # Calculate how much X can be swapped for the available Y
                available_y = reserve_y
                max_x_for_available_y = available_y / price if price > 0 else Decimal('0')
                # For X→Y swaps, we don't need X tokens in the bin - user provides X tokens
                # Only constrain by remaining input and max X for available Y
                max_in = min(remaining, max_x_for_available_y)
                in_effective = min(remaining, max_in)
                out_this = in_effective * price
                amount_key = 'x_amount'
                function_name = 'swap-x-for-y'
                logger.info(f"X→Y: available_y={available_y}, max_x_for_available_y={max_x_for_available_y}, max_in={max_in}, in_effective={in_effective}, out_this={out_this}")
            else:
                # Y → X swap
                # The limiting factor is how much X (output) is available
                # Calculate how much Y can be swapped for the available X
                available_x = reserve_x
                max_y_for_available_x = available_x * price
                # For Y→X swaps, we don't need Y tokens in the bin - user provides Y tokens
                # Only constrain by remaining input and max Y for available X
                max_in = min(remaining, max_y_for_available_x)
                in_effective = min(remaining, max_in)
                out_this = in_effective / price
                amount_key = 'y_amount'
                function_name = 'swap-y-for-x'
                logger.info(f"Y→X: available_x={available_x}, max_y_for_available_x={max_y_for_available_x}, max_in={max_in}, in_effective={in_effective}, out_this={out_this}")
            
            if in_effective > 0:
                # Calculate partial amount (including fee adjustment)
                partial_amount = in_effective / (Decimal('1') - fee_rate) if fee_rate < Decimal('1') else Decimal('0')
                
                # Add to execution path
                entry = {
                    'pool_trait': TraitMappings.get_pool_trait(pool_id),
                    'x_token_trait': TraitMappings.get_token_trait(token0),
                    'y_token_trait': TraitMappings.get_token_trait(token1),
                    'bin_id': bin_id,
                    'function_name': function_name,
                    amount_key: partial_amount.quantize(Decimal('1'))
                }
                execution_path.append(entry)
                
                amount_out += out_this
                remaining -= in_effective
                logger.info(f"Added step: bin={bin_id}, used={in_effective}, remaining={remaining}")
            else:
                logger.info(f"Bin {bin_id}: No liquidity available")
        
        # amount_out is already in raw units (no conversion needed)
        
        # Rounding adjustment on last partial (if needed)
        if execution_path:
            total_partial = sum(
                Decimal(str(e.get('x_amount', '0'))) + Decimal(str(e.get('y_amount', '0'))) 
                for e in execution_path
            )
            adjustment = amount_in - total_partial
            if abs(adjustment) > Decimal('0.001'):  # Only adjust if difference is significant
                last_entry = execution_path[-1]
                if 'x_amount' in last_entry:
                    last_entry['x_amount'] = str(Decimal(str(last_entry['x_amount'])) + adjustment)
                elif 'y_amount' in last_entry:
                    last_entry['y_amount'] = str(Decimal(str(last_entry['y_amount'])) + adjustment)
        
        return {
            'success': True,
            'amount_out': amount_out.quantize(Decimal('1')),
            'execution_path': execution_path,
            'fee_amount': fee_amount.quantize(Decimal('1')),
            'effective_amount_in': effective_amount_in.quantize(Decimal('1')),
            'price_impact': Decimal('0'),  # TODO: Calculate price impact
            'input_token_decimals': input_token_decimals,
            'output_token_decimals': output_token_decimals
        }
        
    except Exception as e:
        logger.error(f"Error computing quote for {pool_id}: {e}")
        return {
            'success': False,
            'amount_out': Decimal('0'),
            'execution_path': [],
            'fee_amount': Decimal('0'),
            'error': str(e)
        }


def find_best_route(paths: List[List[str]], amount_in: Decimal, redis_client: RedisClient, 
                   shared_data: Dict[str, Any], graph: nx.Graph) -> Dict[str, Any]:
    """
    Find the best route among all possible paths.
    
    Args:
        paths: List of token paths
        amount_in: Input amount
        redis_client: Redis client
        shared_data: Pre-fetched shared data
        graph: Token graph
        
    Returns:
        Dict with best route details
    """
    best_out = Decimal('0')
    best_details = None
    total_fee = Decimal('0')
    
    for path in paths:
        current_amt = amount_in
        hop_details = []
        route_fee = Decimal('0')
        viable = True
        
        for i in range(len(path) - 1):
            from_tok, to_tok = path[i], path[i + 1]
            pools = get_pools_for_token_pair(graph, from_tok, to_tok)
            
            best_hop_out = Decimal('0')
            best_hop = None
            
            for pool in pools:
                hop = compute_quote(pool, from_tok, to_tok, current_amt, redis_client, shared_data)
                
                if hop['success'] and hop['amount_out'] > best_hop_out:
                    best_hop_out = hop['amount_out']
                    best_hop = hop
            
            if best_hop_out == 0:
                viable = False
                break
                
            hop_details.append(best_hop)
            route_fee += best_hop.get('fee_amount', Decimal('0'))
            current_amt = best_hop_out
        
        if viable and current_amt > best_out:
            best_out = current_amt
            total_fee = route_fee
            
            # Flatten execution path across hops
            flattened = []
            for hop in hop_details:
                flattened.extend(hop['execution_path'])
            
            # Get decimal information from first and last hops
            input_token_decimals = hop_details[0].get('input_token_decimals') if hop_details else None
            
            # For output decimals, we need to get the final output token's decimals
            # The last hop's output_token_decimals is for the intermediate token
            # We need to get the final output token's decimals from Redis
            final_output_token = path[-1] if path else None
            output_token_decimals = None
            if final_output_token:
                output_token_decimals = get_token_decimals(redis_client, final_output_token)
            
            best_details = {
                'success': True,
                'amount_out': str(best_out),
                'route_path': path,
                'execution_path': flattened,
                'total_fee': str(total_fee),
                'fee_rate_avg': str(total_fee / amount_in) if amount_in > 0 else '0',
                'input_token_decimals': input_token_decimals,
                'output_token_decimals': output_token_decimals
            }
    
    if not best_details:
        return {
            'success': False,
            'amount_out': '0',
            'route_path': [],
            'execution_path': [],
            'total_fee': '0',
            'error': 'No viable route found'
        }
    
    return best_details


def get_pools_for_token_pair(graph, token_a: str, token_b: str) -> List[str]:
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