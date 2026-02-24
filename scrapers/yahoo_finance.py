"""
=============================================================================
YAHOO FINANCE SCRAPER - Daily
=============================================================================
Fields updated:
  - current_price, market_cap (Rs Crs), enterprise_value (Rs Crs)
  - volume, high_52_week, low_52_week
  - return_1m, return_3m, return_6m, return_12m (%)
  - down_from_52w_high (%), up_from_52w_low (%)
  - beta, dividend_yield
=============================================================================
"""
import yfinance as yf
from utils import safe_round, clean_bse_code
from config import CR
import logging

logger = logging.getLogger("all_fetching.yahoo")


def get_yf_ticker(nse_code, bse_code):
    """Build yfinance ticker symbol from NSE/BSE code."""
    if nse_code:
        return f"{nse_code.strip()}.NS"
    bse = clean_bse_code(bse_code)
    if bse:
        return f"{bse}.BO"
    return None


def scrape_yahoo_finance(company):
    """
    Fetch daily market data from Yahoo Finance.
    
    Args:
        company: dict with keys: isin_code, nse_code, bse_code, company_name
        
    Returns:
        dict of fields to update in equity_universe, or empty dict on failure
    """
    nse_code = company.get("nse_code")
    bse_code = company.get("bse_code")
    name = company.get("company_name", "Unknown")
    
    yf_symbol = get_yf_ticker(nse_code, bse_code)
    if not yf_symbol:
        logger.warning(f"No ticker for {name}")
        return {}
    
    try:
        # Retry logic for 429 Too Many Requests
        info = {}
        for attempt in range(3):
            try:
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info or {}
                if info and info.get("regularMarketPrice") is not None:
                    break
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    wait = 10 * (2 ** attempt)  # 10s, 20s, 40s
                    logger.warning(f"Yahoo 429 for {name}, waiting {wait}s (attempt {attempt+1}/3)")
                    import time
                    time.sleep(wait)
                else:
                    raise
        
        if not info or info.get("regularMarketPrice") is None:
            logger.warning(f"No data from yfinance for {name} ({yf_symbol})")
            return {}
        
        result = {}
        
        # ── Price & Market Data ──────────────────────────────────────────
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        if price:
            result["current_price"] = safe_round(price, 2)
        
        mcap = info.get("marketCap")
        if mcap:
            result["market_cap"] = safe_round(mcap / CR, 2)  # Convert to Rs Crs
        
        ev = info.get("enterpriseValue")
        if ev:
            result["enterprise_value"] = safe_round(ev / CR, 2)  # Convert to Rs Crs
        
        vol = info.get("regularMarketVolume") or info.get("volume")
        if vol:
            result["volume"] = vol
        
        # ── 52 Week High / Low ───────────────────────────────────────────
        h52 = info.get("fiftyTwoWeekHigh")
        l52 = info.get("fiftyTwoWeekLow")
        if h52:
            result["high_52_week"] = safe_round(h52, 2)
        if l52:
            result["low_52_week"] = safe_round(l52, 2)
        
        # ── Returns ──────────────────────────────────────────────────────
        if price and h52 and h52 > 0:
            result["return_down_from_52w_high"] = safe_round(
                (price - h52) / h52 * 100
            )
        if price and l52 and l52 > 0:
            result["return_up_from_52w_low"] = safe_round(
                (price - l52) / l52 * 100
            )
        
        # ── Historical Returns (1M, 3M, 6M, 12M) ────────────────────────
        try:
            hist = ticker.history(period="1y")
            if not hist.empty and price:
                closes = hist["Close"]
                
                if len(closes) >= 22:  # ~1 month
                    result["return_1m"] = safe_round(
                        (price - closes.iloc[-22]) / closes.iloc[-22] * 100
                    )
                if len(closes) >= 66:  # ~3 months
                    result["return_3m"] = safe_round(
                        (price - closes.iloc[-66]) / closes.iloc[-66] * 100
                    )
                if len(closes) >= 132:  # ~6 months
                    result["return_6m"] = safe_round(
                        (price - closes.iloc[-132]) / closes.iloc[-132] * 100
                    )
                if len(closes) >= 240:  # ~12 months (less than 252 trading days is fine)
                    result["return_12m"] = safe_round(
                        (price - closes.iloc[0]) / closes.iloc[0] * 100
                    )
        except Exception as e:
            logger.debug(f"History error for {name}: {e}")
        
        # ── Target Prices & Analyst Consensus ────────────────────────────
        target_high = info.get("targetHighPrice")
        if target_high:
            result["target_price_high"] = safe_round(target_high, 2)
            
        target_low = info.get("targetLowPrice")
        if target_low:
            result["target_price_low"] = safe_round(target_low, 2)
            
        target_mean = info.get("targetMeanPrice")
        if target_mean:
            result["consensus_target_price"] = safe_round(target_mean, 2)

        # ── Analyst Estimates (FY26E & FY27E) ────────────────────────────
        try:
            # yfinance uses '0y' for the current fiscal year (FY26E) and '+1y' for next (FY27E)
            rev_est = ticker.revenue_estimate
            if rev_est is not None and not rev_est.empty:
                if '0y' in rev_est.index:
                    result["revenue_fy2026e"] = safe_round(rev_est.loc['0y', 'avg'] / CR, 2)
                    result["revenue_fy26"] = result["revenue_fy2026e"]
                if '+1y' in rev_est.index:
                    result["revenue_fy2027e"] = safe_round(rev_est.loc['+1y', 'avg'] / CR, 2)
                    result["revenue_fy27"] = result["revenue_fy2027e"]
                if '+2y' in rev_est.index:
                    result["revenue_fy2028e"] = safe_round(rev_est.loc['+2y', 'avg'] / CR, 2)
                    result["revenue_fy28"] = result["revenue_fy2028e"]

            eps_est = ticker.earnings_estimate
            if eps_est is not None and not eps_est.empty:
                if '0y' in eps_est.index:
                    result["eps_fy2026e"] = safe_round(eps_est.loc['0y', 'avg'], 2)
                if '+1y' in eps_est.index:
                    result["eps_fy2027e"] = safe_round(eps_est.loc['+1y', 'avg'], 2)
                if '+2y' in eps_est.index:
                    result["eps_fy2028e"] = safe_round(eps_est.loc['+2y', 'avg'], 2)
        except Exception as e:
            logger.debug(f"Estimates error for {name}: {e}")

        # ── Other Daily Fields ───────────────────────────────────────────
        beta = info.get("beta")
        if beta:
            result["beta"] = safe_round(beta, 2)
        
        div_yield = info.get("dividendYield")
        if div_yield:
            # yfinance sometimes returns decimal (0.0123) or pct (1.23)
            if div_yield > 1:
                result["dividend_yield"] = safe_round(div_yield, 2)  # already %
            else:
                result["dividend_yield"] = safe_round(div_yield * 100, 2)  # convert to %
        
        # ── Number of equity shares (in Crores) ─────────────────────────
        shares = info.get("sharesOutstanding")
        if shares:
            result["num_equity_shares"] = safe_round(shares / CR, 2)
        
        # ── Derived codes (google_code, nse_bom_code) ────────────────────
        bse_clean = clean_bse_code(bse_code)
        if nse_code:
            result["google_code"] = f"NSE:{nse_code.strip()}"
        elif bse_clean:
            result["google_code"] = f"BOM:{bse_clean}"
        if bse_clean:
            result["nse_bom_code"] = f"BOM:{bse_clean}"
        
        logger.info(f"Yahoo OK: {name} ({yf_symbol}) - {len(result)} fields")
        return result
        
    except Exception as e:
        logger.error(f"Yahoo ERROR: {name} ({yf_symbol}): {e}")
        return {}
