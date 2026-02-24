# FIELD REFERENCE — All Fetching System
# What Gets Scraped, From Where, When, and Units
# Database: Supabase → public.equity_universe (keyed by isin_code)
# Last Updated: 2026-02-24
#
# IMPORTANT: Each schedule ONLY scrapes what's unique to that frequency.
#            No duplication across schedules.

═══════════════════════════════════════════════════════════════════
 SCHEDULE OVERVIEW (OPTIMIZED — No Overlap)
═══════════════════════════════════════════════════════════════════

DAILY     → Every day 6:30 AM IST     → Yahoo Finance ONLY
            What changes daily: prices, volume, returns
            Est. time: ~20 min for 895 stocks

WEEKLY    → Every Monday 7:30 AM IST  → Screener.in ONLY
            What changes weekly: TTM financials, ratios, balance sheet,
            quarterly results, shareholding, sectors, per-FY actuals
            Est. time: ~50 min for 895 stocks

BIWEEKLY  → 1st & 15th 8:30 AM IST   → Trendlyne + GoIndiaStocks ONLY
            What changes rarely: analyst targets, forward estimates
            Est. time: ~3-4 hours for 895 stocks

QUARTERLY → Jan/Apr/Jul/Oct 9:30 AM   → Screener.in ONLY
            Post-earnings season refresh to capture new quarterly
            results and updated annual figures
            Est. time: ~50 min for 895 stocks


═══════════════════════════════════════════════════════════════════
 ★ DAILY — Yahoo Finance ONLY
 ★ What: Prices, returns, volume — things that change every trading day
 ★ Source: yfinance Python API (no browser needed)
 ★ Runs: Every day at 6:30 AM IST (01:00 UTC)
═══════════════════════════════════════════════════════════════════

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
current_price                   │ Live market price                  │ ₹ per share
market_cap                      │ Market capitalization              │ ₹ Crores
enterprise_value                │ MCap + Debt − Cash                 │ ₹ Crores
volume                          │ Daily trading volume               │ Number of shares
high_52_week                    │ 52-week high price                 │ ₹ per share
low_52_week                     │ 52-week low price                  │ ₹ per share
return_down_from_52w_high       │ How far below 52w high             │ % (negative)
return_up_from_52w_low          │ How far above 52w low              │ % (positive)
return_1m                       │ 1-month stock return               │ %
return_3m                       │ 3-month stock return               │ %
return_6m                       │ 6-month stock return               │ %
return_12m                      │ 12-month stock return              │ %
target_price_high               │ Analyst highest target price       │ ₹ per share
target_price_low                │ Analyst lowest target price        │ ₹ per share
consensus_target_price          │ Analyst mean target price          │ ₹ per share
dividend_yield                  │ Annual dividend yield              │ %
beta                            │ Stock beta (volatility measure)    │ Ratio
num_equity_shares               │ Total shares outstanding           │ Crores
revenue_fy2026e / revenue_fy26  │ Revenue estimate FY2026            │ ₹ Crores
revenue_fy2027e / revenue_fy27  │ Revenue estimate FY2027            │ ₹ Crores
revenue_fy2028e / revenue_fy28  │ Revenue estimate FY2028            │ ₹ Crores
eps_fy2026e                     │ EPS estimate FY2026                │ ₹ per share
eps_fy2027e                     │ EPS estimate FY2027                │ ₹ per share
eps_fy2028e                     │ EPS estimate FY2028                │ ₹ per share
google_code                     │ Google Finance ticker              │ Text (NSE:RELIANCE)
nse_bom_code                    │ BSE BOM code                       │ Text (BOM:500325)

>>> DAILY CALCULATED FIELDS (computed after Yahoo scrape) <<<

