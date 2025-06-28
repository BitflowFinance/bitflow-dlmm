#!/usr/bin/env python3
"""
DLMM Visualization Tool
Shows current pool state vs quoted swap impact
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pool import MockPool
from src.routing import SinglePoolRouter


def create_pool(pool_type="bell_curve"):
    """Create a mock pool for visualization."""
    if pool_type == "bell_curve":
        return MockPool.create_bell_curve_pool()
    elif pool_type == "uniform":
        return MockPool.create_uniform_pool()
    else:
        return MockPool.create_bell_curve_pool()  # Default fallback


def get_bin_data_for_viz(pool, bin_range=20):
    """Get bin data for visualization."""
    active_bin_id = pool.config.active_bin_id
    start_bin = active_bin_id - bin_range
    end_bin = active_bin_id + bin_range
    
    bins_data = []
    for bin_id in range(start_bin, end_bin + 1):
        bin_data = pool.get_bin(bin_id)
        if bin_data:
            bins_data.append({
                'bin_id': bin_id,
                'x_amount': bin_data.x_amount,
                'y_amount': bin_data.y_amount,
                'price': bin_data.price,
                'total_liquidity': bin_data.total_liquidity,
                'is_active': bin_id == active_bin_id
            })
    
    return bins_data


def create_tvl_histogram(bins_data, title, used_bins=None):
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
            trace_name = 'X Tokens (BTC)'
            if is_active:
                trace_name += ' - Active'
            
            fig.add_trace(go.Bar(
                x=[price],
                y=[x_usd_value],
                name=trace_name,
                marker_color='#ff7f0e',
                opacity=0.8,
                hovertemplate='<b>Price: $%{x:,.2f}</b><br>' +
                             'X Tokens: %{customdata[0]:.4f} BTC<br>' +
                             'X Value: $%{y:,.0f}<br>' +
                             'Bin ID: %{customdata[1]}<extra></extra>',
                customdata=[[x_amount, bin_id]],
                showlegend=False if not is_active else True
            ))
        
        # Add Y tokens if present
        if y_amount > 0:
            trace_name = 'Y Tokens (USDC)'
            if is_active:
                trace_name += ' - Active'
            
            fig.add_trace(go.Bar(
                x=[price],
                y=[y_amount],
                name=trace_name,
                marker_color='#1f77b4',
                opacity=0.8,
                hovertemplate='<b>Price: $%{x:,.2f}</b><br>' +
                             'Y Tokens: %{y:,.0f} USDC<br>' +
                             'Y Value: $%{y:,.0f}<br>' +
                             'Bin ID: %{customdata}<extra></extra>',
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
    if used_bins:
        for bin_id in used_bins:
            bin_data = df[df['bin_id'] == bin_id]
            if len(bin_data) > 0:
                bin_price = bin_data['price'].iloc[0]
                fig.add_vrect(
                    x0=bin_price-0.5,
                    x1=bin_price+0.5,
                    fillcolor="rgba(44, 160, 44, 0.2)",
                    layer="below",
                    line_width=0
                )
    
    fig.update_layout(
        title=title,
        xaxis_title="BTC/USD Price",
        yaxis_title="TVL (USD)",
        barmode='stack',
        height=400,
        showlegend=True,
        hovermode='x unified'
    )
    
    return fig


def get_quoted_bin_state(pool, amount, direction, bin_range=500):
    """Get what bins would look like after a quoted swap."""
    router = SinglePoolRouter(pool)
    
    if direction == "X→Y":
        token_in, token_out = pool.config.x_token, pool.config.y_token
    else:
        token_in, token_out = pool.config.y_token, pool.config.x_token
    
    quote = router.get_quote(token_in, amount, token_out)
    
    if not quote.success:
        return None, quote
    
    # Get current bin data using the same bin range as the visualization
    current_bins = get_bin_data_for_viz(pool, bin_range)
    original_active_bin_id = pool.config.active_bin_id
    
    # Create quoted state by accounting for both tokens leaving and entering
    quoted_bins = []
    used_bin_ids = set()
    
    # Create a mapping of bin_id to current data for easy lookup
    current_bin_map = {bin_data['bin_id']: bin_data for bin_data in current_bins}
    
    for bin_data in current_bins:
        bin_id = bin_data['bin_id']
        quoted_bin = bin_data.copy()
        
        # Find if this bin was used in the quote
        for step in quote.steps:
            if step.bin_id == bin_id:
                used_bin_ids.add(bin_id)
                
                # Tokens leaving the bin (input tokens)
                if direction == "X→Y":
                    quoted_bin['x_amount'] += step.amount_in  # X tokens added to pool
                    quoted_bin['y_amount'] -= step.amount_out  # Y tokens removed from pool
                else:  # Y→X
                    quoted_bin['y_amount'] += step.amount_in  # Y tokens added to pool
                    quoted_bin['x_amount'] -= step.amount_out  # X tokens removed from pool
                break
        
        # Ensure amounts don't go negative
        quoted_bin['x_amount'] = max(0, quoted_bin['x_amount'])
        quoted_bin['y_amount'] = max(0, quoted_bin['y_amount'])
        
        # Recalculate total liquidity based on the new token amounts
        # Total liquidity = X tokens + (Y tokens / price)
        quoted_bin['total_liquidity'] = quoted_bin['x_amount'] + (quoted_bin['y_amount'] / quoted_bin['price'])
        
        quoted_bins.append(quoted_bin)
    
    # Determine the new active bin based on the quoted state
    # For X→Y swaps: active bin moves right (higher bin index, higher price)
    # For Y→X swaps: active bin moves left (lower bin index, lower price)
    if quote.steps:
        # Use the last bin that was used in the swap as the new active bin
        new_active_bin_id = quote.steps[-1].bin_id
    else:
        # If no steps, keep the original active bin
        new_active_bin_id = original_active_bin_id
    
    # Debug: Print the liquidity values to understand what's happening
    print(f"Original active bin: {original_active_bin_id}")
    print(f"New active bin: {new_active_bin_id}")
    print("Liquidity values:")
    for bin_data in sorted(quoted_bins, key=lambda x: x['bin_id']):
        if bin_data['total_liquidity'] > 0:
            print(f"  Bin {bin_data['bin_id']}: {bin_data['total_liquidity']:.2f} (X: {bin_data['x_amount']:.2f}, Y: {bin_data['y_amount']:.2f})")
    
    # Update the is_active flag for all bins
    for bin_data in quoted_bins:
        bin_data['is_active'] = (bin_data['bin_id'] == new_active_bin_id)
    
    return quoted_bins, quote, used_bin_ids, new_active_bin_id


def main():
    st.set_page_config(
        page_title="DLMM Visualization",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("DLMM Pool Visualization")
    st.markdown("Visualize the impact of quoted swaps on pool liquidity distribution")
    
    # Initialize session state
    if 'pool' not in st.session_state:
        st.session_state.pool = create_pool()
    if 'amount' not in st.session_state:
        st.session_state.amount = 0.0
    if 'direction' not in st.session_state:
        st.session_state.direction = "X→Y"
    if 'pool_type' not in st.session_state:
        st.session_state.pool_type = "bell_curve"
    
    # Sidebar controls
    st.sidebar.header("Swap Controls")
    
    # Pool type selection
    st.sidebar.subheader("Pool Distribution")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Bell Curve", key="bell_curve_btn"):
            st.session_state.pool_type = "bell_curve"
            st.session_state.pool = create_pool("bell_curve")
            st.session_state.amount = 0.0
            st.rerun()
    
    with col2:
        if st.button("Uniform", key="uniform_btn"):
            st.session_state.pool_type = "uniform"
            st.session_state.pool = create_pool("uniform")
            st.session_state.amount = 0.0
            st.rerun()
    
    # Show current pool type
    st.sidebar.markdown(f"**Current: {st.session_state.pool_type.replace('_', ' ').title()}**")
    
    # Bin range input
    bin_range = st.sidebar.number_input(
        "Bin Range to Display",
        min_value=10,
        max_value=500,
        value=200,
        step=10,
        help="Number of bins to show on each side of the active bin"
    )
    
    # Get current state to calculate total TVL
    current_bins = get_bin_data_for_viz(st.session_state.pool, bin_range)
    total_x = sum(bin['x_amount'] for bin in current_bins)
    total_y = sum(bin['y_amount'] for bin in current_bins)
    
    # Calculate total TVL in USD
    active_bin = next((bin for bin in current_bins if bin['is_active']), None)
    if active_bin:
        total_tvl_usd = (total_x * active_bin['price']) + total_y
    else:
        total_tvl_usd = 0
    
    # Direction toggle
    direction = st.sidebar.radio(
        "Swap Direction",
        ["X→Y", "Y→X"],
        index=0 if st.session_state.direction == "X→Y" else 1,
        help="Direction of the swap",
        key="direction_radio"
    )
    
    # Calculate theoretical maximum input amount based on swap direction
    # Only consider bins that are currently visible in the visualization
    if direction == "X→Y":
        # For X→Y swaps: calculate how many X tokens needed to swap out ALL Y tokens from visible bins
        # This is the theoretical maximum X input for visible range
        max_x_input = 0
        for bin_data in current_bins:
            if bin_data['y_amount'] > 0:
                # Calculate X tokens needed to swap out all Y tokens in this bin
                # Using constant sum: X_in * price = Y_out
                x_needed = bin_data['y_amount'] / bin_data['price']
                max_x_input += x_needed
        max_amount = max_x_input
    else:  # Y→X
        # For Y→X swaps: calculate how many Y tokens needed to swap out ALL X tokens from visible bins
        # This is the theoretical maximum Y input for visible range
        max_y_input = 0
        for bin_data in current_bins:
            if bin_data['x_amount'] > 0:
                # Calculate Y tokens needed to swap out all X tokens in this bin
                # Using constant sum: Y_in = X_out * price
                y_needed = bin_data['x_amount'] * bin_data['price']
                max_y_input += y_needed
        max_amount = max_y_input
    
    # Reset amount to 0 when bin range changes to avoid out-of-range values
    if 'last_bin_range' not in st.session_state:
        st.session_state.last_bin_range = bin_range
    elif st.session_state.last_bin_range != bin_range:
        st.session_state.amount = 0.0
        st.session_state.last_bin_range = bin_range
        st.rerun()  # Force rerun to update slider max value
    
    # Reset amount when direction changes
    if 'last_direction' not in st.session_state:
        st.session_state.last_direction = direction
    elif st.session_state.last_direction != direction:
        st.session_state.amount = 0.0
        st.session_state.last_direction = direction
        st.rerun()  # Force rerun to update slider max value
    
    # Amount slider
    amount = st.sidebar.slider(
        "Input Amount",
        min_value=0.0,
        max_value=float(max_amount),  # Convert to float for slider
        value=float(st.session_state.amount),
        step=0.1,
        help=f"Amount of input token to swap (0-{max_amount:.2f})",
        key=f"amount_slider_{bin_range}_{direction}"  # Include direction in key for better uniqueness
    )
    
    # Update session state
    st.session_state.amount = amount
    st.session_state.direction = direction
    
    # Reset button
    if st.sidebar.button("Reset to Original State"):
        st.session_state.pool = create_pool(st.session_state.pool_type)
        st.session_state.amount = 0.0
        st.session_state.direction = "X→Y"
        st.rerun()
    
    # Only get quoted state if amount > 0
    if amount > 0:
        quoted_bins, quote, used_bin_ids, new_active_bin_id = get_quoted_bin_state(
            st.session_state.pool, amount, direction, bin_range
        )
    else:
        quoted_bins = None
        quote = None
        used_bin_ids = None
        new_active_bin_id = None
    
    # Stats bar across the top
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if quoted_bins and quote and quote.success:
            # Show quoted state stats
            total_x_quoted = sum(bin['x_amount'] for bin in quoted_bins)
            total_y_quoted = sum(bin['y_amount'] for bin in quoted_bins)
            
            # Use new active bin price for quoted state TVL calculation
            new_active_bin = next((bin for bin in quoted_bins if bin['is_active']), None)
            if new_active_bin:
                total_tvl_quoted = (total_x_quoted * new_active_bin['price']) + total_y_quoted
            else:
                total_tvl_quoted = (total_x_quoted * active_bin['price']) + total_y_quoted if active_bin else 0
            
            st.metric(
                "Total TVL",
                f"${total_tvl_quoted:,.0f}",
                delta=f"{total_tvl_quoted - total_tvl_usd:+,.0f}"
            )
        else:
            st.metric("Total TVL", f"${total_tvl_usd:,.0f}")
    
    with col2:
        if quoted_bins and quote and quote.success:
            total_x_quoted = sum(bin['x_amount'] for bin in quoted_bins)
            st.metric(
                f"Total {st.session_state.pool.config.x_token}",
                f"{total_x_quoted:.2f}",
                delta=f"{total_x_quoted - total_x:+.2f}"
            )
        else:
            st.metric(f"Total {st.session_state.pool.config.x_token}", f"{total_x:.2f}")
    
    with col3:
        if quoted_bins and quote and quote.success:
            total_y_quoted = sum(bin['y_amount'] for bin in quoted_bins)
            st.metric(
                f"Total {st.session_state.pool.config.y_token}",
                f"{total_y_quoted:,.0f}",
                delta=f"{total_y_quoted - total_y:+,.0f}"
            )
        else:
            st.metric(f"Total {st.session_state.pool.config.y_token}", f"{total_y:,.0f}")
    
    with col4:
        if quoted_bins and quote and quote.success:
            new_active_bin = next((bin for bin in quoted_bins if bin['is_active']), None)
            if new_active_bin:
                st.metric(
                    "Active Bin Price",
                    f"${new_active_bin['price']:,.2f}",
                    delta=f"{new_active_bin['price'] - active_bin['price']:+.2f}" if active_bin else None
                )
        else:
            if active_bin:
                st.metric("Active Bin Price", f"${active_bin['price']:,.2f}")
            else:
                st.metric("Active Bin Price", "N/A")
    
    st.markdown("---")
    
    # Create two columns for the histograms
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current State")
        st.markdown("*Note: Chart shows TVL in USD with BTC/USD price on X-axis. Hover for detailed token amounts and values.*")
        current_fig = create_tvl_histogram(current_bins, "Current Pool Liquidity")
        st.plotly_chart(current_fig, use_container_width=True)
    
    with col2:
        st.subheader("Quoted State")
        if amount == 0:
            st.markdown("*Set an input amount above to see quoted state*")
            # Show the same current state when amount is 0
            quoted_fig = create_tvl_histogram(current_bins, "No Swap (Amount = 0)")
            st.plotly_chart(quoted_fig, use_container_width=True)
        elif quoted_bins and quote and quote.success:
            st.markdown("*Note: Chart shows TVL in USD with BTC/USD price on X-axis. Hover for detailed token amounts and values.*")
            quoted_fig = create_tvl_histogram(
                quoted_bins, 
                f"After {amount} {direction} Quote",
                used_bin_ids
            )
            st.plotly_chart(quoted_fig, use_container_width=True)
        else:
            st.error("Quote failed or invalid")
    
    # Quote details
    st.subheader("Quote Details")
    if quote and quote.success:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Input Amount", f"{amount} {quote.steps[0].token_in if quote.steps else ''}")
        
        with col2:
            st.metric("Output Amount", f"{quote.total_amount_out:.2f} {quote.steps[0].token_out if quote.steps else ''}")
        
        with col3:
            st.metric("Price Impact", f"{quote.total_price_impact:.4f}%")
        
        # Show bin usage details
        st.markdown("**Bin Usage Details:**")
        if quote.steps:
            usage_data = []
            for step in quote.steps:
                usage_data.append({
                    'Bin ID': step.bin_id,
                    'Amount In': f"{step.amount_in:.4f} {step.token_in}",
                    'Amount Out': f"{step.amount_out:.2f} {step.token_out}",
                    'Price': f"${step.price:,.2f}",
                    'Price Impact': f"{step.price_impact:.4f}%"
                })
            
            usage_df = pd.DataFrame(usage_data)
            st.dataframe(usage_df, use_container_width=True)
        else:
            st.info("No bins used in this quote")
    
    elif quote:
        st.error(f"Quote failed: {quote.error_message}")


if __name__ == "__main__":
    main() 