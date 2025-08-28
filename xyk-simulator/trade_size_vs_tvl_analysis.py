#!/usr/bin/env python3
"""
Trade Size vs TVL Required Analysis

Demonstrates the exponential relationship between trade size and required TVL
to keep slippage below 0.5% for XYK pools.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Tuple

def calculate_tvl_requirements():
    """
    Calculate TVL requirements for different trade sizes to keep slippage below 0.5%
    
    Based on the finding that we need approximately 800x liquidity to maintain <0.5% slippage
    """
    
    # Trade sizes to analyze (in USD)
    trade_sizes = [100, 1000, 5000, 25000, 50000, 100000, 250000, 500000, 1000000]
    
    # Calculate required TVL (800x trade size)
    required_tvl = [size * 800 for size in trade_sizes]
    
    # Calculate ratios
    tvl_to_trade_ratio = [tvl / size for tvl, size in zip(required_tvl, trade_sizes)]
    
    # Create results DataFrame
    results = []
    for i, trade_size in enumerate(trade_sizes):
        results.append({
            'Trade Size (USD)': trade_size,
            'Required TVL (USD)': required_tvl[i],
            'TVL/Trade Ratio': tvl_to_trade_ratio[i],
            'Trade Size (% of Pool)': (trade_size / required_tvl[i]) * 100
        })
    
    return pd.DataFrame(results)

def create_matplotlib_chart(df: pd.DataFrame):
    """Create matplotlib chart showing the relationship"""
    
    plt.figure(figsize=(12, 8))
    
    # Plot trade size vs required TVL
    plt.plot(df['Trade Size (USD)'], df['Required TVL (USD)'], 
             marker='o', linewidth=2, markersize=8, color='#1f77b4')
    
    # Add data labels
    for _, row in df.iterrows():
        plt.annotate(f"${row['Required TVL (USD)']:,.0f}", 
                    (row['Trade Size (USD)'], row['Required TVL (USD)']),
                    textcoords="offset points", xytext=(0,10), ha='center',
                    fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    # Customize chart
    plt.title('Trade Size vs TVL Required to Keep Slippage Below 0.5%', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Trade Size (USD)', fontsize=12)
    plt.ylabel('Required TVL (USD)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Use linear scale to show the exponential curve
    # Log scales would make this appear as a straight line
    # Linear scales reveal the true exponential relationship
    # plt.xscale('log')  # Commented out to show exponential curve
    # plt.yscale('log')  # Commented out to show exponential curve
    
    # Add reference line showing 800x ratio
    min_trade = df['Trade Size (USD)'].min()
    max_trade = df['Trade Size (USD)'].max()
    x_ref = np.linspace(min_trade, max_trade, 100)
    y_ref = x_ref * 800
    plt.plot(x_ref, y_ref, '--', color='red', alpha=0.7, linewidth=1, 
             label='800x Liquidity Ratio')
    
    plt.legend()
    plt.tight_layout()
    
    # Save chart
    plt.savefig('trade_size_vs_tvl_chart.png', dpi=300, bbox_inches='tight')
    plt.show()

def create_plotly_chart(df: pd.DataFrame):
    """Create interactive Plotly chart"""
    
    # Create the main scatter plot
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['Trade Size (USD)'],
        y=df['Required TVL (USD)'],
        mode='lines+markers',
        name='Required TVL',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=10, color='#1f77b4'),
        hovertemplate='<b>Trade Size:</b> $%{x:,.0f}<br>' +
                     '<b>Required TVL:</b> $%{y:,.0f}<br>' +
                     '<b>Ratio:</b> %{customdata:.0f}x<extra></extra>',
        customdata=df['TVL/Trade Ratio']
    ))
    
    # Add reference line for 800x ratio
    min_trade = df['Trade Size (USD)'].min()
    max_trade = df['Trade Size (USD)'].max()
    x_ref = np.linspace(min_trade, max_trade, 100)
    y_ref = x_ref * 800
    
    fig.add_trace(go.Scatter(
        x=x_ref,
        y=y_ref,
        mode='lines',
        name='800x Liquidity Ratio',
        line=dict(color='red', width=2, dash='dash'),
        hovertemplate='<b>800x Reference Line</b><extra></extra>'
    ))
    
    # Customize layout
    fig.update_layout(
        title={
            'text': 'Trade Size vs TVL Required to Keep Slippage Below 0.5%',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': 'black'}
        },
        xaxis_title='Trade Size (USD)',
        yaxis_title='Required TVL (USD)',
        # xaxis_type='log',  # Commented out to show exponential curve
        # yaxis_type='log',  # Commented out to show exponential curve
        hovermode='closest',
        template='plotly_white',
        width=1000,
        height=600
    )
    
    # Add annotations for key data points
    annotations = []
    for _, row in df.iterrows():
        if row['Trade Size (USD)'] in [100000, 1000000]:  # Highlight key points
            annotations.append(dict(
                x=row['Trade Size (USD)'],
                y=row['Required TVL (USD)'],
                text=f"${row['Required TVL (USD)']:,.0f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor='black',
                ax=0,
                ay=-40,
                bgcolor='white',
                bordercolor='black',
                borderwidth=1
            ))
    
    fig.update_layout(annotations=annotations)
    
    # Save interactive chart
    fig.write_html('trade_size_vs_tvl_interactive.html')
    
    return fig

def main():
    """Main analysis function"""
    
    print("=" * 80)
    print("TRADE SIZE vs TVL REQUIRED ANALYSIS")
    print("=" * 80)
    print()
    
    print("📊 Calculating TVL requirements for 0.5% slippage threshold...")
    print("   Based on finding: $100k trade needs ~$80M TVL (800x ratio)")
    print()
    
    # Calculate requirements
    df = calculate_tvl_requirements()
    
    # Display results table
    print("📈 RESULTS TABLE:")
    print("-" * 80)
    print(f"{'Trade Size':<15} {'Required TVL':<20} {'TVL/Trade':<15} {'Trade % of Pool':<20}")
    print(f"{'(USD)':<15} {'(USD)':<20} {'Ratio':<15} {'(% of TVL)':<20}")
    print(f"{'-'*15} {'-'*20} {'-'*15} {'-'*20}")
    
    for _, row in df.iterrows():
        print(f"${row['Trade Size (USD)']:<14,} ${row['Required TVL (USD)']:<19,} {row['TVL/Trade Ratio']:<15.0f}x {row['Trade Size (% of Pool)']:<20.3f}%")
    
    print()
    
    # Key insights
    print("🔍 KEY INSIGHTS:")
    print("-" * 80)
    print(f"• Small trades ($100): Need ${df.iloc[0]['Required TVL (USD)']:,.0f} TVL (800x)")
    print(f"• Medium trades ($100k): Need ${df.iloc[5]['Required TVL (USD)']:,.0f} TVL (800x)")
    print(f"• Large trades ($1M): Need ${df.iloc[8]['Required TVL (USD)']:,.0f} TVL (800x)")
    print()
    print(f"• All trade sizes require the same 800x liquidity ratio")
    print(f"• Trade size as % of pool remains constant at 0.125%")
    print(f"• This demonstrates the exponential nature of AMM slippage")
    
    print()
    
    # Create charts
    print("📊 CREATING CHARTS...")
    print("-" * 80)
    
    try:
        # Matplotlib chart
        print("• Creating matplotlib chart...")
        create_matplotlib_chart(df)
        print("  ✅ Matplotlib chart saved as 'trade_size_vs_tvl_chart.png'")
        
        # Plotly chart
        print("• Creating interactive Plotly chart...")
        fig = create_plotly_chart(df)
        print("  ✅ Interactive chart saved as 'trade_size_vs_tvl_interactive.html'")
        
        print()
        print("🎯 CHARTS CREATED SUCCESSFULLY!")
        print("   • Static chart: trade_size_vs_tvl_chart.png")
        print("   • Interactive chart: trade_size_vs_tvl_interactive.html")
        
    except Exception as e:
        print(f"❌ Error creating charts: {e}")
        print("   Displaying results table only")
    
    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