Supabase Column                 │ Formula                            │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
consensus_target_price          │ avg(target_high, target_low)       │ ₹ per share
consensus_upside_pct            │ (Consensus − Price) / Price × 100  │ %
potential_upside_high           │ (HighTarget − Price) / Price × 100 │ %
potential_upside_low            │ (LowTarget − Price) / Price × 100  │ %
pe_fy24..pe_fy28                │ Current Price / EPS of that FY     │ Ratio (x)
pb_fy24..pb_fy28                │ Current Price / Book Value         │ Ratio (x)
sotp_value                      │ target_price_high or current_price │ ₹ per share

TOTAL DAILY FIELDS: ~33 scraped + ~15 calculated = ~48 fields


═══════════════════════════════════════════════════════════════════
 ★ WEEKLY — Screener.in ONLY
 ★ What: Financials, ratios, balance sheet — things that change weekly
 ★ Source: HTTP GET + BeautifulSoup (no browser)
 ★ URL: https://www.screener.in/company/{NSE_CODE}/consolidated/
 ★ Runs: Every Monday at 7:30 AM IST (02:00 UTC)
═══════════════════════════════════════════════════════════════════

>>> TOP RATIOS (from ratios bar at top of page) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
current_price                   │ Current stock price                │ ₹ per share
market_cap                      │ Market capitalization              │ ₹ Crores
high_52_week                    │ 52-week high                       │ ₹ per share
low_52_week                     │ 52-week low                        │ ₹ per share
pe_ttm                          │ Price-to-Earnings (TTM)            │ Ratio (x)
book_value                      │ Book value per share               │ ₹ per share
face_value                      │ Face value per share               │ ₹ per share
dividend_yield                  │ Dividend yield                     │ %
roce                            │ Return on Capital Employed         │ %
roe                             │ Return on Equity                   │ %

>>> SECTOR CLASSIFICATION (from Peers section) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
broad_sector                    │ Broad sector                       │ Text ("Commodities")
sector                          │ Sector                             │ Text ("Oil & Gas")
broad_industry                  │ Broad industry                     │ Text ("Oil Exploration")
industry                        │ Industry                           │ Text ("Crude Oil")

>>> QUARTERLY RESULTS (from Quarters table on page) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
quarterly_results_date          │ Date of latest quarter results     │ Date (YYYY-MM-DD)
sales_latest_qtr                │ Revenue — latest quarter           │ ₹ Crores
op_profit_latest_qtr            │ Operating profit — latest quarter  │ ₹ Crores
pat_latest_qtr                  │ PAT — latest quarter               │ ₹ Crores
ebitda_margin_latest_qtr        │ EBITDA margin — latest quarter     │ %
pat_margin_latest_qtr           │ PAT margin — latest quarter        │ %
sales_preceding_qtr             │ Revenue — preceding quarter        │ ₹ Crores
op_profit_preceding_qtr         │ Op profit — preceding quarter      │ ₹ Crores
pat_preceding_qtr               │ PAT — preceding quarter            │ ₹ Crores
revenue_growth_qoq              │ Revenue QoQ growth                 │ %
ebitda_growth_qoq               │ EBITDA QoQ growth                  │ %
pat_growth_qoq                  │ PAT QoQ growth                     │ %
sales_growth_yoy_qtr            │ Revenue YoY (vs same qtr last yr)  │ %
profit_growth_yoy_qtr           │ Profit YoY (vs same qtr last yr)   │ %

>>> PROFIT & LOSS — TTM (from P&L table, last column) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
sales_ttm_screener              │ Revenue TTM                        │ ₹ Crores
revenue_ttm                     │ Revenue TTM (same value)           │ ₹ Crores
op_profit_ttm                   │ Operating Profit TTM               │ ₹ Crores
ebitda_ttm                      │ EBITDA TTM (same as op_profit)     │ ₹ Crores
pat_ttm                         │ Profit After Tax TTM               │ ₹ Crores
pat_ttm_screener                │ PAT TTM (same value)               │ ₹ Crores
eps_ttm                         │ Earnings Per Share TTM             │ ₹ per share
eps_ttm_actual                  │ EPS TTM actual (same value)        │ ₹ per share
ebitda_margin_ttm               │ EBITDA / Revenue × 100             │ %
pat_margin_ttm                  │ PAT / Revenue × 100                │ %
opm_last_year                   │ OPM of last full fiscal year       │ %
ps_ttm                          │ Market Cap / Revenue               │ Ratio (x)
ev_ebitda_ttm                   │ Enterprise Value / EBITDA          │ Ratio (x)

