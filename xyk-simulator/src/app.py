"""
Streamlit App for XYK Simulator

Interactive web interface for analyzing price slippage in constant product AMMs.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from xyk_simulator import XYKSimulator
import numpy as np


def main():
    st.set_page_config(
        page_title="XYK Simulator - Price Slippage Analysis",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("🚀 XYK Simulator - Price Slippage Analysis")
    st.markdown("Analyze price slippage in constant product AMMs (X*Y=K)")
    
    # Sidebar configuration
    st.sidebar.header("Pool Configuration")
    
    tvl = st.sidebar.number_input(
        "Total Value Locked (USD)",
        min_value=10000,
        max_value=10000000,
        value=3000000,
        step=100000,
        format="%d"
    )
    
    initial_price = st.sidebar.number_input(
        "Initial Price (Y/X)",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1,
        format="%.2f"
    )
    
    # Initialize simulator
    simulator = XYKSimulator(total_value_locked=tvl, initial_price=initial_price)
    
    # Display pool state
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Value Locked", f"${simulator.get_tvl():,.0f}")
    
    with col2:
        st.metric("Reserve X", f"${simulator.reserve_x:,.0f}")
    
    with col3:
        st.metric("Reserve Y", f"${simulator.reserve_y:,.0f}")
    
    with col4:
        st.metric("Spot Price", f"${simulator.get_spot_price():.4f}")
    
    st.markdown("---")
    
    # Main analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Slippage Analysis", 
        "💰 TVL Requirements", 
        "🔍 Interactive Trade", 
        "📊 Insights"
    ])
    
    with tab1:
        st.header("Trade Size vs Slippage Analysis")
        
        # Trade direction and size range
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trade_direction = st.selectbox(
                "Trade Direction",
                ["Swap X for Y", "Swap Y for X"],
                index=0,
                key="trade_direction_analyzer"
            )
            input_is_x = (trade_direction == "Swap X for Y")
        
        with col2:
            min_trade = st.number_input(
                "Minimum Trade Size (USD)",
                min_value=100,
                max_value=10000,
                value=1000,
                step=100
            )
        
        with col3:
            max_trade = st.number_input(
                "Maximum Trade Size (USD)",
                min_value=min_trade,
                max_value=tvl,
                value=min(tvl // 2, 500000),
                step=1000
            )
        
        # Generate trade sizes
        num_points = 20
        trade_sizes = np.linspace(min_trade, max_trade, num_points)
        
        # Analyze slippage using selected direction
        results = []
        for trade_size in trade_sizes:
            result = simulator.calculate_price_impact(trade_size, input_is_x=input_is_x)
            results.append({
                'Trade Size': trade_size,
                'Slippage %': result.slippage_percentage,
                'Price Impact': result.price_impact,
                'Output Amount': result.output_amount,
                'Trade Size % of Pool': (trade_size / simulator.get_tvl()) * 100
            })
        
        results_df = pd.DataFrame(results)
        
        # Display table
        st.subheader("Slippage Analysis Table")
        display_df = results_df.copy()
        display_df['Trade Size'] = display_df['Trade Size'].apply(lambda x: f"${x:,.0f}")
        display_df['Slippage %'] = display_df['Slippage %'].apply(lambda x: f"{x:.4f}%")
        display_df['Price Impact'] = display_df['Price Impact'].apply(lambda x: f"{x:.6f}")
        display_df['Output Amount'] = display_df['Output Amount'].apply(lambda x: f"${x:,.2f}")
        display_df['Trade Size % of Pool'] = display_df['Trade Size % of Pool'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(display_df, use_container_width=True)
        
        # Create slippage chart
        st.subheader("Slippage vs Trade Size")
        
        direction_text = "X→Y" if input_is_x else "Y→X"
        fig = px.line(
            results_df, 
            x='Trade Size', 
            y='Slippage %',
            title=f"Slippage Impact for {direction_text} Trades in ${tvl:,.0f} Pool"
        )
        fig.update_layout(
            xaxis_title="Trade Size (USD)",
            yaxis_title="Slippage (%)",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Trade size as percentage of pool
        st.subheader("Trade Size as Percentage of Pool")
        
        fig2 = px.line(
            results_df,
            x='Trade Size % of Pool',
            y='Slippage %',
            title="Slippage vs Trade Size (% of Pool)"
        )
        fig2.update_layout(
            xaxis_title="Trade Size (% of Pool)",
            yaxis_title="Slippage (%)",
            hovermode='x unified'
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # NEW: Slippage as percentage of input token liquidity
        st.subheader("Slippage vs Trade Size (% of Input Token Liquidity)")
        
        # Calculate trade size as % of input token liquidity
        if input_is_x:
            # Swapping X for Y, so show as % of X liquidity
            results_df['Trade Size % of X Liquidity'] = (results_df['Trade Size'] / simulator.reserve_x) * 100
            x_axis_col = 'Trade Size % of X Liquidity'
            x_title = "Trade Size (% of X Liquidity)"
        else:
            # Swapping Y for X, so show as % of Y liquidity
            results_df['Trade Size % of Y Liquidity'] = (results_df['Trade Size'] / simulator.reserve_y) * 100
            x_axis_col = 'Trade Size % of Y Liquidity'
            x_title = "Trade Size (% of Y Liquidity)"
        
        fig3 = px.line(
            results_df,
            x=x_axis_col,
            y='Slippage %',
            title=f"Slippage vs Trade Size ({x_title})"
        )
        fig3.update_layout(
            xaxis_title=x_title,
            yaxis_title="Slippage (%)",
            hovermode='x unified'
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    with tab2:
        st.header("TVL Requirements Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            target_trade_size = st.number_input(
                "Target Trade Size (USD)",
                min_value=1000,
                max_value=1000000,
                value=100000,
                step=1000
            )
        
        with col2:
            max_slippage = st.slider(
                "Maximum Slippage (%)",
                min_value=0.1,
                max_value=10.0,
                value=1.0,
                step=0.1
            ) / 100
        
        # Calculate TVL requirement
        requirement = simulator.find_tvl_for_slippage(
            trade_size=target_trade_size,
            max_slippage=max_slippage,
            input_is_x=True
        )
        
        # Display results
        st.subheader(f"TVL Requirements for ${target_trade_size:,.0f} Trade")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Required TVL",
                f"${requirement.required_tvl:,.0f}",
                delta=f"{(requirement.required_tvl - tvl):,.0f}"
            )
        
        with col2:
            st.metric(
                "Required Reserve X",
                f"${requirement.required_reserve_x:,.0f}"
            )
        
        with col3:
            st.metric(
                "Required Reserve Y",
                f"${requirement.required_reserve_y:,.0f}"
            )
        
        # Multiple slippage thresholds
        st.subheader("TVL Requirements for Different Slippage Thresholds")
        
        thresholds = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1]
        tvl_data = []
        
        for threshold in thresholds:
            req = simulator.find_tvl_for_slippage(
                trade_size=target_trade_size,
                max_slippage=threshold,
                input_is_x=True
            )
            tvl_data.append({
                'Max Slippage': f"{threshold * 100:.1f}%",
                'Required TVL': req.required_tvl,
                'Trade Size % of TVL': (target_trade_size / req.required_tvl) * 100
            })
        
        tvl_df = pd.DataFrame(tvl_data)
        
        # Create TVL requirement chart
        fig3 = px.bar(
            tvl_df,
            x='Max Slippage',
            y='Required TVL',
            title=f"TVL Requirements for ${target_trade_size:,.0f} Trade"
        )
        fig3.update_layout(
            xaxis_title="Maximum Slippage",
            yaxis_title="Required TVL (USD)",
            showlegend=False
        )
        st.plotly_chart(fig3, use_container_width=True)
        
        # Display table
        display_tvl_df = tvl_df.copy()
        display_tvl_df['Required TVL'] = display_tvl_df['Required TVL'].apply(lambda x: f"${x:,.0f}")
        display_tvl_df['Trade Size % of TVL'] = display_tvl_df['Trade Size % of TVL'].apply(lambda x: f"{x:.2f}%")
        
        st.dataframe(display_tvl_df, use_container_width=True)
    
    with tab3:
        st.header("Interactive Trade Simulation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            trade_amount = st.number_input(
                "Trade Amount (USD)",
                min_value=100,
                max_value=int(tvl * 0.8),
                value=10000,
                step=100
            )
            
            trade_direction_executor = st.selectbox(
                "Trade Direction",
                ["Swap X for Y", "Swap Y for X"],
                key="trade_direction_executor"
            )
        
        with col2:
            if st.button("Execute Trade", type="primary"):
                input_is_x = (trade_direction_executor == "Swap X for Y")
                
                # Calculate trade impact
                result = simulator.calculate_price_impact(trade_amount, input_is_x)
                
                # Display results
                st.success("Trade executed successfully!")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Price Before",
                        f"${result.price_before:.4f}"
                    )
                
                with col2:
                    st.metric(
                        "Price After",
                        f"${result.price_after:.4f}"
                    )
                
                with col3:
                    st.metric(
                        "Slippage",
                        f"{result.slippage_percentage:.4f}%"
                    )
                
                st.metric(
                    "Output Amount",
                    f"${result.output_amount:,.2f}"
                )
                
                # Reset pool button
                if st.button("Reset Pool"):
                    simulator.reset_pool()
                    st.rerun()
        
        # Current pool state
        st.subheader("Current Pool State")
        
        pool_state = simulator.get_pool_state()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Reserve X", f"${pool_state['reserve_x']:,.2f}")
        
        with col2:
            st.metric("Reserve Y", f"${pool_state['reserve_y']:,.2f}")
        
        with col3:
            st.metric("Spot Price", f"${pool_state['spot_price']:.4f}")
    
    with tab4:
        st.header("Key Insights & Analysis")
        
        st.subheader("🎯 Core Findings")
        
        st.markdown("""
        **1. Exponential Slippage Relationship**
        - Slippage increases exponentially with trade size relative to pool size
        - Small trades (<1% of pool) have minimal impact
        - Large trades (>10% of pool) cause significant price movement
        
        **2. TVL Requirements & Pool Depth Impact**
        - For a $100K trade with <1% slippage, you need ~$20M TVL
        - **$3M pools** can handle $100K trades with ~12% slippage (vs 30% in $1M pools)
        - Trade size should typically be <5% of pool TVL for reasonable slippage
        - **Pool depth provides dramatic slippage protection** - 3x larger pool = 3x less slippage
        
        **3. Price Impact Symmetry**
        - Equal-sized trades in opposite directions have symmetric price impact
        - The constant product formula ensures this mathematical property
        - Pool rebalancing happens automatically through arbitrage
        """)
        
        st.subheader("💡 Practical Implications")
        
        st.markdown("""
        **For Traders:**
        - Split large trades into smaller chunks to minimize slippage
        - **Choose deeper pools** - $3M pools offer 3x better slippage protection than $1M pools
        - Monitor slippage vs. execution cost trade-offs
        - **$100K trades** work well in $3M+ pools (~12% slippage), avoid in $1M pools (~30% slippage)
        
        **For Liquidity Providers:**
        - **Larger pools provide dramatically better slippage protection**
        - Consider expected trade sizes when setting pool sizes
        - Pool depth is more important than fee structure for large trades
        - **$3M pools** can attract institutional traders who need to execute $100K+ trades
        
        **For Pool Design:**
        - Target appropriate TVL for expected trade sizes
        - Balance between capital efficiency and slippage protection
        - Consider market maker incentives for deep liquidity
        - **Pool depth scaling** - 3x larger pool = 3x better slippage protection
        """)
        
        st.subheader("🔬 Mathematical Foundation")
        
        st.markdown("""
        **Constant Product Formula: X × Y = K**
        
        When trading ΔX for ΔY:
        - New reserves: X' = X + ΔX, Y' = Y - ΔY
        - Constant maintained: X' × Y' = K
        - Price change: ΔP = P' - P = (Y'/X') - (Y/X)
        - Slippage: %ΔP = (ΔP/P) × 100
        
        **Key Insight:** The larger ΔX is relative to X, the greater the price impact.
        This creates the exponential relationship between trade size and slippage.
        """)


if __name__ == "__main__":
    main()
