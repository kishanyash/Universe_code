import yfinance as yf
ticker = yf.Ticker("RELIANCE.NS")
hist = ticker.history(period="1y")
with open("test_yf_ret.txt", "w") as f:
    f.write(f"Hist rows: {len(hist)}\n")
    if not hist.empty:
      f.write(f"First close: {hist['Close'].iloc[0]}, last close: {hist['Close'].iloc[-1]}")