>>> PER-FY ACTUALS (from P&L annual columns) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
revenue_fy2023 / revenue_fy23   │ Revenue FY2023 (Apr'22 – Mar'23)   │ ₹ Crores
revenue_fy2024 / revenue_fy24   │ Revenue FY2024 (Apr'23 – Mar'24)   │ ₹ Crores
revenue_fy2025 / revenue_fy25   │ Revenue FY2025 (Apr'24 – Mar'25)   │ ₹ Crores
ebitda_fy2023 / ebitda_fy23     │ EBITDA FY2023                      │ ₹ Crores
ebitda_fy2024 / ebitda_fy24     │ EBITDA FY2024                      │ ₹ Crores
ebitda_fy2025 / ebitda_fy25     │ EBITDA FY2025                      │ ₹ Crores
pat_fy2023 / pat_fy23           │ PAT FY2023                         │ ₹ Crores
pat_fy2024 / pat_fy24           │ PAT FY2024                         │ ₹ Crores
pat_fy2025 / pat_fy25           │ PAT FY2025                         │ ₹ Crores
eps_fy2023                      │ EPS FY2023                         │ ₹ per share
eps_fy2024                      │ EPS FY2024                         │ ₹ per share
eps_fy2025                      │ EPS FY2025                         │ ₹ per share

>>> HISTORICAL CAGRS (calculated from P&L data) <<<

Supabase Column                 │ Formula                            │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
revenue_cagr_hist_2yr           │ CAGR(Revenue 2yr ago, Revenue TTM) │ %
ebitda_cagr_hist_2yr            │ CAGR(EBITDA 2yr ago, EBITDA TTM)   │ %
pat_cagr_hist_2yr               │ CAGR(PAT 2yr ago, PAT TTM)         │ %
eps_cagr_hist_2yr               │ CAGR(EPS 2yr ago, EPS TTM)         │ %

>>> BALANCE SHEET (from Balance Sheet table, latest year) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
debt                            │ Total borrowings                   │ ₹ Crores
net_worth                       │ Equity Capital + Reserves          │ ₹ Crores
cash_equivalents                │ Investments + 30% Other Assets     │ ₹ Crores
net_debt                        │ Debt − Cash                        │ ₹ Crores
enterprise_value                │ Market Cap + Net Debt              │ ₹ Crores
num_equity_shares               │ Equity Capital / Face Value        │ Crores
cwip                            │ Capital Work in Progress           │ ₹ Crores
net_block                       │ Fixed Assets / Net Block           │ ₹ Crores
cwip_to_net_block_ratio         │ CWIP / Net Block × 100             │ %

>>> RATIOS (from Ratios table) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
roce                            │ Return on Capital Employed         │ %
roe                             │ Return on Equity                   │ %
roic                            │ Return on Invested Capital         │ %
asset_turnover_ratio            │ Revenue / Total Assets             │ Ratio (x)
working_capital_to_sales_ratio  │ Working Capital Days / 365         │ Ratio (x)

>>> SHAREHOLDING (from Shareholding table) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
promoter_holding_pct            │ Promoter holding                   │ %
unpledged_promoter_holding_pct  │ Unpledged promoter holding         │ %

>>> HISTORICAL P/E (calculated from EPS history) <<<

Supabase Column                 │ Formula                            │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
pe_avg_3yr                      │ CMP / Avg EPS of last 3 FYs        │ Ratio (x)
pe_avg_5yr                      │ CMP / Avg EPS of last 5 FYs        │ Ratio (x)
pe_high_hist                    │ CMP / Min historical EPS           │ Ratio (x)
pe_low_hist                     │ CMP / Max historical EPS           │ Ratio (x)

