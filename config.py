"""
=============================================================================
CONFIG - Batch Financial Data Update System
=============================================================================
All credentials loaded from environment variables.
Data flows: Scrapers → Supabase equity_universe table (keyed by isin_code)
=============================================================================
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Supabase ────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bmpvcjbfeyvkkbvclwkb.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJtcHZjamJmZXl2a2tidmNsd2tiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5ODk1MzEsImV4cCI6MjA4NDU2NTUzMX0.AJHhRIw1biBsP6aiN-_7VniMxMxPWkmk-Fq6h5SugQo")
SUPABASE_TABLE = "equity_universe"

# ─── Trendlyne ───────────────────────────────────────────────────
TRENDLYNE_USERNAME = os.getenv("TRENDLYNE_USERNAME", "")
TRENDLYNE_PASSWORD = os.getenv("TRENDLYNE_PASSWORD", "")

# ─── Screener.in ─────────────────────────────────────────────────
SCREENER_USERNAME = os.getenv("SCREENER_USERNAME", "")
SCREENER_PASSWORD = os.getenv("SCREENER_PASSWORD", "")

# ─── Flask API ───────────────────────────────────────────────────
API_PORT = int(os.getenv("API_PORT", "5001"))
API_SECRET = os.getenv("API_SECRET", "change-me-in-production")

# ─── Schedule → Source Mapping ───────────────────────────────────
# Each schedule ONLY scrapes what's unique to that frequency.
# No duplication — saves time and avoids rate limiting.
#
# DAILY:      Yahoo Finance only — prices, returns, volume, market cap
#             (these change every trading day)
# WEEKLY:     Screener.in full — TTM financials, ratios, balance sheet,
#             quarterly results, shareholding, sectors, per-FY actuals
#             (these change at most once a week)
# BIWEEKLY:   Trendlyne + GoIndiaStocks — analyst target prices,
#             forward estimates FY26E-FY28E
#             (analyst consensus updates infrequently)
# QUARTERLY:  Screener.in full — post-earnings refresh to capture
#             new quarterly results and updated annual data
#             (runs Jan/Apr/Jul/Oct after earnings season)
SCHEDULES = {
    "daily":     ["yahoo_finance"],
    "weekly":    ["screener_full"],
    "biweekly":  ["trendlyne", "go_india_stocks"],
    "quarterly": ["screener_full"],
}

# ─── Batch Processing Config ────────────────────────────────────
# batch_size   = how many stocks per batch before writing to Supabase
# delay        = seconds between individual stock scrapes (rate limiting)
# max_workers  = concurrent threads (1 = sequential for browser-based scrapers)
BATCH_CONFIG = {
    "yahoo_finance":    {"batch_size": 10, "delay": 2.0, "max_workers": 3},
    "screener_daily":   {"batch_size": 5,  "delay": 3.0, "max_workers": 1},
    "screener_full":    {"batch_size": 5,  "delay": 3.0, "max_workers": 1},
    "trendlyne":        {"batch_size": 5,  "delay": 8.0, "max_workers": 1},
    "go_india_stocks":  {"batch_size": 5,  "delay": 6.0, "max_workers": 1},
}

# ─── Chrome Options ──────────────────────────────────────────────
CHROME_ARGS = [
    "--headless",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1920,1080",
    "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ─── Screener HTTP Headers ───────────────────────────────────────
SCREENER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── Constants ───────────────────────────────────────────────────
CR = 1e7  # 1 Crore = 10,000,000
FISCAL_YEARS = ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26", "FY27"]

# ─── Valid Supabase Columns ──────────────────────────────────────
# Only these columns will be written to equity_universe.
# Any scraped field not in this set is silently dropped.
VALID_COLUMNS = {
    # Identity
    "company_name", "isin_code", "nse_code", "bse_code",
    "google_code", "nse_bom_code",
    # Sectors
    "broad_sector", "sector", "broad_industry", "industry",
    # Market data
    "market_cap", "current_price", "high_52_week", "low_52_week",
    "volume", "face_value", "book_value", "dividend_yield",
    "num_equity_shares", "enterprise_value",
    # Valuation
    "pe_ttm", "ev_ebitda_ttm", "ps_ttm",
    "pe_avg_3yr", "pe_avg_5yr", "pe_high_hist", "pe_low_hist",
    # Profitability
    "roe", "roce", "roic",
    "ebitda_margin_ttm", "opm_last_year", "pat_margin_ttm",
    "ebitda_margin_ttm_calc", "pat_margin_ttm_calc",
    "asset_turnover_ratio", "working_capital_to_sales_ratio",
    # P&L TTM
    "sales_ttm_screener", "revenue_ttm", "op_profit_ttm",
    "ebitda_ttm", "pat_ttm", "pat_ttm_screener",
    "eps_ttm", "eps_ttm_actual",
    # Balance sheet
    "debt", "cash_equivalents", "net_debt", "net_worth",
    "net_block", "cwip", "cwip_to_net_block_ratio",
    # Shareholding
    "promoter_holding_pct", "unpledged_promoter_holding_pct",
    # Quarterly
    "quarterly_results_date",
    "sales_latest_qtr", "op_profit_latest_qtr", "pat_latest_qtr",
    "ebitda_margin_latest_qtr", "pat_margin_latest_qtr",
    "sales_preceding_qtr", "op_profit_preceding_qtr", "pat_preceding_qtr",
    "revenue_growth_qoq", "ebitda_growth_qoq", "pat_growth_qoq",
    "ebitda_margin_growth_qoq_bps", "pat_margin_growth_qoq_bps",
    "sales_growth_yoy_qtr", "profit_growth_yoy_qtr",
    # Returns
    "return_down_from_52w_high", "return_up_from_52w_low",
    "return_1m", "return_3m", "return_6m", "return_12m",
    # CAGRs
    "revenue_cagr_hist_2yr", "ebitda_cagr_hist_2yr",
    "pat_cagr_hist_2yr", "eps_cagr_hist_2yr",
    "revenue_cagr_fwd_2yr", "ebitda_cagr_fwd_2yr",
    "pat_cagr_fwd_2yr", "eps_cagr_fwd_2yr",
    # Per-FY actuals (long naming)
    "revenue_fy2023", "revenue_fy2024", "revenue_fy2025",
    "ebitda_fy2023", "ebitda_fy2024", "ebitda_fy2025",
    "pat_fy2023", "pat_fy2024", "pat_fy2025",
    "eps_fy2023", "eps_fy2024", "eps_fy2025",
    # Per-FY estimates (long naming)
    "revenue_fy2026e", "revenue_fy2027e", "revenue_fy2028e",
    "ebitda_fy2026e", "ebitda_fy2027e", "ebitda_fy2028e",
    "pat_fy2026e", "pat_fy2027e", "pat_fy2028e",
    "eps_fy2026e", "eps_fy2027e", "eps_fy2028e",
    # Per-FY (short naming)
    "revenue_fy23", "revenue_fy24", "revenue_fy25",
    "revenue_fy26", "revenue_fy27", "revenue_fy28",
    "ebitda_fy23", "ebitda_fy24", "ebitda_fy25",
    "ebitda_fy26", "ebitda_fy27", "ebitda_fy28",
    "pat_fy23", "pat_fy24", "pat_fy25",
    "pat_fy26", "pat_fy27", "pat_fy28",
    # Per-FY margins
    "ebitda_margin_fy2023", "ebitda_margin_fy2024", "ebitda_margin_fy2025",
    "ebitda_margin_fy2026e", "ebitda_margin_fy2027e", "ebitda_margin_fy2028e",
    "pat_margin_fy2023", "pat_margin_fy2024", "pat_margin_fy2025",
    "pat_margin_fy2026e", "pat_margin_fy2027e", "pat_margin_fy2028e",
    # Per-FY valuations
    "pe_fy24", "pe_fy25", "pe_fy26", "pe_fy27", "pe_fy28",
    "pe_fy2026e", "pe_fy2027e", "pe_fy2028e",
    "pb_fy24", "pb_fy25", "pb_fy26", "pb_fy27", "pb_fy28",
    "ev_ebitda_fy2026e", "ev_ebitda_fy2027e", "ev_ebitda_fy2028e",
    "ps_fy2026e", "ps_fy2027e", "ps_fy2028e",
    # Target prices
    "target_price_high", "target_price_low",
    "potential_upside_high", "potential_upside_low",
    "consensus_target_price", "consensus_upside_pct",
    "sotp_value",
    # Dates & timestamps
    "last_annual_result_date", "updated_at",
}
