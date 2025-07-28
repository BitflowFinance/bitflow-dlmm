#!/usr/bin/env python3
"""
DLMM Visualization Tool
Shows current pool state vs quoted swap impact using API data
Updated for Task 003: Integration with new quote-engine infrastructure
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import sys
import os
import requests
import json
import random
import time
import threading
from datetime import datetime
import redis
from typing import Dict, List, Optional, Any


# Configuration for new quote-engine integration
QUOTE_ENGINE_BASE_URL = "http://localhost:8000/api/v1"
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'decode_responses': True
}


def format_amount(amount_str, token, decimals=None):
    """Format amount string to human-readable format based on token decimals."""
    try:
        amount = int(amount_str)
        if decimals is not None:
            # API returns raw amounts, not atomic amounts
            # So we don't need to divide by decimal factors
            return f"{amount} {token}"
        else:
            # Fallback to hardcoded decimals
            if token == "BTC":
                return f"{amount:.8f} BTC"  # Raw BTC amount
            elif token == "ETH":
                return f"{amount:.18f} ETH"  # Raw ETH amount
            elif token == "SOL":
                return f"{amount:.9f} SOL"  # Raw SOL amount
            else:  # USDC
                return f"{amount:.2f} USDC"  # Raw USDC amount
    except:
        return amount_str


def format_number_with_commas(number):
    """Format number with commas for better readability."""
    try:
        return f"{number:,.2f}"
    except:
        return str(number)


def get_redis_client():
    """Get Redis client for direct data access"""
    try:
        return redis.Redis(**REDIS_CONFIG)
    except Exception as e:
        st.error(f"Failed to connect to Redis: {e}")
        return None


def get_pool_data_from_api(pool_id):
    """Get pool data from the new quote-engine API."""
    try:
        # Get all pools and filter by pool_id
        api_url = f"{QUOTE_ENGINE_BASE_URL}/pools"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            pools = data.get('pools', [])
            # Find the specific pool
            for pool in pools:
                if pool.get('pool_id') == pool_id:
                    return pool
            st.error(f"Pool {pool_id} not found")
            return None
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Failed to get pool data from API: {e}")
        return None


def get_bin_data_from_redis(pool_id, bin_range=20):
    """Get bin data directly from Redis for visualization."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return []
        
        # Get pool data to find active bin
        pool_data = get_pool_data_from_api(pool_id)
        if not pool_data:
            return []
        
        active_bin_id = pool_data.get('active_bin', 500)
        start_bin = active_bin_id - bin_range
        end_bin = active_bin_id + bin_range
        
        bins_data = []
        
        # Get bin prices from ZSET - Fixed key pattern
        price_key = f"pool:{pool_id}:bins"
        bin_prices = redis_client.zrangebyscore(price_key, 0, float('inf'), withscores=True)
        
        for bin_id_str, price in bin_prices:
            bin_id = int(bin_id_str)
            if start_bin <= bin_id <= end_bin:
                # Get bin reserves
                bin_key = f"bin:{pool_id}:{bin_id}"
                bin_data = redis_client.hgetall(bin_key)
                
                if bin_data:
                    reserve_x = int(bin_data.get('reserve_x', 0))
                    reserve_y = int(bin_data.get('reserve_y', 0))
                    liquidity = int(bin_data.get('liquidity', 0))
                    
                    bins_data.append({
                        'bin_id': bin_id,
                        'x_amount': reserve_x,
                        'y_amount': reserve_y,
                        'price': price,
                        'total_liquidity': liquidity,
                        'is_active': bin_id == active_bin_id
                    })
        
        return bins_data
    except Exception as e:
        st.error(f"Failed to get bin data from Redis: {e}")
        return []


def get_available_pools_from_api():
    """Get list of available pools from the new quote-engine API."""
    try:
        api_url = f"{QUOTE_ENGINE_BASE_URL}/pools"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('pools', [])
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Failed to get available pools from API: {e}")
        return []