>>> WEEKLY CALCULATED FIELDS <<<

Supabase Column                 │ Formula                            │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
ebitda_margin_ttm_calc          │ EBITDA_TTM / Revenue_TTM × 100     │ %
pat_margin_ttm_calc             │ PAT_TTM / Revenue_TTM × 100        │ %
ebitda_margin_growth_qoq_bps    │ (Latest − Preceding margin) × 100  │ Basis Points
pat_margin_growth_qoq_bps       │ (Latest − Preceding margin) × 100  │ Basis Points
return_down_from_52w_high       │ (Price − 52wHigh) / 52wHigh × 100  │ %
return_up_from_52w_low          │ (Price − 52wLow) / 52wLow × 100    │ %
ebitda_margin_fy2023..fy2025    │ EBITDA / Revenue × 100 per FY      │ %
pat_margin_fy2023..fy2025       │ PAT / Revenue × 100 per FY         │ %
last_annual_result_date         │ quarterly_results_date or default   │ Date

TOTAL WEEKLY FIELDS: ~65 scraped + ~18 calculated = ~83 fields


═══════════════════════════════════════════════════════════════════
 ★ BIWEEKLY — Trendlyne + GoIndiaStocks ONLY
 ★ What: Analyst targets & forward estimates — change infrequently
 ★ Sources: Selenium headless Chrome (slow, ~8s/stock + ~6s/stock)
 ★ Runs: 1st & 15th of every month at 8:30 AM IST (03:00 UTC)
═══════════════════════════════════════════════════════════════════

---------------------------------------------------------------
 FROM: TRENDLYNE (requires login, Selenium)
 URL: https://trendlyne.com/equity/{NSE_CODE}/stock-page
---------------------------------------------------------------

>>> TARGET PRICES <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
consensus_target_price          │ Average analyst target price        │ ₹ per share
target_price_high               │ Highest analyst target              │ ₹ per share
target_price_low                │ Lowest analyst target               │ ₹ per share

>>> FY ACTUALS (cross-verification with Screener) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
revenue_fy2023..fy2025          │ Operating Revenue actuals           │ ₹ Crores
ebitda_fy2023..fy2025           │ EBITDA actuals                      │ ₹ Crores
pat_fy2023..fy2025              │ Net Profit actuals                  │ ₹ Crores
eps_fy2023..fy2025              │ EPS actuals                         │ ₹ per share

>>> FORWARD ESTIMATES <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
revenue_fy2026e / revenue_fy26  │ Revenue estimate FY2026            │ ₹ Crores
revenue_fy2027e / revenue_fy27  │ Revenue estimate FY2027            │ ₹ Crores
ebitda_fy2026e / ebitda_fy26    │ EBITDA estimate FY2026             │ ₹ Crores
ebitda_fy2027e / ebitda_fy27    │ EBITDA estimate FY2027             │ ₹ Crores
pat_fy2026e / pat_fy26          │ PAT estimate FY2026                │ ₹ Crores
pat_fy2027e / pat_fy27          │ PAT estimate FY2027                │ ₹ Crores
eps_fy2026e                     │ EPS estimate FY2026                │ ₹ per share
eps_fy2027e                     │ EPS estimate FY2027                │ ₹ per share


---------------------------------------------------------------
 FROM: GOINDIA STOCKS (no login, Selenium)
 URL: https://www.goindiastocks.com/companyinfo/{NSE_CODE}
---------------------------------------------------------------

>>> TARGET PRICES <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
target_price_high               │ Highest analyst target              │ ₹ per share
consensus_target_price          │ Average analyst target              │ ₹ per share
target_price_low                │ Lowest analyst target               │ ₹ per share

>>> FY ACTUALS + FORWARD ESTIMATES (FY23 to FY28E) <<<

