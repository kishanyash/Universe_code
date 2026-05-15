# 📊 All Fetching — Complete Documentation

> **Batch Financial Data Aggregation System for Indian Equities**
>
> Last Updated: 2026-02-24

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Data Sources & Scrapers](#3-data-sources--scrapers)
4. [Schedule — What Updates When](#4-schedule--what-updates-when)
5. [Detailed Column Reference](#5-detailed-column-reference)
6. [Calculation Engine](#6-calculation-engine)
7. [Database Schema](#7-database-schema)
8. [API Endpoints](#8-api-endpoints)
9. [n8n Workflows](#9-n8n-workflows)
10. [Deployment](#10-deployment)
11. [Monitoring & Troubleshooting](#11-monitoring--troubleshooting)

---

## 1. Overview

### What is this?

This system automatically scrapes financial data for Indian equities from **4 different sources**, calculates derived metrics, and stores everything in a **Supabase PostgreSQL database** (`equity_universe` table). It runs on a **VPS** (72.61.226.16) and is triggered by **n8n workflows** on a daily/weekly/biweekly/quarterly schedule.

### What problem does it solve?

Instead of manually looking up 166+ financial parameters across multiple websites for hundreds of stocks, this system:

- Scrapes **current prices, returns, volume** daily from Yahoo Finance (fast API)
- Scrapes **financials (TTM P&L, ratios, balance sheet, quarterly results)** weekly from Screener.in
- Scrapes **forward estimates & analyst target prices** biweekly from Trendlyne & GoIndiaStocks
- Runs a **post-earnings refresh** quarterly via Screener.in (Jan/Apr/Jul/Oct)
- **Calculates** 30+ derived metrics (margins, CAGRs, P/E, P/B, etc.)
- Writes everything to a single database table keyed by `isin_code`
- **No schedule overlap** — each tier only scrapes what's unique to that frequency

### Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.11 |
| **Web API** | Flask + Gunicorn |
| **Database** | Supabase (PostgreSQL) |
| **Scraping** | `yfinance` (API), `requests` + BeautifulSoup (HTTP), Selenium + Chrome (browser) |
| **Scheduling** | n8n (workflow automation) |
| **Hosting** | VPS at 72.61.226.16:5001 |
| **Container** | Docker (optional, Dockerfile provided) |

---

## 2. Architecture

### System Flow

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│   n8n         │────>│  Flask API        │────>│  Batch Processor    │
│  (Scheduler)  │     │  app.py           │     │  batch_processor.py │
│               │     │  POST /webhook/*  │     │                    │
└──────────────┘     └──────────────────┘     └────────┬───────────┘
                                                        │
                           ┌────────────────────────────┼────────────────────────────┐
                           │                            │                            │
                     ┌─────▼──────┐  ┌─────────────┐  ┌▼────────────┐  ┌────────────▼─┐
                     │ Yahoo      │  │ Screener.in  │  │ Trendlyne   │  │ GoIndiaStocks│
                     │ Finance    │  │ (HTTP)       │  │ (Selenium)  │  │ (Selenium)   │
                     │ (yfinance) │  │              │  │             │  │              │
                     └─────┬──────┘  └──────┬───────┘  └──────┬──────┘  └──────┬───────┘
                           │                │                 │                │
                           └────────────────┴─────────┬───────┴────────────────┘
                                                      │
                                              ┌───────▼────────┐
                                              │  Calculations   │
                                              │  calculations.py│
                                              │  (Derived       │
                                              │   Metrics)      │
                                              └───────┬────────┘
                                                      │
                                              ┌───────▼────────┐
                                              │   Supabase      │
                                              │   equity_       │
                                              │   universe      │
                                              └────────────────┘
```

### File Structure

```
all_fetching/
├── app.py                  # Flask API (webhook endpoints for n8n)
├── batch_processor.py      # Core engine (fetch companies → run scrapers → write DB)
├── calculations.py         # Derived financial metrics
├── config.py               # Credentials, schedules, column whitelist, batch config
├── utils.py                # Shared helpers (Chrome driver, number parsing, CAGR)
├── .env                    # Environment variables (secrets)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker containerization
├── docker-compose.yml      # Docker Compose config
│
├── scrapers/
│   ├── __init__.py          # Scraper registry (SCRAPER_MAP)
│   ├── yahoo_finance.py     # Yahoo Finance via yfinance API
│   ├── screener.py          # Screener.in via HTTP + BeautifulSoup
│   ├── trendlyne.py         # Trendlyne via Selenium (headless Chrome)
│   └── go_india_stocks.py   # GoIndiaStocks via Selenium (headless Chrome)
│
├── n8n_workflows/
│   ├── daily_sync.json      # Daily n8n workflow
│   ├── weekly_sync.json     # Weekly n8n workflow
│   ├── biweekly_sync.json   # Biweekly n8n workflow
│   └── quarterly_sync.json  # Quarterly n8n workflow
│
└── run_all.py               # Test harness (run all scrapers for 1 stock)
```

---

## 3. Data Sources & Scrapers

### 3.1 Yahoo Finance (`scrapers/yahoo_finance.py`)

| Property | Value |
|---|---|
| **Method** | `yfinance` Python API (no browser needed) |
| **Speed** | Fast (~2s per stock, 3 parallel workers) |
| **Authentication** | None required |
| **Ticker Format** | `{NSE_CODE}.NS` or `{BSE_CODE}.BO` |
| **Rate Limiting** | Auto-retries on 429 errors (10s/20s/40s backoff) |

**Fields scraped:**

| Column | Description | Unit |
|---|---|---|
| `current_price` | Live market price | ₹ |
| `market_cap` | Market capitalization | ₹ Crores |
| `enterprise_value` | Enterprise value | ₹ Crores |
| `volume` | Trading volume | Shares |
| `high_52_week` | 52-week high price | ₹ |
| `low_52_week` | 52-week low price | ₹ |
| `return_down_from_52w_high` | % below 52w high | % |
| `return_up_from_52w_low` | % above 52w low | % |
| `return_1m` | 1-month return | % |
| `return_3m` | 3-month return | % |
| `return_6m` | 6-month return | % |
| `return_12m` | 12-month return | % |
| `target_price_high` | Analyst high target | ₹ |
| `target_price_low` | Analyst low target | ₹ |
| `consensus_target_price` | Analyst mean target | ₹ |
| `revenue_fy2026e` / `revenue_fy26` | Revenue estimate FY26 | ₹ Crores |
| `revenue_fy2027e` / `revenue_fy27` | Revenue estimate FY27 | ₹ Crores |
| `revenue_fy2028e` / `revenue_fy28` | Revenue estimate FY28 | ₹ Crores |
| `eps_fy2026e` | EPS estimate FY26 | ₹ |
| `eps_fy2027e` | EPS estimate FY27 | ₹ |
| `eps_fy2028e` | EPS estimate FY28 | ₹ |
| `dividend_yield` | Dividend yield | % |
| `num_equity_shares` | Shares outstanding | Crores |
| `google_code` | Google Finance code | e.g. `NSE:RELIANCE` |
| `nse_bom_code` | BSE BOM code | e.g. `BOM:500325` |

---

### 3.2 Screener.in — Daily (`scrapers/screener.py` → `scrape_screener_daily`)

| Property | Value |
|---|---|
| **Method** | HTTP GET + BeautifulSoup HTML parsing |
| **Speed** | Medium (~2s per stock, sequential) |
| **Authentication** | None (public pages, no login needed) |
| **URL Pattern** | `https://www.screener.in/company/{NSE_CODE}/consolidated/` |

**Fields scraped:**

**Market Data (from Top Ratios bar):**

| Column | Description |
|---|---|
| `current_price` | Current stock price |
| `market_cap` | Market cap (₹ Crores) |
| `high_52_week` | 52-week high |
| `low_52_week` | 52-week low |
| `book_value` | Book value per share |
| `face_value` | Face value |
| `dividend_yield` | Dividend yield (%) |
| `pe_ttm` | Stock P/E (TTM) |
| `roce` | Return on Capital Employed (%) |
| `roe` | Return on Equity (%) |

**Sector Classification (from Peers section):**

| Column | Description |
|---|---|
| `broad_sector` | e.g. "Commodities" |
| `sector` | e.g. "Oil & Gas" |
| `broad_industry` | e.g. "Oil Exploration" |
| `industry` | e.g. "Crude Oil & Natural Gas" |

**Quarterly Results (from Quarters table):**

| Column | Description |
|---|---|
| `quarterly_results_date` | Date of latest quarter (e.g. `2025-12-31`) |
| `sales_latest_qtr` | Revenue – latest quarter (₹ Cr) |
| `op_profit_latest_qtr` | Operating profit – latest quarter (₹ Cr) |
| `pat_latest_qtr` | PAT – latest quarter (₹ Cr) |
| `ebitda_margin_latest_qtr` | EBITDA margin – latest quarter (%) |
| `pat_margin_latest_qtr` | PAT margin – latest quarter (%) |
| `sales_preceding_qtr` | Revenue – preceding quarter (₹ Cr) |
| `op_profit_preceding_qtr` | Op profit – preceding quarter (₹ Cr) |
| `pat_preceding_qtr` | PAT – preceding quarter (₹ Cr) |
| `revenue_growth_qoq` | Revenue QoQ growth (%) |
| `ebitda_growth_qoq` | EBITDA QoQ growth (%) |
| `pat_growth_qoq` | PAT QoQ growth (%) |
| `sales_growth_yoy_qtr` | Revenue YoY (vs same quarter last year) (%) |
| `profit_growth_yoy_qtr` | Profit YoY (vs same quarter last year) (%) |

**Profit & Loss — TTM (from P&L table, last column = TTM):**

| Column | Description |
|---|---|
| `sales_ttm_screener` / `revenue_ttm` | Revenue TTM (₹ Cr) |
| `op_profit_ttm` / `ebitda_ttm` | Operating Profit / EBITDA TTM (₹ Cr) |
| `pat_ttm_screener` / `pat_ttm` | PAT TTM (₹ Cr) |
| `eps_ttm` / `eps_ttm_actual` | EPS TTM (₹) |
| `ebitda_margin_ttm` | EBITDA Margin TTM (%) |
| `pat_margin_ttm` | PAT Margin TTM (%) |
| `opm_last_year` | OPM last full year (%) |
| `ps_ttm` | Price-to-Sales TTM |
| `ev_ebitda_ttm` | EV/EBITDA TTM |

**Historical CAGRs (calculated from P&L annual data):**

| Column | Description |
|---|---|
| `revenue_cagr_hist_2yr` | Revenue CAGR last 2 years (%) |
| `ebitda_cagr_hist_2yr` | EBITDA CAGR last 2 years (%) |
| `pat_cagr_hist_2yr` | PAT CAGR last 2 years (%) |
| `eps_cagr_hist_2yr` | EPS CAGR last 2 years (%) |

**Balance Sheet (from Balance Sheet table, latest year):**

| Column | Description |
|---|---|
| `debt` | Total borrowings (₹ Cr) |
| `net_worth` | Equity + Reserves (₹ Cr) |
| `cash_equivalents` | Investments + 30% of Other Assets (₹ Cr) |
| `net_debt` | Debt − Cash (₹ Cr) |
| `enterprise_value` | Market Cap + Net Debt (₹ Cr) |
| `num_equity_shares` | Equity Capital / Face Value (Crores) |
| `cwip` | Capital Work in Progress (₹ Cr) |
| `net_block` | Fixed Assets / Net Block (₹ Cr) |
| `cwip_to_net_block_ratio` | CWIP / Net Block × 100 (%) |

**Ratios (from Ratios table):**

| Column | Description |
|---|---|
| `roce` | Return on Capital Employed (%) |
| `roe` | Return on Equity (%) |
| `roic` | Return on Invested Capital (%) |
| `asset_turnover_ratio` | Revenue / Total Assets |
| `working_capital_to_sales_ratio` | Working Capital Days / 365 |

**Shareholding (from Shareholding table):**

| Column | Description |
|---|---|
| `promoter_holding_pct` | Promoter holding (%) |
| `unpledged_promoter_holding_pct` | Unpledged promoter holding (%) |

**Historical P/E (calculated from EPS history):**

| Column | Description |
|---|---|
| `pe_avg_3yr` | Average P/E over last 3 FYs |
| `pe_avg_5yr` | Average P/E over last 5 FYs |
| `pe_high_hist` | Highest historical P/E |
| `pe_low_hist` | Lowest historical P/E |

**52W Return Derivatives:**

| Column | Description |
|---|---|
| `return_down_from_52w_high` | % below 52-week high |
| `return_up_from_52w_low` | % above 52-week low |

---

### 3.3 Screener.in — Full (`scrapers/screener.py` → `scrape_screener_full`)

Same as Screener Daily (above), **PLUS** per-fiscal-year financials:

**Per-FY Financials (from P&L annual columns — FY23, FY24, FY25):**

| Column | Description |
|---|---|
| `revenue_fy2023` / `revenue_fy23` | Revenue FY2023 (₹ Cr) |
| `revenue_fy2024` / `revenue_fy24` | Revenue FY2024 (₹ Cr) |
| `revenue_fy2025` / `revenue_fy25` | Revenue FY2025 (₹ Cr) |
| `ebitda_fy2023` / `ebitda_fy23` | EBITDA FY2023 (₹ Cr) |
| `ebitda_fy2024` / `ebitda_fy24` | EBITDA FY2024 (₹ Cr) |
| `ebitda_fy2025` / `ebitda_fy25` | EBITDA FY2025 (₹ Cr) |
| `pat_fy2023` / `pat_fy23` | PAT FY2023 (₹ Cr) |
| `pat_fy2024` / `pat_fy24` | PAT FY2024 (₹ Cr) |
| `pat_fy2025` / `pat_fy25` | PAT FY2025 (₹ Cr) |
| `eps_fy2023` | EPS FY2023 (₹) |
| `eps_fy2024` | EPS FY2024 (₹) |
| `eps_fy2025` | EPS FY2025 (₹) |

> Note: `scrape_screener_full()` currently calls `scrape_screener_daily()` — both extract the same data including per-FY columns. The "full" mode exists as a separate entry point for the weekly schedule.

---

### 3.4 Trendlyne (`scrapers/trendlyne.py`)

| Property | Value |
|---|---|
| **Method** | Selenium (headless Chrome) — requires login |
| **Speed** | Slow (~8s per stock, sequential) |
| **Authentication** | Email/password login (TRENDLYNE_USERNAME/PASSWORD) |
| **URL Pattern** | `https://trendlyne.com/equity/{NSE_CODE}/stock-page` |

**Fields scraped:**

**Target Prices (from Forecaster block & Consensus page):**

| Column | Description |
|---|---|
| `consensus_target_price` | Average analyst target price (₹) |
| `target_price_high` | Highest analyst target price (₹) |
| `target_price_low` | Lowest analyst target price (₹) |

**Annual Actuals (from Annual Results table — FY23, FY24, FY25):**

| Column | Description |
|---|---|
| `revenue_fy2023` / `revenue_fy23` | Operating Revenue FY2023 (₹ Cr) |
| `revenue_fy2024` / `revenue_fy24` | Operating Revenue FY2024 (₹ Cr) |
| `revenue_fy2025` / `revenue_fy25` | Operating Revenue FY2025 (₹ Cr) |
| `ebitda_fy2023` / `ebitda_fy23` | EBITDA FY2023 (₹ Cr) |
| `ebitda_fy2024` / `ebitda_fy24` | EBITDA FY2024 (₹ Cr) |
| `ebitda_fy2025` / `ebitda_fy25` | EBITDA FY2025 (₹ Cr) |
| `pat_fy2023` / `pat_fy23` | Net Profit FY2023 (₹ Cr) |
| `pat_fy2024` / `pat_fy24` | Net Profit FY2024 (₹ Cr) |
| `pat_fy2025` / `pat_fy25` | Net Profit FY2025 (₹ Cr) |
| `eps_fy2023` | EPS FY2023 (₹) |
| `eps_fy2024` | EPS FY2024 (₹) |
| `eps_fy2025` | EPS FY2025 (₹) |

**Forward Estimates (from Consensus Estimates page — FY26E, FY27E):**

| Column | Description |
|---|---|
| `revenue_fy2026e` / `revenue_fy26` | Revenue estimate FY2026 (₹ Cr) |
| `revenue_fy2027e` / `revenue_fy27` | Revenue estimate FY2027 (₹ Cr) |
| `ebitda_fy2026e` / `ebitda_fy26` | EBITDA estimate FY2026 (calculated: EBIT + Depreciation) (₹ Cr) |
| `ebitda_fy2027e` / `ebitda_fy27` | EBITDA estimate FY2027 (₹ Cr) |
| `pat_fy2026e` / `pat_fy26` | PAT estimate FY2026 (₹ Cr) |
| `pat_fy2027e` / `pat_fy27` | PAT estimate FY2027 (₹ Cr) |
| `eps_fy2026e` | EPS estimate FY2026 (₹) |
| `eps_fy2027e` | EPS estimate FY2027 (₹) |

---

### 3.5 GoIndiaStocks (`scrapers/go_india_stocks.py`)

| Property | Value |
|---|---|
| **Method** | Selenium (headless Chrome) |
| **Speed** | Slow (~6s per stock, sequential) |
| **Authentication** | None (public pages) |
| **URL Pattern** | `https://www.goindiastocks.com/companyinfo/{NSE_CODE}` |

**Fields scraped:**

**Target Prices (from Basic Info section):**

| Column | Description |
|---|---|
| `target_price_high` | Highest analyst target (₹) |
| `consensus_target_price` | Average analyst target (₹) |
| `target_price_low` | Lowest analyst target (₹) |

**Actuals & Forward Estimates (from Financials table — FY23 to FY28E):**

| Column | Description |
|---|---|
| `revenue_fy2023` / `revenue_fy23` | Revenue FY2023 (₹ Cr) |
| `revenue_fy2024` / `revenue_fy24` | Revenue FY2024 (₹ Cr) |
| `revenue_fy2025` / `revenue_fy25` | Revenue FY2025 (₹ Cr) |
| `revenue_fy2026e` / `revenue_fy26` | Revenue estimate FY2026 (₹ Cr) |
| `revenue_fy2027e` / `revenue_fy27` | Revenue estimate FY2027 (₹ Cr) |
| `revenue_fy2028e` / `revenue_fy28` | Revenue estimate FY2028 (₹ Cr) |
| `ebitda_fy2023` – `ebitda_fy2028e` | EBITDA (or PPOP for banks) for each FY (₹ Cr) |
| `pat_fy2023` – `pat_fy2028e` | PAT for each FY (₹ Cr) |
| `eps_fy2023` – `eps_fy2028e` | Diluted EPS for each FY (₹) |

---

## 4. Schedule — What Updates When

> **IMPORTANT:** Each schedule ONLY scrapes what's unique to that frequency.
> No duplication — saves time and avoids rate limiting.

### 4.1 Overview

| Schedule | When | Source | What Gets Updated | Est. Time (895 stocks) |
|---|---|---|---|---|
| **DAILY** | Every day @ 6:30 AM IST | Yahoo Finance ONLY | Prices, returns, volume, market cap, 52w range, targets, estimates | ~20 min |
| **WEEKLY** | Every Monday @ 7:30 AM IST | Screener.in ONLY | TTM P&L, ratios, balance sheet, quarterly results, sectors, shareholding, per-FY actuals | ~50 min |
| **BIWEEKLY** | 1st & 15th @ 8:30 AM IST | Trendlyne + GoIndiaStocks ONLY | Analyst target prices, forward estimates (FY26E–FY28E) | ~3-4 hours |
| **QUARTERLY** | 1st of Jan/Apr/Jul/Oct @ 9:30 AM IST | Screener.in ONLY | Post-earnings refresh — captures new quarterly results and updated annual data | ~50 min |

### 4.2 Detailed: DAILY Schedule

**Runs:** Every day at 06:30 AM IST (01:00 UTC)
**Sources:** `yahoo_finance` ONLY
**API Endpoint:** `POST /webhook/daily`
**Why daily?** Prices, volume, and returns change every trading day.

**Columns updated by Yahoo Finance:**

```
current_price, market_cap, enterprise_value, volume,
high_52_week, low_52_week,
return_down_from_52w_high, return_up_from_52w_low,
return_1m, return_3m, return_6m, return_12m,
target_price_high, target_price_low, consensus_target_price,
revenue_fy2026e, revenue_fy2027e, revenue_fy2028e,
eps_fy2026e, eps_fy2027e, eps_fy2028e,
dividend_yield, beta, num_equity_shares,
google_code, nse_bom_code
```

**Columns added by Calculation Engine (after scraping):**

```
consensus_target_price, consensus_upside_pct,
potential_upside_high, potential_upside_low,
pe_fy24..pe_fy28, pe_fy2026e..pe_fy2028e,
pb_fy24..pb_fy28,
sotp_value
```

### 4.3 Detailed: WEEKLY Schedule

**Runs:** Every Monday at 07:30 AM IST (02:00 UTC)
**Sources:** `screener_full` ONLY
**API Endpoint:** `POST /webhook/weekly`
**Why weekly?** Financials, ratios, balance sheet, and quarterly results change at most once a week.

**Columns updated by Screener.in:**

```
current_price, market_cap, high_52_week, low_52_week,
book_value, face_value, dividend_yield,
pe_ttm, roce, roe,
broad_sector, sector, broad_industry, industry,
quarterly_results_date,
sales_latest_qtr, op_profit_latest_qtr, pat_latest_qtr,
ebitda_margin_latest_qtr, pat_margin_latest_qtr,
sales_preceding_qtr, op_profit_preceding_qtr, pat_preceding_qtr,
revenue_growth_qoq, ebitda_growth_qoq, pat_growth_qoq,
sales_growth_yoy_qtr, profit_growth_yoy_qtr,
sales_ttm_screener, revenue_ttm, op_profit_ttm, ebitda_ttm,
pat_ttm_screener, pat_ttm, eps_ttm, eps_ttm_actual,
ebitda_margin_ttm, pat_margin_ttm, opm_last_year,
revenue_cagr_hist_2yr, ebitda_cagr_hist_2yr,
pat_cagr_hist_2yr, eps_cagr_hist_2yr,
debt, net_worth, cash_equivalents, net_debt, enterprise_value,
num_equity_shares, cwip, net_block, cwip_to_net_block_ratio,
ps_ttm, ev_ebitda_ttm,
roce, roe, roic, asset_turnover_ratio,
working_capital_to_sales_ratio,
promoter_holding_pct, unpledged_promoter_holding_pct,
pe_avg_3yr, pe_avg_5yr, pe_high_hist, pe_low_hist,
return_down_from_52w_high, return_up_from_52w_low,
revenue_fy2023..fy2025, ebitda_fy2023..fy2025,
pat_fy2023..fy2025, eps_fy2023..fy2025
```

**Columns added by Calculation Engine:**

```
ebitda_margin_ttm_calc, pat_margin_ttm_calc,
ebitda_margin_fy2023..fy2025, pat_margin_fy2023..fy2025,
ebitda_margin_growth_qoq_bps, pat_margin_growth_qoq_bps,
last_annual_result_date
```

### 4.4 Detailed: BIWEEKLY Schedule

**Runs:** 1st & 15th of every month at 08:30 AM IST (03:00 UTC)
**Sources:** `trendlyne` + `go_india_stocks` ONLY
**API Endpoint:** `POST /webhook/biweekly`
**Why biweekly?** Analyst consensus and forward estimates update infrequently.

**Columns updated by Trendlyne:**

```
consensus_target_price,
target_price_high, target_price_low,
revenue_fy2023..fy2025, ebitda_fy2023..fy2025,
pat_fy2023..fy2025, eps_fy2023..fy2025,
revenue_fy2026e..fy2027e, ebitda_fy2026e..fy2027e,
pat_fy2026e..fy2027e, eps_fy2026e..fy2027e
```

**Columns updated by GoIndiaStocks:**

```
target_price_high, consensus_target_price, target_price_low,
revenue_fy2023..fy2028e, ebitda_fy2023..fy2028e,
pat_fy2023..fy2028e, eps_fy2023..fy2028e
```

**Columns added by Calculation Engine:**

```
ebitda_margin_fy2026e..fy2028e, pat_margin_fy2026e..fy2028e,
ev_ebitda_fy2026e..fy2028e, ps_fy2026e..fy2028e,
revenue_cagr_fwd_2yr, ebitda_cagr_fwd_2yr,
pat_cagr_fwd_2yr, eps_cagr_fwd_2yr
```

### 4.5 Detailed: QUARTERLY Schedule

**Runs:** 1st of January, April, July, October at 09:30 AM IST (04:00 UTC)
**Sources:** `screener_full` ONLY (post-earnings refresh)
**API Endpoint:** `POST /webhook/quarterly`
**Why quarterly?** After earnings season, companies publish new quarterly/annual results. This ensures the latest financials are captured even if a weekly run was missed.

Updates the **same columns as Weekly** above. Acts as a safety net after earnings announcements.

---

## 5. Detailed Column Reference

### Complete list of all 166 columns in `equity_universe`

#### Identity (6 columns)
| Column | Source | Schedule |
|---|---|---|
| `company_name` | Pre-populated | — |
| `isin_code` | Pre-populated (primary key) | — |
| `nse_code` | Pre-populated | — |
| `bse_code` | Pre-populated | — |
| `google_code` | Yahoo Finance | Daily |
| `nse_bom_code` | Yahoo Finance | Daily |

#### Sectors (4 columns)
| Column | Source | Schedule |
|---|---|---|
| `broad_sector` | Screener | Weekly |
| `sector` | Screener | Weekly |
| `broad_industry` | Screener | Weekly |
| `industry` | Screener | Weekly |

#### Market Data (10 columns)
| Column | Source | Schedule |
|---|---|---|
| `current_price` | Yahoo (daily) + Screener (weekly) | Daily / Weekly |
| `market_cap` | Yahoo (daily) + Screener (weekly) | Daily / Weekly |
| `high_52_week` | Yahoo (daily) + Screener (weekly) | Daily / Weekly |
| `low_52_week` | Yahoo (daily) + Screener (weekly) | Daily / Weekly |
| `volume` | Yahoo | Daily |
| `enterprise_value` | Yahoo (daily) + Screener calc (weekly) | Daily / Weekly |
| `face_value` | Screener | Weekly |
| `book_value` | Screener | Weekly |
| `dividend_yield` | Yahoo (daily) + Screener (weekly) | Daily / Weekly |
| `num_equity_shares` | Yahoo (daily) + Screener (weekly) | Daily / Weekly |

#### Valuation — TTM (7 columns)
| Column | Source | Schedule |
|---|---|---|
| `pe_ttm` | Screener | Weekly |
| `ev_ebitda_ttm` | Screener (calc) | Weekly |
| `ps_ttm` | Screener (calc) | Weekly |
| `pe_avg_3yr` | Screener (calc) | Weekly |
| `pe_avg_5yr` | Screener (calc) | Weekly |
| `pe_high_hist` | Screener (calc) | Weekly |
| `pe_low_hist` | Screener (calc) | Weekly |

#### Profitability (10 columns)
| Column | Source | Schedule |
|---|---|---|
| `roe` | Screener | Weekly |
| `roce` | Screener | Weekly |
| `roic` | Screener (calc) | Weekly |
| `ebitda_margin_ttm` | Screener | Weekly |
| `ebitda_margin_ttm_calc` | Calculation Engine | Weekly |
| `opm_last_year` | Screener | Weekly |
| `pat_margin_ttm` | Screener | Weekly |
| `pat_margin_ttm_calc` | Calculation Engine | Weekly |
| `asset_turnover_ratio` | Screener | Weekly |
| `working_capital_to_sales_ratio` | Screener | Weekly |

#### P&L — TTM (8 columns)
| Column | Source | Schedule |
|---|---|---|
| `sales_ttm_screener` | Screener | Weekly |
| `revenue_ttm` | Screener | Weekly |
| `op_profit_ttm` | Screener | Weekly |
| `ebitda_ttm` | Screener | Weekly |
| `pat_ttm` | Screener | Weekly |
| `pat_ttm_screener` | Screener | Weekly |
| `eps_ttm` | Screener | Weekly |
| `eps_ttm_actual` | Screener | Weekly |

#### Balance Sheet (7 columns)
| Column | Source | Schedule |
|---|---|---|
| `debt` | Screener | Weekly |
| `cash_equivalents` | Screener (calc) | Weekly |
| `net_debt` | Screener (calc) | Weekly |
| `net_worth` | Screener (calc) | Weekly |
| `net_block` | Screener | Weekly |
| `cwip` | Screener | Weekly |
| `cwip_to_net_block_ratio` | Screener (calc) | Weekly |

#### Shareholding (2 columns)
| Column | Source | Schedule |
|---|---|---|
| `promoter_holding_pct` | Screener | Weekly |
| `unpledged_promoter_holding_pct` | Screener (calc) | Weekly |

#### Quarterly Results (15 columns)
| Column | Source | Schedule |
|---|---|---|
| `quarterly_results_date` | Screener | Weekly |
| `sales_latest_qtr` | Screener | Weekly |
| `op_profit_latest_qtr` | Screener | Weekly |
| `pat_latest_qtr` | Screener | Weekly |
| `ebitda_margin_latest_qtr` | Screener | Weekly |
| `pat_margin_latest_qtr` | Screener (calc) | Weekly |
| `sales_preceding_qtr` | Screener | Weekly |
| `op_profit_preceding_qtr` | Screener | Weekly |
| `pat_preceding_qtr` | Screener | Weekly |
| `revenue_growth_qoq` | Screener (calc) | Weekly |
| `ebitda_growth_qoq` | Screener (calc) | Weekly |
| `pat_growth_qoq` | Screener (calc) | Weekly |
| `ebitda_margin_growth_qoq_bps` | Calculation Engine | Weekly |
| `pat_margin_growth_qoq_bps` | Calculation Engine | Weekly |
| `sales_growth_yoy_qtr` | Screener (calc) | Weekly |
| `profit_growth_yoy_qtr` | Screener (calc) | Weekly |

#### Returns (6 columns)
| Column | Source | Schedule |
|---|---|---|
| `return_down_from_52w_high` | Yahoo + Screener | Daily |
| `return_up_from_52w_low` | Yahoo + Screener | Daily |
| `return_1m` | Yahoo | Daily |
| `return_3m` | Yahoo | Daily |
| `return_6m` | Yahoo | Daily |
| `return_12m` | Yahoo | Daily |

#### Historical CAGRs (8 columns)
| Column | Source | Schedule |
|---|---|---|
| `revenue_cagr_hist_2yr` | Screener (calc) | Weekly |
| `ebitda_cagr_hist_2yr` | Screener (calc) | Weekly |
| `pat_cagr_hist_2yr` | Screener (calc) | Weekly |
| `eps_cagr_hist_2yr` | Screener (calc) | Weekly |
| `revenue_cagr_fwd_2yr` | Calculation Engine | Biweekly |
| `ebitda_cagr_fwd_2yr` | Calculation Engine | Biweekly |
| `pat_cagr_fwd_2yr` | Calculation Engine | Biweekly |
| `eps_cagr_fwd_2yr` | Calculation Engine | Biweekly |

#### Per-FY Financials — Actuals (18 columns, long + short naming)
| Column | Source | Schedule |
|---|---|---|
| `revenue_fy2023` / `revenue_fy23` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `revenue_fy2024` / `revenue_fy24` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `revenue_fy2025` / `revenue_fy25` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `ebitda_fy2023` / `ebitda_fy23` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `ebitda_fy2024` / `ebitda_fy24` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `ebitda_fy2025` / `ebitda_fy25` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `pat_fy2023` / `pat_fy23` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `pat_fy2024` / `pat_fy24` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `pat_fy2025` / `pat_fy25` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |

#### Per-FY Financials — Estimates (18 columns, long + short naming)
| Column | Source | Schedule |
|---|---|---|
| `revenue_fy2026e` / `revenue_fy26` | Yahoo + Trendlyne + GoIndia | Daily / Biweekly |
| `revenue_fy2027e` / `revenue_fy27` | Yahoo + Trendlyne + GoIndia | Daily / Biweekly |
| `revenue_fy2028e` / `revenue_fy28` | Yahoo + GoIndia | Daily / Biweekly |
| `ebitda_fy2026e` / `ebitda_fy26` | Trendlyne + GoIndia (+ Calc) | Biweekly |
| `ebitda_fy2027e` / `ebitda_fy27` | Trendlyne + GoIndia (+ Calc) | Biweekly |
| `ebitda_fy2028e` / `ebitda_fy28` | GoIndia (+ Calc extrapolation) | Biweekly |
| `pat_fy2026e` / `pat_fy26` | Trendlyne + GoIndia (+ Calc) | Biweekly |
| `pat_fy2027e` / `pat_fy27` | Trendlyne + GoIndia (+ Calc) | Biweekly |
| `pat_fy2028e` / `pat_fy28` | GoIndia (+ Calc extrapolation) | Biweekly |

#### Per-FY EPS (6 columns)
| Column | Source | Schedule |
|---|---|---|
| `eps_fy2023` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `eps_fy2024` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `eps_fy2025` | Screener + Trendlyne + GoIndia | Weekly / Biweekly |
| `eps_fy2026e` | Yahoo + Trendlyne + GoIndia | Daily / Biweekly |
| `eps_fy2027e` | Yahoo + Trendlyne + GoIndia | Daily / Biweekly |
| `eps_fy2028e` | Yahoo + GoIndia (+ Calc) | Daily / Biweekly |

#### Per-FY Margins (12 columns)
| Column | Source | Schedule |
|---|---|---|
| `ebitda_margin_fy2023..fy2025` | Calculation Engine | Weekly |
| `ebitda_margin_fy2026e..fy2028e` | Calculation Engine | Biweekly |
| `pat_margin_fy2023..fy2025` | Calculation Engine | Weekly |
| `pat_margin_fy2026e..fy2028e` | Calculation Engine | Biweekly |

#### Per-FY Valuations (18 columns)
| Column | Source | Schedule |
|---|---|---|
| `pe_fy24..pe_fy28` | Calculation Engine | Daily |
| `pe_fy2026e..pe_fy2028e` | Calculation Engine | Daily |
| `pb_fy24..pb_fy28` | Calculation Engine | Daily |
| `ev_ebitda_fy2026e..fy2028e` | Calculation Engine | Biweekly |
| `ps_fy2026e..fy2028e` | Calculation Engine | Biweekly |

#### Target Prices (7 columns)
| Column | Source | Schedule |
|---|---|---|
| `target_price_high` | Yahoo + Trendlyne + GoIndia | Daily / Biweekly |
| `target_price_low` | Yahoo + Trendlyne + GoIndia | Daily / Biweekly |
| `consensus_target_price` | Yahoo + Trendlyne + GoIndia + Calc | Daily / Biweekly |
| `consensus_upside_pct` | Calculation Engine | Daily |
| `potential_upside_high` | Calculation Engine | Daily |
| `potential_upside_low` | Calculation Engine | Daily |
| `sotp_value` | Calculation Engine (fallback) | Daily |

#### Dates & Timestamps (2 columns)
| Column | Source | Schedule |
|---|---|---|
| `last_annual_result_date` | Calculation Engine (fallback) | Daily |
| `updated_at` | System (auto-set on every write) | Every update |

---

## 6. Calculation Engine

**File:** `calculations.py` → `calculate_derived_fields(data)`

After all scrapers finish for a stock, the calculation engine runs and computes derived metrics. It modifies the data dict in-place.

### 6.1 Per-FY Margins

```
EBITDA Margin = EBITDA / Revenue × 100
PAT Margin = PAT / Revenue × 100
```

Calculated for: FY2023, FY2024, FY2025, FY2026E, FY2027E, FY2028E

### 6.2 TTM Margin Calculations

```
ebitda_margin_ttm_calc = EBITDA_TTM / Revenue_TTM × 100
pat_margin_ttm_calc = PAT_TTM / Revenue_TTM × 100
```

### 6.3 Missing Estimate Derivation

When GoIndiaStocks/Trendlyne don't provide estimates:

```
PAT = EPS × Number of Shares
EBITDA = Revenue × Historical EBITDA Margin
```

### 6.4 FY2028E Extrapolation

When FY28E is missing, extrapolated from FY27E:

```
metric_fy2028e = metric_fy2027e × 1.05  (5% flat growth)
```

### 6.5 Per-FY P/E

```
P/E = Current Price / EPS  (preferred)
P/E = Market Cap / PAT     (fallback)
```

Calculated for: FY24, FY25, FY26, FY27, FY28

### 6.6 Per-FY EV/EBITDA

```
EV/EBITDA = Enterprise Value / EBITDA
```

Calculated for: FY2026E, FY2027E, FY2028E

### 6.7 Per-FY P/S

```
P/S = Market Cap / Revenue
```

Calculated for: FY2026E, FY2027E, FY2028E

### 6.8 Per-FY P/B

```
P/B = Current Price / Book Value
```

Calculated for: FY24, FY25, FY26, FY27, FY28

### 6.9 Forward CAGRs (2-year)

```
CAGR = ((end_value / start_value) ^ (1/years) - 1) × 100
```

- `revenue_cagr_fwd_2yr` = CAGR(revenue_fy25, revenue_fy27e)
- `ebitda_cagr_fwd_2yr` = CAGR(ebitda_fy25, ebitda_fy27e)
- `pat_cagr_fwd_2yr` = CAGR(pat_fy25, pat_fy27e)
- `eps_cagr_fwd_2yr` = CAGR(eps_fy25, eps_fy27e)

### 6.10 Consensus Target & Upside

```
consensus_target_price = average(target_price_high, target_price_low)
consensus_upside_pct = (consensus - price) / price × 100
potential_upside_high = (high_target - price) / price × 100
potential_upside_low = (low_target - price) / price × 100
```

### 6.11 QoQ Margin Changes (BPS)

```
ebitda_margin_growth_qoq_bps = (latest_margin - preceding_margin) × 100
pat_margin_growth_qoq_bps = (latest_margin - preceding_margin) × 100
```

### 6.12 Fallbacks

```
asset_turnover_ratio = Revenue_TTM / (Net Worth + Debt)  [if missing]
sotp_value = target_price_high or current_price           [placeholder]
last_annual_result_date = quarterly_results_date or "2024-03-31"
```

### 6.13 Column Sync

Both naming conventions are kept in sync:

```
revenue_fy2023 ↔ revenue_fy23
revenue_fy2024 ↔ revenue_fy24
... (18 pairs total for revenue, ebitda, pat)
```

---

## 7. Database Schema

**Database:** Supabase PostgreSQL
**Table:** `public.equity_universe`
**Primary Key:** `(company_id, isin_code)`
**Unique Constraints:** `isin_code` (unique), `nse_code` (unique)

All monetary values are in **₹ Crores** unless otherwise noted.
All percentages are stored as **plain numbers** (e.g., 15.5 = 15.5%).

---

## 8. API Endpoints

**Base URL:** `http://72.61.226.16:5001`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check + running jobs |
| `POST` | `/webhook/daily` | Trigger daily sync |
| `POST` | `/webhook/weekly` | Trigger weekly sync |
| `POST` | `/webhook/biweekly` | Trigger biweekly sync |
| `POST` | `/webhook/quarterly` | Trigger quarterly full refresh |
| `POST` | `/webhook/single` | Sync a single stock by ISIN |
| `GET` | `/job/{job_id}` | Check status of a background job |
| `GET` | `/sources` | List available scrapers and schedules |

### Request Body (optional for webhook endpoints)

```json
{
  "isin_list": ["INE002A01018"],   // Optional: specific stocks
  "limit": 50,                      // Optional: max stocks
  "async": true                     // Run in background (default: true)
}
```

### Authentication

Header: `X-API-Secret: <your API_SECRET>`

> ⚠️ Requests are rejected if `API_SECRET` is unset or left as `"change-me-in-production"`.

---

## 9. n8n Workflows

### Files

```
n8n_workflows/
├── daily_sync.json       → Runs every day at 6:30 AM IST
├── weekly_sync.json      → Runs every Monday at 7:30 AM IST
├── biweekly_sync.json    → Runs 1st & 15th at 8:30 AM IST
└── quarterly_sync.json   → Runs 1st of Jan/Apr/Jul/Oct at 9:30 AM IST
```

### Workflow Pattern (all 4 follow this)

```
Cron Trigger
    ↓
POST /webhook/{tier}  (async=true)
    ↓
Job Started?
    ├── Yes → Poll /job/{id}  → Still Running?
    │                            ├── Yes → (loop back to poll)
    │                            └── No  → ✅ Success
    └── No  → ❌ Error
```

### Polling Intervals

| Workflow | Poll Interval | Reason |
|---|---|---|
| Daily | 60 seconds | Fast (Yahoo API + HTTP scraping) |
| Weekly | 120 seconds | Medium (Screener HTTP scraping) |
| Biweekly | 180 seconds | Slow (Selenium browser scraping) |
| Quarterly | 300 seconds | Very slow (ALL sources, full refresh) |

---

## 10. Deployment

### VPS Details

- **IP:** 72.61.226.16
- **Port:** 5001
- **User:** root
- **Path:** `/root/all_fetching`
- **Python:** 3.x with virtualenv at `/root/all_fetching/venv`

### Starting the Server

```bash
cd /root/all_fetching
source venv/bin/activate
nohup gunicorn --bind 0.0.0.0:5001 --timeout 600 --workers 2 app:app > server.log 2>&1 &
```

### Restarting After Code Update

```bash
# Upload from local machine
scp -r . root@72.61.226.16:/root/all_fetching

# On VPS
pkill gunicorn
cd /root/all_fetching
source venv/bin/activate
nohup gunicorn --bind 0.0.0.0:5001 --timeout 600 --workers 2 app:app > server.log 2>&1 &
```

### Rate Limiting Config

| Source | Batch Size | Delay Between Stocks | Max Workers |
|---|---|---|---|
| Yahoo Finance | 20 | 0.5s | 10 (parallel) |
| Screener Daily | 10 | 2.0s | 1 (sequential) |
| Screener Full | 10 | 2.0s | 1 (sequential) |
| Trendlyne | 5 | 8.0s | 1 (sequential) |
| GoIndiaStocks | 5 | 6.0s | 1 (sequential) |

---

## 11. Monitoring & Troubleshooting

### Check API Health

```bash
curl -s http://72.61.226.16:5001/health | python3 -m json.tool
```

### View Server Logs

```bash
tail -f /root/all_fetching/server.log        # Live logs
tail -n 100 /root/all_fetching/server.log    # Last 100 lines
```

### Check Job Status

```bash
curl -s http://72.61.226.16:5001/job/{JOB_ID} | python3 -m json.tool
```

### Verify Database Updates (Supabase SQL Editor)

```sql
-- Recently updated stocks
SELECT company_name, nse_code, current_price, market_cap, updated_at
FROM equity_universe
ORDER BY updated_at DESC
LIMIT 10;

-- Stocks updated today
SELECT COUNT(*) FROM equity_universe WHERE updated_at::date = CURRENT_DATE;

-- Check a specific stock
SELECT * FROM equity_universe WHERE nse_code = 'RELIANCE';

-- Stocks with missing estimates
SELECT company_name, nse_code, revenue_fy2026e, eps_fy2026e, target_price_high
FROM equity_universe
WHERE revenue_fy2026e IS NULL AND nse_code IS NOT NULL
ORDER BY market_cap DESC NULLS LAST
LIMIT 20;
```

### Common Issues

| Issue | Cause | Fix |
|---|---|---|
| Yahoo skipping stocks | Ticker not found (`.NS`/`.BO` suffix issue) | Check `nse_code`/`bse_code` in DB |
| Trendlyne errors | Login failed or page structure changed | Check credentials in `.env`, verify site manually |
| GoIndiaStocks timeout | Page didn't load in 30s | Increase `WebDriverWait` timeout |
| "No companies found" | Empty DB or wrong table name | Check `SUPABASE_TABLE` in config |
| Job stuck as "running" | Gunicorn worker crashed | Restart gunicorn |

---

*End of Documentation*
