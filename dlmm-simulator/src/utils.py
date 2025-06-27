"""
Utility functions for DLMM simulator.
"""

import json
from typing import Dict, List, Any
from .pool import MockPool, PoolConfig
from .math import DLMMMath


def print_route_result(result, detailed: bool = False):
    """
    Print a route result in a formatted way.
    
    Args:
        result: RouteResult object
        detailed: Whether to print detailed step information
    """
    print(f"\n=== Route Result ===")
    print(f"Success: {result.success}")
    
    if not result.success:
        print(f"Error: {result.error_message}")
        return
    
    print(f"Input: {result.total_amount_in:.6f}")
    print(f"Output: {result.total_amount_out:.6f}")
    print(f"Total Price Impact: {result.total_price_impact:.4f}%")
    print(f"Number of Steps: {len(result.steps)}")
    
    if detailed and result.steps:
        print(f"\n=== Route Steps ===")
        for i, step in enumerate(result.steps):
            print(f"Step {i+1}:")
            print(f"  Pool: {step.pool_id}")
            print(f"  Bin: {step.bin_id}")
            print(f"  {step.token_in} → {step.token_out}")
            print(f"  Amount In: {step.amount_in:.6f}")
            print(f"  Amount Out: {step.amount_out:.6f}")
            print(f"  Price: ${step.price:,.2f}")
            print(f"  Price Impact: {step.price_impact:.4f}%")


def create_test_pools() -> Dict[str, MockPool]:
    """
    Create a set of test pools for simulation.
    
    Returns:
        Dictionary of pool_id -> MockPool
    """
    pools = {}
    
    # BTC/USDC pool
    btc_usdc_config = PoolConfig(
        active_bin_id=500,
        active_price=50000.0,
        bin_step=0.001,
        x_token="BTC",
        y_token="USDC"
    )
    pools["BTC-USDC"] = MockPool(btc_usdc_config)
    
    # ETH/USDC pool
    eth_usdc_config = PoolConfig(
        active_bin_id=500,
        active_price=3000.0,
        bin_step=0.001,
        x_token="ETH",
        y_token="USDC"
    )
    pools["ETH-USDC"] = MockPool(eth_usdc_config)
    
    # ETH/BTC pool
    eth_btc_config = PoolConfig(
        active_bin_id=500,
        active_price=0.06,  # 1 ETH = 0.06 BTC
        bin_step=0.001,
        x_token="ETH",
        y_token="BTC"
    )
    pools["ETH-BTC"] = MockPool(eth_btc_config)
    
    return pools


def analyze_pool_state(pool: MockPool) -> Dict[str, Any]:
    """
    Analyze the state of a pool and return statistics.
    
    Args:
        pool: MockPool to analyze
    
    Returns:
        Dictionary with pool statistics
    """
    math = DLMMMath()
    
    # Calculate TVL
    tvl = math.calculate_tvl(pool.bins)
    
    # Calculate bin distribution
    distribution = math.calculate_bin_distribution(pool.bins, pool.config.active_bin_id)
    
    # Get active bin details
    active_bin = pool.get_active_bin()
    
    # Calculate price range
    min_price = min(bin_data.price for bin_data in pool.bins.values())
    max_price = max(bin_data.price for bin_data in pool.bins.values())
    
    return {
        'pool_id': f"{pool.config.x_token}-{pool.config.y_token}",
        'active_bin_id': pool.config.active_bin_id,
        'active_price': pool.config.active_price,
        'bin_step': pool.config.bin_step,
        'tvl': tvl,
        'price_range': {
            'min': min_price,
            'max': max_price,
            'spread': max_price - min_price
        },
        'active_bin': {
            'bin_id': active_bin.bin_id,
            'price': active_bin.price,
            'x_amount': active_bin.x_amount,
            'y_amount': active_bin.y_amount,
            'total_liquidity': active_bin.total_liquidity
        },
        'distribution': distribution
    }


def print_pool_analysis(pool: MockPool):
    """
    Print a detailed analysis of a pool.
    
    Args:
        pool: MockPool to analyze
    """
    analysis = analyze_pool_state(pool)
    
    print(f"\n=== Pool Analysis: {analysis['pool_id']} ===")
    print(f"Active Bin: {analysis['active_bin_id']} at ${analysis['active_price']:,.2f}")
    print(f"Bin Step: {analysis['bin_step']:.3f} ({analysis['bin_step']*10000:.0f} bps)")
    print(f"TVL: ${analysis['tvl']:,.2f}")
    print(f"Price Range: ${analysis['price_range']['min']:,.2f} - ${analysis['price_range']['max']:,.2f}")
    print(f"Price Spread: ${analysis['price_range']['spread']:,.2f}")
    
    print(f"\n=== Active Bin Details ===")
    active = analysis['active_bin']
    print(f"Bin ID: {active['bin_id']}")
    print(f"Price: ${active['price']:,.2f}")
    print(f"X Amount: {active['x_amount']:,.6f}")
    print(f"Y Amount: {active['y_amount']:,.2f}")
    print(f"Total Liquidity: ${active['total_liquidity']:,.2f}")
    
    print(f"\n=== Liquidity Distribution ===")
    dist = analysis['distribution']
    print(f"Left Bins: {dist['left_bins_count']} ({dist['left_percentage']:.1f}%)")
    print(f"Right Bins: {dist['right_bins_count']} ({dist['right_percentage']:.1f}%)")
    print(f"Active Bin: {dist['active_percentage']:.1f}%")