Supabase Column                 │ What It Is                         │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
revenue_fy2023..fy2025          │ Revenue actuals                     │ ₹ Crores
revenue_fy2026e..fy2028e        │ Revenue estimates                   │ ₹ Crores
ebitda_fy2023..fy2025           │ EBITDA actuals (PPOP for banks)     │ ₹ Crores
ebitda_fy2026e..fy2028e         │ EBITDA estimates                    │ ₹ Crores
pat_fy2023..fy2025              │ PAT actuals                         │ ₹ Crores
pat_fy2026e..fy2028e            │ PAT estimates                       │ ₹ Crores
eps_fy2023..fy2025              │ Diluted EPS actuals                 │ ₹ per share
eps_fy2026e..fy2028e            │ Diluted EPS estimates               │ ₹ per share

>>> BIWEEKLY CALCULATED FIELDS <<<

Supabase Column                 │ Formula                            │ Unit
────────────────────────────────┼────────────────────────────────────┼─────────────
ebitda_margin_fy2026e..fy2028e  │ EBITDA / Revenue × 100 per FY      │ %
pat_margin_fy2026e..fy2028e     │ PAT / Revenue × 100 per FY         │ %
ev_ebitda_fy2026e..fy2028e      │ Enterprise Value / EBITDA           │ Ratio (x)
ps_fy2026e..fy2028e             │ Market Cap / Revenue                │ Ratio (x)
revenue_cagr_fwd_2yr            │ CAGR(Revenue FY25, Revenue FY27E)  │ %
ebitda_cagr_fwd_2yr             │ CAGR(EBITDA FY25, EBITDA FY27E)    │ %
pat_cagr_fwd_2yr                │ CAGR(PAT FY25, PAT FY27E)          │ %
eps_cagr_fwd_2yr                │ CAGR(EPS FY25, EPS FY27E)          │ %

>>> FY2028E EXTRAPOLATION (when FY28E data is missing) <<<

revenue_fy2028e                 │ Revenue FY27E × 1.05 (5% growth)   │ ₹ Crores
ebitda_fy2028e                  │ EBITDA FY27E × 1.05                │ ₹ Crores
pat_fy2028e                     │ PAT FY27E × 1.05                   │ ₹ Crores
eps_fy2028e                     │ EPS FY27E × 1.05                   │ ₹ per share

>>> MISSING ESTIMATE DERIVATION <<<

pat (if missing)                │ EPS × Number of Shares             │ ₹ Crores
ebitda (if missing)             │ Revenue × Historical EBITDA Margin │ ₹ Crores

TOTAL BIWEEKLY FIELDS: ~45 scraped + ~20 calculated = ~65 fields


═══════════════════════════════════════════════════════════════════
 ★ QUARTERLY — Screener.in ONLY (Post-Earnings Refresh)
 ★ What: Same as WEEKLY — refresh to capture new quarterly results
 ★ Purpose: After earnings season (Jan/Apr/Jul/Oct), companies
 ★          publish new quarterly/annual results. This ensures
 ★          the latest financials are captured.
 ★ Runs: 1st of Jan, Apr, Jul, Oct at 9:30 AM IST (04:00 UTC)
═══════════════════════════════════════════════════════════════════

Same fields as WEEKLY (see above) — runs Screener Full.

Why quarterly if we already have weekly?
→ The quarterly run ensures post-earnings-season data is captured
   even if a weekly run was missed or had errors.
→ Quarterly runs align with earnings announcement cycles.
→ New FY actuals (e.g. FY2025 results published in May) will be
   captured by the weekly run, but quarterly acts as a safety net.


═══════════════════════════════════════════════════════════════════
 UNIT REFERENCE
═══════════════════════════════════════════════════════════════════

₹ per share     = Indian Rupees per equity share
                   Used for: current_price, eps, target prices,
                   book_value, face_value

₹ Crores        = Indian Rupees in Crores
                   1 Crore = 1,00,00,000 = 10 Million
                   Used for: revenue, ebitda, pat, market_cap,
                   enterprise_value, debt, net_worth, etc.