def get_quoted_state_from_api(token_in, token_out, amount_in):
    """Get quoted state from the new quote-engine API."""
    try:
        api_url = f"{QUOTE_ENGINE_BASE_URL}/quote"
        payload = {
            "input_token": token_in,
            "output_token": token_out,
            "amount_in": str(amount_in)
        }
        
        response = requests.post(api_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Failed to get quote from API: {e}")
        return None


def create_tvl_histogram(bins_data, title, token0="BTC", token1="USDC", used_bin_ids=None, bin_step=None):
    """Create TVL histogram visualization with stacked bars for active bin."""
    if not bins_data:
        return go.Figure()
    
    # Prepare data for plotting
    bin_ids = [bin_data['bin_id'] for bin_data in bins_data]
    x_amounts = [bin_data['x_amount'] for bin_data in bins_data]
    y_amounts = [bin_data['y_amount'] for bin_data in bins_data]
    prices = [bin_data['price'] for bin_data in bins_data]
    is_active = [bin_data.get('is_active', False) for bin_data in bins_data]
    
    # Use amounts as-is since Redis data is already in raw units
    # No need to divide by decimal factors
    x_amounts_readable = x_amounts
    y_amounts_readable = y_amounts
    
    # Create figure
    fig = go.Figure()
    
    # Separate active bin data from other bins
    active_bin_data = []
    other_bin_data = []
    
    for i, (bin_id, x_readable, y_readable, price, active) in enumerate(zip(bin_ids, x_amounts_readable, y_amounts_readable, prices, is_active)):
        if active:
            active_bin_data.append({
                'bin_id': bin_id,
                'x_amount': x_readable,
                'y_amount': y_readable,
                'price': price,
                'is_used': bin_id in (used_bin_ids or set())
            })
        else:
            # For non-active bins, determine which token is present and calculate total liquidity
            if x_readable > 0:  # X tokens only
                total_liquidity = x_readable * price  # Convert to USDC equivalent
                token_type = 'x'
                token_amount = x_readable
            else:  # Y tokens only
                total_liquidity = y_readable
                token_type = 'y'
                token_amount = y_readable
            
            other_bin_data.append({
                'bin_id': bin_id,
                'total_liquidity': total_liquidity,
                'price': price,
                'token_type': token_type,
                'token_amount': token_amount,
                'is_used': bin_id in (used_bin_ids or set())
            })
    
    # Add bars for non-active bins (single color)
    if other_bin_data:
        other_bin_ids = [data['bin_id'] for data in other_bin_data]
        other_liquidity = [data['total_liquidity'] for data in other_bin_data]
        
        # Color coding for non-active bins
        other_colors = []
        for data in other_bin_data:
            if data['is_used']:
                other_colors.append('#FF6B6B')  # Coral red for used bins
            elif data['token_type'] == 'x':
                other_colors.append('#FF9F43')  # Orange for X tokens (BTC/ETH/SOL)
            else:
                other_colors.append('#10AC84')  # Green for Y tokens (USDC)
        
        fig.add_trace(
            go.Bar(
                x=other_bin_ids,
                y=other_liquidity,
                name='Other Bins',
                marker_color=other_colors,
                opacity=0.8,
                hovertemplate=(
                    '<b>Bin %{x}</b><br>' +
                    'Token: %{customdata[0]}<br>' +
                    '%{customdata[1]} Amount: %{customdata[2]}<br>' +
                    'Dollar Value: $%{customdata[3]}<br>' +
                    'Price: $%{customdata[4]}<br>' +
                    '<extra></extra>'
                ),
                customdata=[[
                    token0 if data['token_type'] == 'x' else token1,
                    token0 if data['token_type'] == 'x' else token1,
                    f"{data['token_amount']:.8f}" if data['token_type'] == 'x' else f"{data['token_amount']:.2f}",
                    format_number_with_commas(data['total_liquidity']),
                    format_number_with_commas(data['price'])
                ] for data in other_bin_data]
            )
        )
    
    # Add stacked bars for active bin
    if active_bin_data:
        active_data = active_bin_data[0]  # Should only be one active bin
        active_bin_id = active_data['bin_id']
        
        # Convert X tokens to USDC equivalent for stacking
        x_usdc_equivalent = active_data['x_amount'] * active_data['price']
        y_amount = active_data['y_amount']
        
        # Color for active bin
        active_color = 'red' if active_data['is_used'] else 'green'
        
        # Add X tokens (bottom of stack)
        fig.add_trace(
            go.Bar(
                x=[active_bin_id],
                y=[x_usdc_equivalent],
                name=f'{token0} (Active)',
                marker_color='#FF9F43',  # Orange for X tokens
                opacity=0.8,
                hovertemplate=(
                    f'<b>Bin {active_bin_id} - {token0}</b><br>' +
                    f'{token0} Amount: {active_data["x_amount"]:.4f}<br>' +
                    f'{token0} Dollar Value: ${format_number_with_commas(x_usdc_equivalent)}<br>' +
                    f'Price: ${format_number_with_commas(active_data["price"])}<br>' +
                    '<extra></extra>'
                )
            )
        )
        
        # Add Y tokens (top of stack)
        fig.add_trace(
            go.Bar(
                x=[active_bin_id],
                y=[y_amount],
                name=f'{token1} (Active)',
                marker_color='#10AC84',  # Green for Y tokens
                opacity=0.8,
                hovertemplate=(
                    f'<b>Bin {active_bin_id} - {token1}</b><br>' +
                    f'{token1} Amount: {format_number_with_commas(y_amount)}<br>' +
                    f'{token1} Dollar Value: ${format_number_with_commas(y_amount)}<br>' +
                    f'Price: ${format_number_with_commas(active_data["price"])}<br>' +
                    '<extra></extra>'
                )
            )
        )
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Bin ID",
        yaxis_title="Liquidity (USDC)",
        showlegend=True,
        height=500,
        hovermode='x unified',
        barmode='stack'  # Enable stacking for active bin
    )
    
    # Add annotation for active bin if present
    if active_bin_data:
        active_data = active_bin_data[0]
        active_bin_id = active_data['bin_id']
        x_usdc_equivalent = active_data['x_amount'] * active_data['price']
        y_amount = active_data['y_amount']
        total_liquidity = x_usdc_equivalent + y_amount
        
        fig.add_annotation(
            x=active_bin_id,
            y=total_liquidity * 1.05,
            text=f"Active Bin<br>{token0}: {active_data['x_amount']:.2f}<br>{token1}: {format_number_with_commas(y_amount)}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="green",
            arrowwidth=2,
            bgcolor="green",
            bordercolor="white",
            borderwidth=1,
            font=dict(color="white", size=10)
        )
    
    return fig


