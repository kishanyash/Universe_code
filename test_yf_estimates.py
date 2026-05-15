"""
Check Yahoo Finance for estimates
"""
if __name__ != "__main__":
    import pytest
    pytest.skip("utility script; not a pytest test module", allow_module_level=True)

import yfinance as yf
ticker = yf.Ticker("RELIANCE.NS")
info = ticker.info

print("Target Prices:")
print("High:", info.get("targetHighPrice"))
print("Low:", info.get("targetLowPrice"))
print("Mean:", info.get("targetMeanPrice"))
print("Median:", info.get("targetMedianPrice"))

print("\nEarnings Estimate:")
try:
    print(ticker.earnings_estimate)
except Exception as e:
    print(e)
    
print("\nRevenue Estimate:")
try:
    print(ticker.revenue_estimate)
except Exception as e:
    print(e)