def save_pool_state(pool: MockPool, filename: str):
    """
    Save pool state to a JSON file.
    
    Args:
        pool: MockPool to save
        filename: Output filename
    """
    state = {
        'config': {
            'active_bin_id': pool.config.active_bin_id,
            'active_price': pool.config.active_price,
            'bin_step': pool.config.bin_step,
            'num_bins': pool.config.num_bins,
            'x_token': pool.config.x_token,
            'y_token': pool.config.y_token
        },
        'bins': {}
    }
    
    for bin_id, bin_data in pool.bins.items():
        state['bins'][str(bin_id)] = {
            'price': bin_data.price,
            'x_amount': bin_data.x_amount,
            'y_amount': bin_data.y_amount,
            'total_liquidity': bin_data.total_liquidity,
            'is_active': bin_data.is_active
        }
    
    with open(filename, 'w') as f:
        json.dump(state, f, indent=2)


def load_pool_state(filename: str) -> MockPool:
    """
    Load pool state from a JSON file.
    
    Args:
        filename: Input filename
    
    Returns:
        MockPool with loaded state
    """
    with open(filename, 'r') as f:
        state = json.load(f)
    
    config = PoolConfig(
        active_bin_id=state['config']['active_bin_id'],
        active_price=state['config']['active_price'],
        bin_step=state['config']['bin_step'],
        num_bins=state['config']['num_bins'],
        x_token=state['config']['x_token'],
        y_token=state['config']['y_token']
    )
    
    pool = MockPool(config)
    
    # Override bins with loaded data
    for bin_id_str, bin_data in state['bins'].items():
        bin_id = int(bin_id_str)
        pool.bins[bin_id] = pool.get_bin(bin_id)  # Get existing bin
        if pool.bins[bin_id]:
            pool.bins[bin_id].price = bin_data['price']
            pool.bins[bin_id].x_amount = bin_data['x_amount']
            pool.bins[bin_id].y_amount = bin_data['y_amount']
            pool.bins[bin_id].total_liquidity = bin_data['total_liquidity']
            pool.bins[bin_id].is_active = bin_data['is_active']
    
    return pool


def compare_routes(route1, route2) -> Dict[str, Any]:
    """
    Compare two route results.
    
    Args:
        route1: First RouteResult
        route2: Second RouteResult
    
    Returns:
        Dictionary with comparison results
    """
    if not route1.success or not route2.success:
        return {
            'valid_comparison': False,
            'route1_success': route1.success,
            'route2_success': route2.success
        }
    
    # Calculate differences
    amount_diff = route2.total_amount_out - route1.total_amount_out
    amount_diff_pct = (amount_diff / route1.total_amount_out * 100) if route1.total_amount_out > 0 else 0
    
    price_impact_diff = route2.total_price_impact - route1.total_price_impact
    
    return {
        'valid_comparison': True,
        'route1': {
            'amount_out': route1.total_amount_out,
            'price_impact': route1.total_price_impact,
            'steps': len(route1.steps)
        },
        'route2': {
            'amount_out': route2.total_amount_out,
            'price_impact': route2.total_price_impact,
            'steps': len(route2.steps)
        },
        'differences': {
            'amount_diff': amount_diff,
            'amount_diff_pct': amount_diff_pct,
            'price_impact_diff': price_impact_diff,
            'better_route': 'route2' if amount_diff > 0 else 'route1'
        }
    }


def print_route_comparison(route1, route2):
    """
    Print a comparison between two routes.
    
    Args:
        route1: First RouteResult
        route2: Second RouteResult
    """
    comparison = compare_routes(route1, route2)
    
    if not comparison['valid_comparison']:
        print("Cannot compare routes - one or both failed")
        return
    
    print(f"\n=== Route Comparison ===")
    print(f"Route 1: {comparison['route1']['amount_out']:.6f} output, {comparison['route1']['price_impact']:.4f}% impact, {comparison['route1']['steps']} steps")
    print(f"Route 2: {comparison['route2']['amount_out']:.6f} output, {comparison['route2']['price_impact']:.4f}% impact, {comparison['route2']['steps']} steps")
    
    diff = comparison['differences']
    print(f"Amount Difference: {diff['amount_diff']:+.6f} ({diff['amount_diff_pct']:+.2f}%)")
    print(f"Price Impact Difference: {diff['price_impact_diff']:+.4f}%")
    print(f"Better Route: {diff['better_route']}") 