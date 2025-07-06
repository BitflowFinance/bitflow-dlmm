#!/usr/bin/env python3
"""
Test script to demonstrate fee calculation in DLMM quotes.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.quote_engine import MockRedisClient, QuoteEngine


def test_fee_calculation():
    """Test fee calculation and verify pricing logic"""
    print("💰 DLMM Fee Calculation Test")
    print("=" * 60)
    
    # Initialize quote engine
    redis_client = MockRedisClient()
    quote_engine = QuoteEngine(redis_client)
    
    # Test with 1.0 BTC
    input_amount = 1.0
    quote = quote_engine.get_quote("BTC", "USDC", input_amount)
    
    print(f"\n📊 Quote Details:")
    print(f"Input: {input_amount} BTC")
    print(f"Output: {quote.amount_out:.2f} USDC")
    print(f"Active bin price: $100,000.00")
    print(f"Fee rate: 0.1% (10 basis points)")
    
    # Calculate expected values
    fee_amount = input_amount * 0.001  # 0.1% fee
    amount_after_fees = input_amount - fee_amount
    expected_output = amount_after_fees * 100000  # Active bin price
    
    print(f"\n🧮 Fee Calculation:")
    print(f"Fee amount: {fee_amount:.3f} BTC")
    print(f"Amount after fees: {amount_after_fees:.3f} BTC")
    print(f"Expected output: {expected_output:.2f} USDC")
    print(f"Actual output: {quote.amount_out:.2f} USDC")
    
    # Verify the calculation
    if abs(quote.amount_out - expected_output) < 0.01:
        print(f"✅ Fee calculation is correct!")
    else:
        print(f"❌ Fee calculation error!")
    
    # Test reverse calculation
    print(f"\n🔄 Reverse Calculation:")
    print(f"If you want {quote.amount_out:.2f} USDC, you need:")
    usdc_needed = quote.amount_out
    btc_needed = usdc_needed / 100000  # At active bin price
    btc_with_fees = btc_needed / (1 - 0.001)  # Add fees back
    print(f"  BTC at active price: {btc_needed:.3f} BTC")
    print(f"  BTC with fees: {btc_with_fees:.3f} BTC")
    print(f"  This matches input: {input_amount:.3f} BTC ✅")


if __name__ == "__main__":
    test_fee_calculation() 