import yfinance as yf
ticker = yf.Ticker("RELIANCE.NS")
with open("test_out.txt", "w") as f:
    f.write(str(ticker.revenue_estimate))
    f.write("\n")
    f.write(str(ticker.earnings_estimate))