def main():
    st.set_page_config(
        page_title="DLMM Pool Visualization & Quote Testing",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("DLMM Pool Visualization & Quote Testing")
    st.markdown("Interactive pool state visualization and comprehensive quote testing with multi-hop routing")
    st.markdown("**Updated for Task 003: Integration with new quote-engine infrastructure**")
    
    # Check API connection
    try:
        health_response = requests.get(f"{QUOTE_ENGINE_BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            st.error("❌ Quote engine API is not responding properly. Please ensure the quote-engine is running.")
            st.stop()
    except Exception as e:
        st.error("❌ Cannot connect to quote-engine API. Please start the quote-engine with: `cd quote-engine && python main.py`")
        st.stop()
    
    # Get available pools from API
    available_pools = get_available_pools_from_api()
    if not available_pools:
        st.error("❌ No pools found via API. Please ensure the quote-engine is running and has data.")
        st.stop()
    
    # Pool Visualization Section
    st.markdown("---")
    st.subheader("📈 Pool State Visualization")
    
    # Show all available pools
    st.write("**Available Pools:**")
    for pool in available_pools:
        st.write(f"- {pool['pool_id']} ({pool['token0']}/{pool['token1']}) - Active Bin: {pool['active_bin']}")
    
    # Create tabs for each pool
    # Sort pools to put BTC-USDC-25 first as default
    sorted_pools = sorted(available_pools, key=lambda x: x['pool_id'] != 'BTC-USDC-25')
    pool_tabs = st.tabs([pool['pool_id'] for pool in sorted_pools])
    
    for i, (pool, tab) in enumerate(zip(sorted_pools, pool_tabs)):
        with tab:
            pool_id = pool['pool_id']
            current_bins = get_bin_data_from_redis(pool_id, bin_range=20)
            
            if current_bins:
                # Create current state visualization
                current_fig = create_tvl_histogram(
                    current_bins,
                    f"Pool State - {pool_id}",
                    pool['token0'],
                    pool['token1']
                )
                
                st.plotly_chart(current_fig, use_container_width=True)
                
                # Show pool stats
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Active Bin", pool['active_bin'])
                with col2:
                    st.metric("Bin Step", f"{pool['bin_step']*100:.2f}%")
                with col3:
                    st.metric("Protocol Fee", f"{pool['x_protocol_fee']} bps")
                with col4:
                    st.metric("Provider Fee", f"{pool['x_provider_fee']} bps")
            else:
                st.error(f"❌ No bin data available for {pool_id}")
    
    # Quote Testing Section
    st.markdown("---")
    st.subheader("🔍 Quote Testing")
    
    # Get all available tokens from all pools
    all_tokens = set()
    for pool in available_pools:
        all_tokens.add(pool['token0'])
        all_tokens.add(pool['token1'])
    all_tokens = sorted(list(all_tokens))  # Sort for consistent order
    
    # Create a clean, card-like quote testing interface
    with st.container():
        st.markdown("### 💱 Swap Configuration")
        
        # Token selection in a more intuitive layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**From:**")
            token_in = st.selectbox(
                "Select token to swap from",
                all_tokens,
                key="quote_token_in",
                label_visibility="collapsed"
            )
        
        with col2:
            st.markdown("**To:**")
            token_out = st.selectbox(
                "Select token to swap to",
                all_tokens,
                index=1 if token_in == all_tokens[0] else 0,
                key="quote_token_out",
                label_visibility="collapsed"
            )
        
        # Amount input with better labeling
        st.markdown("**Amount:**")
        
        # Determine appropriate amount range based on token
        if token_in == "BTC":
            amount_in = st.number_input(
                f"Enter {token_in} amount",
                min_value=0.0,
                max_value=None,
                value=1.0,
                step=0.1,
                key="quote_amount_in",
                label_visibility="collapsed"
            )
            amount_in_atomic = int(amount_in)  # Send raw BTC amount
        elif token_in == "ETH":
            amount_in = st.number_input(
                f"Enter {token_in} amount",
                min_value=0.0,
                max_value=None,
                value=1.0,
                step=0.1,
                key="quote_amount_in",
                label_visibility="collapsed"
            )
            amount_in_atomic = int(amount_in)  # Send raw ETH amount
        elif token_in == "SOL":
            amount_in = st.number_input(
                f"Enter {token_in} amount",
                min_value=0.0,
                max_value=None,
                value=10.0,
                step=1.0,
                key="quote_amount_in",
                label_visibility="collapsed"
            )
            amount_in_atomic = int(amount_in)  # Send raw SOL amount
        else:  # USDC
            amount_in = st.number_input(
                f"Enter {token_in} amount",
                min_value=0.0,
                max_value=None,
                value=1000.0,
                step=100.0,
                key="quote_amount_in",
                label_visibility="collapsed"
            )
            amount_in_atomic = int(amount_in)  # Send raw USDC amount
        
        # Quote button with better styling
        st.markdown("")
        if st.button("🚀 Get Quote", key="quote_btn", type="primary", use_container_width=True):
            quote_data = get_quoted_state_from_api(token_in, token_out, amount_in_atomic)
            
            if quote_data and quote_data.get('success'):
                st.success("✅ Quote Generated Successfully!")
                
                # Get decimal information from API response
                input_decimals = quote_data.get('input_token_decimals')
                output_decimals = quote_data.get('output_token_decimals')
                
                # Display quote results in a clean, card-like format
                st.markdown("### 📊 Quote Results")
                
                # Create a more visually appealing metrics display
                with st.container():
                    # Main quote info in a highlighted box
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric(
                            "You'll Receive",
                            format_amount(quote_data['amount_out'], token_out, output_decimals),
                            help=f"Amount of {token_out} you will receive"
                        )
                    
                    with col2:
                        st.metric(
                            "Total Fee",
                            format_amount(quote_data['fee'], token_out, output_decimals),
                            help=f"Total fee paid in {token_out}"
                        )
                    
                    # Additional info in a more subtle way
                    st.markdown(f"**Route:** {' → '.join(quote_data['route_path'])}")
                    st.markdown(f"**Price Impact:** {quote_data.get('price_impact_bps', 0)} bps")
                
                # Show execution path details in a cleaner format
                st.markdown("### 🔧 Execution Details")
                execution_path = quote_data.get('execution_path', [])
                
                if execution_path:
                    for i, step in enumerate(execution_path):
                        with st.expander(f"Step {i+1}: {step.get('function_name', 'Unknown')} on {step.get('pool_trait', 'Unknown')}", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Pool:** {step.get('pool_trait', 'Unknown')}")
                                st.markdown(f"**Bin ID:** {step.get('bin_id', 'Unknown')}")
                            
                            with col2:
                                if step.get('x_amount'):
                                    st.markdown(f"**Amount:** {format_amount(str(step['x_amount']), token_in, input_decimals)}")
                                elif step.get('y_amount'):
                                    st.markdown(f"**Amount:** {format_amount(str(step['y_amount']), token_out, output_decimals)}")
                                
                                # Visual indicator
                                if step.get('function_name') == 'swap-x-for-y':
                                    st.markdown("**Direction:** 🔄 X → Y")
                                elif step.get('function_name') == 'swap-y-for-x':
                                    st.markdown("**Direction:** 🔄 Y → X")
                else:
                    st.info("No execution path details available")
            else:
                st.error("❌ Failed to generate quote")
                if quote_data:
                    st.error(f"Error: {quote_data.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 