%               = Percentage (stored as plain number: 15.5 = 15.5%)
                   Used for: margins, returns, CAGR, yields, holdings

Ratio (x)       = Valuation multiple (e.g. PE of 25x)
                   Used for: pe_ttm, ev_ebitda, ps_ttm, pb, pe_avg

Basis Points    = 1/100th of a percentage point (100 BPS = 1%)
                   Used for: margin_growth_qoq_bps

Crores          = Number in Crores (NOT ₹)
                   Used for: num_equity_shares

Date            = YYYY-MM-DD format
Timestamp       = ISO 8601 (e.g. 2026-02-24T10:08:19+00:00)
Text            = String value

IMPORTANT NOTES:
• ALL monetary values are in ₹ CRORES (not Lakhs, not absolute ₹)
  EXCEPT: current_price, book_value, face_value, EPS, target prices
          which are in absolute ₹ per share
• No values are stored in Lakhs (₹ Lakhs) — everything is ₹ Crores
• Percentages are plain numbers (15.5 means 15.5%, NOT 0.155)


═══════════════════════════════════════════════════════════════════
 DUPLICATE COLUMN NAMING (both conventions always in sync)
═══════════════════════════════════════════════════════════════════

Long Name           │ Short Name      │ Both hold the same value
────────────────────┼─────────────────┼──────────────────────────
revenue_fy2023      │ revenue_fy23    │ Revenue FY2023 in ₹ Cr
revenue_fy2024      │ revenue_fy24    │ Revenue FY2024 in ₹ Cr
revenue_fy2025      │ revenue_fy25    │ Revenue FY2025 in ₹ Cr
revenue_fy2026e     │ revenue_fy26    │ Revenue FY2026E in ₹ Cr
revenue_fy2027e     │ revenue_fy27    │ Revenue FY2027E in ₹ Cr
revenue_fy2028e     │ revenue_fy28    │ Revenue FY2028E in ₹ Cr
ebitda_fy2023       │ ebitda_fy23     │ EBITDA FY2023 in ₹ Cr
ebitda_fy2024       │ ebitda_fy24     │ EBITDA FY2024 in ₹ Cr
ebitda_fy2025       │ ebitda_fy25     │ EBITDA FY2025 in ₹ Cr
ebitda_fy2026e      │ ebitda_fy26     │ EBITDA FY2026E in ₹ Cr
ebitda_fy2027e      │ ebitda_fy27     │ EBITDA FY2027E in ₹ Cr
ebitda_fy2028e      │ ebitda_fy28     │ EBITDA FY2028E in ₹ Cr
pat_fy2023          │ pat_fy23        │ PAT FY2023 in ₹ Cr
pat_fy2024          │ pat_fy24        │ PAT FY2024 in ₹ Cr
pat_fy2025          │ pat_fy25        │ PAT FY2025 in ₹ Cr
pat_fy2026e         │ pat_fy26        │ PAT FY2026E in ₹ Cr
pat_fy2027e         │ pat_fy27        │ PAT FY2027E in ₹ Cr
pat_fy2028e         │ pat_fy28        │ PAT FY2028E in ₹ Cr


═══════════════════════════════════════════════════════════════════
 TOTAL FIELD COUNT PER SCHEDULE
═══════════════════════════════════════════════════════════════════

DAILY:     ~48 fields  (26 scraped from Yahoo + 22 calculated)
WEEKLY:    ~83 fields  (65 scraped from Screener + 18 calculated)
BIWEEKLY:  ~65 fields  (45 scraped from Trendlyne+GoIndia + 20 calc)
QUARTERLY: ~83 fields  (same as Weekly — safety net refresh)

Note: Many fields overlap between sources (e.g. current_price from
Yahoo AND Screener). When multiple sources provide the same field,
the LAST scraper's value wins.

═══════════════════════════════════════════════════════════════════
 END OF FIELD REFERENCE
═══════════════════════════════════════════════════════════════════
