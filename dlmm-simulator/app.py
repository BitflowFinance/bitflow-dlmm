#!/usr/bin/env python3
"""
DLMM Visualization Tool
Shows current pool state vs quoted swap impact using API data
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


def get_pool_data_from_api(pool_id):
    """Get pool data from the API server."""
    try:
        api_url = f"http://localhost:8000/pools/{pool_id}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Failed to get pool data from API: {e}")
        return None


def get_bin_data_from_api(pool_id, bin_range=20):
    """Get bin data from the API server for visualization."""
    try:
        # Get pool data first to find active bin
        pool_data = get_pool_data_from_api(pool_id)
        if not pool_data:
            return []
        
        active_bin_id = pool_data.get('active_bin_id', 500)
        start_bin = active_bin_id - bin_range
        end_bin = active_bin_id + bin_range
        
        # The API returns all bins for the pool, so we'll filter them
        bins_data = []
        for bin_data in pool_data.get('bins', []):
            bin_id = bin_data.get('bin_id', 0)
            if start_bin <= bin_id <= end_bin:
                bins_data.append({
                    'bin_id': bin_id,
                    'x_amount': bin_data.get('x_amount', 0),
                    'y_amount': bin_data.get('y_amount', 0),
                    'price': bin_data.get('price', 0),
                    'total_liquidity': bin_data.get('x_amount', 0) + (bin_data.get('y_amount', 0) / bin_data.get('price', 1)),
                    'is_active': bin_data.get('is_active', False)
                })
        
        return bins_data
    except Exception as e:
        st.error(f"Failed to get bin data from API: {e}")
        return []


def get_available_pools_from_api():
    """Get list of available pools from the API server."""
    try:
        api_url = "http://localhost:8000/pools"
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
    """Get quoted state from the API server."""
    try:
        api_url = "http://localhost:8000/quote"
        payload = {
            "token_in": token_in,
            "token_out": token_out,
            "amount_in": amount_in
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


def calculate_quoted_bin_state(current_bins, quote_data, direction):
    """Calculate what bins would look like after a quoted swap."""
    if not quote_data or not quote_data.get('success'):
        return None, None, None
    
    quoted_bins = []
    used_bin_ids = set()
    
    # Create a mapping of bin_id to current data for easy lookup
    current_bin_map = {bin_data['bin_id']: bin_data for bin_data in current_bins}
    
    # Process each current bin
    for bin_data in current_bins:
        bin_id = bin_data['bin_id']
        quoted_bin = bin_data.copy()
        
        # Find if this bin was used in the quote
        for step in quote_data.get('steps', []):
            if step.get('bin_id') == bin_id:
                used_bin_ids.add(bin_id)
                
                # Tokens leaving the bin (input tokens)
                if direction == "X→Y":
                    quoted_bin['x_amount'] += step.get('amount_in', 0)  # X tokens added to pool
                    quoted_bin['y_amount'] -= step.get('amount_out', 0)  # Y tokens removed from pool
                else:  # Y→X
                    quoted_bin['y_amount'] += step.get('amount_in', 0)  # Y tokens added to pool
                    quoted_bin['x_amount'] -= step.get('amount_out', 0)  # X tokens removed from pool
                break
        
        # Ensure amounts don't go negative
        quoted_bin['x_amount'] = max(0, quoted_bin['x_amount'])
        quoted_bin['y_amount'] = max(0, quoted_bin['y_amount'])
        
        # Recalculate total liquidity based on the new token amounts
        quoted_bin['total_liquidity'] = quoted_bin['x_amount'] + (quoted_bin['y_amount'] / quoted_bin['price'])
        
        quoted_bins.append(quoted_bin)
    
    # Determine the new active bin based on the quoted state
    new_active_bin_id = None
    if quote_data.get('steps'):
        # Use the last bin that was used in the swap as the new active bin
        new_active_bin_id = quote_data['steps'][-1].get('bin_id')
    
    # Update the is_active flag for all bins
    for bin_data in quoted_bins:
        bin_data['is_active'] = (bin_data['bin_id'] == new_active_bin_id)
    
    return quoted_bins, used_bin_ids, new_active_bin_id


def create_tvl_histogram(bins_data, title, token0="BTC", token1="USDC", used_bin_ids=None, bin_step=None):
    """Create TVL histogram using Plotly."""
    if not bins_data:
        return go.Figure()
    
    df = pd.DataFrame(bins_data)
    
    # Find the active bin from the data
    active_bin_data = df[df['is_active']]
    if len(active_bin_data) == 0:
        # Fallback to highest liquidity bin if no active bin marked
        active_bin_data = df.loc[df['total_liquidity'].idxmax()]
        active_bin_id = active_bin_data['bin_id']
    else:
        active_bin_id = active_bin_data['bin_id'].iloc[0]
    
    # Create figure with secondary y-axis
    fig = go.Figure()
    
    # Process each bin based on its actual token content
    for _, bin_data in df.iterrows():
        bin_id = bin_data['bin_id']
        price = bin_data['price']
        x_amount = bin_data['x_amount']
        y_amount = bin_data['y_amount']
        is_active = bin_data['is_active']
        
        # Calculate USD values
        x_usd_value = x_amount * price
        
        # Add X tokens if present
        if x_amount > 0:
            trace_name = f'X Tokens ({token0})'
            if is_active:
                trace_name += ' - Active'
            
            fig.add_trace(go.Bar(
                x=[price],
                y=[x_usd_value],
                name=trace_name,
                marker_color='#ff7f0e',
                opacity=0.8,
                hovertemplate=f'<b>Price: $%{{x:,.2f}}</b><br>' +
                             f'X Tokens: %{{customdata[0]:.4f}} {token0}<br>' +
                             f'X Value: $%{{y:,.0f}}<br>' +
                             f'Bin ID: %{{customdata[1]}}<extra></extra>',
                customdata=[[x_amount, bin_id]],
                showlegend=False if not is_active else True
            ))
        
        # Add Y tokens if present
        if y_amount > 0:
            trace_name = f'Y Tokens ({token1})'
            if is_active:
                trace_name += ' - Active'
            
            fig.add_trace(go.Bar(
                x=[price],
                y=[y_amount],
                name=trace_name,
                marker_color='#1f77b4',
                opacity=0.8,
                hovertemplate=f'<b>Price: $%{{x:,.2f}}</b><br>' +
                             f'Y Tokens: %{{y:,.0f}} {token1}<br>' +
                             f'Y Value: $%{{y:,.0f}}<br>' +
                             f'Bin ID: %{{customdata}}<extra></extra>',
                customdata=[bin_id],
                showlegend=False if not is_active else True
            ))
    
    # Highlight active bin
    active_bin = df[df['bin_id'] == active_bin_id]
    if len(active_bin) > 0:
        active_price = active_bin['price'].iloc[0]
        fig.add_vline(
            x=active_price,
            line_dash="dash",
            line_color="#2ca02c",
            annotation_text="Active Bin",
            annotation_position="top right"
        )
    
    # Highlight used bins if provided
    if used_bin_ids and bin_step is not None:
        for bin_id in used_bin_ids:
            bin_data = df[df['bin_id'] == bin_id]
            if len(bin_data) > 0:
                bin_price = bin_data['price'].iloc[0]
                
                # Calculate proper bin boundaries based on bin step
                bin_width = bin_price * bin_step * 0.5  # Half the bin step distance
                
                fig.add_vrect(
                    x0=bin_price - bin_width,
                    x1=bin_price + bin_width,
                    fillcolor="rgba(44, 160, 44, 0.2)",
                    layer="below",
                    line_width=0
                )
    
    fig.update_layout(
        title=title,
        xaxis_title=f"{token0}/USD Price",
        yaxis_title="TVL (USD)",
        barmode='stack',
        height=400,
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig


def generate_random_fuzz_swap(pool_data):
    """Generate a random large swap for fuzz testing."""
    token_x = pool_data.get('token_x', 'BTC')
    token_y = pool_data.get('token_y', 'USDC')
    
    # Random direction
    direction = random.choice(['X→Y', 'Y→X'])
    
    # Extract token information
    token0 = pool_data.get('token0', 'BTC')
    token1 = pool_data.get('token1', 'USDC')
    
    # Determine swap direction based on token types
    if direction == "X to Y":
        token_in, token_out = token0, token1
        if token0 == 'BTC':
            amount_in = 1.0
        elif token0 == 'ETH':
            amount_in = 10.0
        elif token0 == 'SOL':
            amount_in = 100.0
        else:
            amount_in = 1.0
    else:  # Y to X
        token_in, token_out = token1, token0
        if token1 == 'USDC':
            amount_in = 50000.0
        else:
            amount_in = 1000.0
    
    return {
        'token_in': token_in,
        'token_out': token_out,
        'amount_in': amount_in,
        'direction': direction,
        'description': f"Random {direction} swap: {amount_in:,.2f} {token_in}"
    }


def main():
    st.set_page_config(
        page_title="DLMM Real-Time Fuzz Testing",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("DLMM Real-Time Fuzz Testing & Pool Visualization")
    st.markdown("Watch pool state change in real-time as automatic fuzz tests are applied")
    
    # Check API connection
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code != 200:
            st.error("❌ API server is not responding properly. Please ensure the API server is running.")
            st.stop()
    except Exception as e:
        st.error("❌ Cannot connect to API server. Please start the API server with: `python api_server.py`")
        st.stop()
    
    # Get available pools from API
    available_pools = get_available_pools_from_api()
    if not available_pools:
        st.error("❌ No pools found via API. Please ensure the API server is running and has data.")
        st.stop()
    
    # Initialize session state
    if 'fuzz_running' not in st.session_state:
        st.session_state.fuzz_running = False
    if 'selected_pool_id' not in st.session_state:
        st.session_state.selected_pool_id = None
    if 'fuzz_history' not in st.session_state:
        st.session_state.fuzz_history = []
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()
    if 'update_counter' not in st.session_state:
        st.session_state.update_counter = 0
    if 'last_pool_data' not in st.session_state:
        st.session_state.last_pool_data = None
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    
    # Real-Time Fuzz Testing Section
    st.markdown("---")
    st.subheader("🧪 Real-Time Fuzz Testing")
    
    # Pool selection for fuzz testing
    pool_options = [f"{pool['pool_id']} ({pool['token0']}/{pool['token1']})" for pool in available_pools]
    # Default to BTC-USDC-25 if present
    default_pool_id = "BTC-USDC-25"
    default_index = 0
    for i, pool in enumerate(available_pools):
        if pool['pool_id'] == default_pool_id:
            default_index = i
            break
    selected_pool_option = st.selectbox(
        "Select Pool for Fuzz Testing",
        pool_options,
        index=default_index,
        key="fuzz_pool_select"
    )
    
    if selected_pool_option:
        selected_pool_id = selected_pool_option.split(" (")[0]
        selected_pool = next((p for p in available_pools if p['pool_id'] == selected_pool_id), None)
        
        if selected_pool:
            st.session_state.selected_pool_id = selected_pool_id
            
            # Fuzz testing controls
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🚀 Start Monitoring", key="start_fuzz_btn"):
                    st.session_state.fuzz_running = True
                    st.session_state.fuzz_history = []
                    st.session_state.update_counter = 0
                    st.session_state.auto_refresh = True
                    st.rerun()
            
            with col2:
                if st.button("⏹️ Stop Monitoring", key="stop_fuzz_btn"):
                    st.session_state.fuzz_running = False
                    st.session_state.auto_refresh = False
                    st.rerun()
            
            with col3:
                if st.button("🔄 Clear History", key="clear_history_btn"):
                    st.session_state.fuzz_history = []
                    st.rerun()
            
            with col4:
                if st.button("🔄 Force Update", key="force_update_btn"):
                    st.session_state.last_update = 0  # Force refresh
                    st.rerun()
            
            # Show fuzz testing status
            if st.session_state.fuzz_running:
                st.success("🟢 **Real-Time Monitoring Active** - Pool state updating every 5 seconds")
                
                # Auto-refresh logic using Streamlit's built-in mechanism
                current_time = time.time()
                time_since_update = current_time - st.session_state.last_update
                
                # Debug info
                st.info(f"⏱️ **Debug Info:** Time since last update: {time_since_update:.1f}s | Update counter: {st.session_state.update_counter}")
                
                # Auto-refresh the page every 5 seconds when monitoring is active
                if st.session_state.auto_refresh:
                    st.markdown("""
                    <script>
                    // Auto-refresh every 5 seconds when monitoring is active
                    setTimeout(function() {
                        window.location.reload();
                    }, 5000);
                    </script>
                    """, unsafe_allow_html=True)
            else:
                st.info("⏸️ **Real-Time Monitoring Paused** - Click 'Start Monitoring' to begin")
            
            # Display current pool state
            st.markdown("---")
            st.subheader(f"📊 Real-Time Pool State: {selected_pool_id}")
            
            # Get current pool data
            pool_data = get_pool_data_from_api(selected_pool_id)
            
            # Check if data has changed
            data_changed = False
            if pool_data and st.session_state.last_pool_data:
                if pool_data.get('active_bin_id') != st.session_state.last_pool_data.get('active_bin_id'):
                    data_changed = True
                    st.success(f"🔄 **Data Changed!** Active bin moved from {st.session_state.last_pool_data.get('active_bin_id')} to {pool_data.get('active_bin_id')}")
            
            st.session_state.last_pool_data = pool_data
            
            # Sidebar controls for visualization
            st.sidebar.header("Visualization Controls")
            
            # Bin range input
            bin_range = st.sidebar.number_input(
                "Bin Range to Display",
                min_value=10,
                max_value=500,
                value=200,
                step=10,
                help="Number of bins to show on each side of the active bin"
            )
            
            # Get current state
            current_bins = get_bin_data_from_api(selected_pool_id, bin_range)
            
            if current_bins:
                # Calculate total TVL
                total_x = sum(bin['x_amount'] for bin in current_bins)
                total_y = sum(bin['y_amount'] for bin in current_bins)
                
                # Calculate total TVL in USD
                active_bin = next((bin for bin in current_bins if bin['is_active']), None)
                if active_bin:
                    total_tvl_usd = (total_x * active_bin['price']) + total_y
                else:
                    total_tvl_usd = 0
                
                # Stats bar across the top
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total TVL", f"${total_tvl_usd:,.0f}")
                
                with col2:
                    st.metric(f"Total {selected_pool['token0']}", f"{total_x:.2f}")
                
                with col3:
                    st.metric(f"Total {selected_pool['token1']}", f"{total_y:,.0f}")
                
                with col4:
                    if active_bin:
                        st.metric("Active Bin Price", f"${active_bin['price']:,.2f}")
                    else:
                        st.metric("Active Bin Price", "N/A")
                
                st.markdown("---")
                
                # Create the histogram with auto-refresh container
                st.subheader("Current Pool Liquidity Distribution")
                st.markdown(f"*Note: Chart shows TVL in USD with {selected_pool['token0']}/USD price on X-axis. Updates every 5 seconds during fuzz testing.*")
                
                # Use a container for the chart that can be updated
                chart_container = st.empty()
                
                current_fig = create_tvl_histogram(
                    current_bins, 
                    f"Real-Time Pool Liquidity - {selected_pool_id} (Update #{st.session_state.update_counter})", 
                    token0=selected_pool['token0'],
                    token1=selected_pool['token1'],
                    bin_step=pool_data.get('bin_step', 25) if pool_data else 25
                )
                chart_container.plotly_chart(current_fig, use_container_width=True)
                
                # Show data freshness info
                if pool_data:
                    st.info(f"📅 **Pool Active Bin:** {pool_data.get('active_bin_id', 'Unknown')} | **Price:** ${pool_data.get('active_bin_price', 0):,.2f}")
            else:
                st.error(f"No bin data found for pool {selected_pool_id}")
        else:
            st.error("Selected pool not found")
    else:
        st.info("Please select a pool to begin fuzz testing")
    
    # Manual Quote Engine Section (for comparison)
    st.markdown("---")
    st.subheader("🚀 Manual Quote Engine (for comparison)")
    
    # Quote Engine Interface
    col1, col2, col3 = st.columns(3)
    
    with col1:
        token_in = st.selectbox(
            "Token In",
            ["BTC", "ETH", "USDC", "SOL"],
            key="token_in_select"
        )
    
    with col2:
        token_out = st.selectbox(
            "Token Out", 
            ["BTC", "ETH", "USDC", "SOL"],
            key="token_out_select"
        )
    
    with col3:
        amount_in = st.number_input(
            "Amount In",
            min_value=0.01,
            value=1.0,
            step=0.01,
            key="amount_in_input"
        )
    
    # Get Quote Button
    if st.button("Get Manual Quote", key="get_quote_btn"):
        if token_in == token_out:
            st.error("Token In and Token Out must be different!")
        else:
            quote_data = get_quoted_state_from_api(token_in, token_out, amount_in)
            if quote_data:
                st.session_state.last_quote = quote_data
                st.rerun()
    
    # Display Quote Results
    if 'last_quote' in st.session_state and st.session_state.last_quote:
        quote = st.session_state.last_quote
        
        if quote.get('success'):
            st.success("✅ Manual Quote Retrieved Successfully!")
            
            # Quote details in columns
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Amount Out",
                    f"{quote.get('amount_out', 0):.6f} {token_out}",
                    help="Amount of output tokens you'll receive"
                )
            
            with col2:
                effective_price = quote.get('amount_out', 0) / quote.get('amount_in', 1) if quote.get('amount_in', 0) > 0 else 0
                st.metric(
                    "Effective Price",
                    f"${effective_price:.2f}",
                    help="Price per input token"
                )
            
            with col3:
                st.metric(
                    "Price Impact",
                    f"{quote.get('price_impact', 0):.4f}%",
                    help="Price impact of this trade"
                )
            
            with col4:
                st.metric(
                    "Route Type",
                    quote.get('route_type', 'unknown'),
                    help="Type of routing used"
                )
            
            # Show route steps
            if quote.get('steps'):
                st.subheader("Manual Quote Route Steps")
                for i, step in enumerate(quote['steps']):
                    with st.expander(f"Step {i+1}: {step.get('pool_id', '')} (Bin {step.get('bin_id', '')})"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Input:** {step.get('amount_in', 0):.6f} {step.get('token_in', '')}")
                        with col2:
                            st.write(f"**Output:** {step.get('amount_out', 0):.6f} {step.get('token_out', '')}")
                        with col3:
                            st.write(f"**Price:** ${step.get('price', 0):.2f}")
        else:
            st.error(f"❌ Manual Quote Failed: {quote.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 