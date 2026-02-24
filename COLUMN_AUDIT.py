"""
=============================================================================
COLUMN AUDIT - Maps every Supabase column to its data source
=============================================================================
This file documents which scraper/calculation populates each column.
Excludes chart_url columns (not fetched).

Key:  Y = Yahoo Finance | S = Screener.in | T = Trendlyne | G = GoIndia
      C = Calculated (calculations.py) | U = Universe sync (existing)
=============================================================================

IDENTITY (from Universe sync):
  company_id                        auto-generated PK
  isin_code                         U (from Google Sheet)
  nse_code                          U
  bse_code                          U
  company_name                      U
  created_at                        auto (Supabase default)
  updated_at                        auto (set on every write)

DERIVED CODES:
  google_code                       Y (NSE:SYMBOL or BOM:CODE)
  nse_bom_code                      Y (BOM:CODE)

SECTORS:
  broad_sector                      S
  sector                            S
  broad_industry                    S
  industry                          S

MARKET DATA:
  market_cap                        Y, S (Rs Crs)
  current_price                     Y, S
  high_52_week                      Y, S
  low_52_week                       Y, S
  volume                            Y
  face_value                        S
  book_value                        S
  dividend_yield                    Y, S
  num_equity_shares                 Y, S (Crores)

VALUATION:
  pe_ttm                            S
  ev_ebitda_ttm                     S, C
  ps_ttm                            S, C
  pe_avg_3yr                        S
  pe_avg_5yr                        S
  pe_high_hist                      S
  pe_low_hist                       S
  enterprise_value                  Y, S (Rs Crs)

PROFITABILITY:
  roe                               S
  roce                              S
  roic                              S
  ebitda_margin_ttm                 S
  pat_margin_ttm                    S
  opm_last_year                     S
  asset_turnover_ratio              S
  working_capital_to_sales_ratio    S

BALANCE SHEET (Rs Crs):
  debt                              S
  cash_equivalents                  S
  net_debt                          S
  net_worth                         S
  net_block                         S
  cwip                              S
  cwip_to_net_block_ratio           S
  eps_ttm_actual                    S
  eps_ttm                           S
  promoter_holding_pct              S
  unpledged_promoter_holding_pct    S

P&L TTM (Rs Crs):
  sales_ttm_screener                S
  revenue_ttm                       S
  op_profit_ttm                     S
  ebitda_ttm                        S, C
  pat_ttm                           S
  pat_ttm_screener                  S

TTM MARGINS (calculated):
  ebitda_margin_ttm_calc            C
  pat_margin_ttm_calc               C

QUARTERLY DATA:
  quarterly_results_date            S
  sales_latest_qtr                  S
  op_profit_latest_qtr              S
  pat_latest_qtr                    S
  ebitda_margin_latest_qtr          S
  pat_margin_latest_qtr             S
  sales_preceding_qtr               S
  op_profit_preceding_qtr           S
  pat_preceding_qtr                 S
  revenue_growth_qoq                S
  ebitda_growth_qoq                 S
  ebitda_margin_growth_qoq_bps      C
  pat_growth_qoq                    S
  pat_margin_growth_qoq_bps         C
  sales_growth_yoy_qtr              S
  profit_growth_yoy_qtr             S

RETURNS:
  return_down_from_52w_high         Y, S
  return_up_from_52w_low            Y, S
  return_1m                         Y
  return_3m                         Y
  return_6m                         Y
  return_12m                        Y

HISTORICAL CAGRs:
  revenue_cagr_hist_2yr             S
  ebitda_cagr_hist_2yr              S
  pat_cagr_hist_2yr                 S
  eps_cagr_hist_2yr                 S

FORWARD CAGRs:
  revenue_cagr_fwd_2yr              C
  ebitda_cagr_fwd_2yr               C
  pat_cagr_fwd_2yr                  C
  eps_cagr_fwd_2yr                  C

PER-FY ACTUALS (Rs Crs) - from S, T, G:
  revenue_fy2023 / revenue_fy23     S, T, G
  revenue_fy2024 / revenue_fy24     S, T, G
  revenue_fy2025 / revenue_fy25     S, T, G
  ebitda_fy2023 / ebitda_fy23       S, T, G
  ebitda_fy2024 / ebitda_fy24       S, T, G
  ebitda_fy2025 / ebitda_fy25       S, T, G
  pat_fy2023 / pat_fy23             S, T, G
  pat_fy2024 / pat_fy24             S, T, G
  pat_fy2025 / pat_fy25             S, T, G
  eps_fy2023 / eps_fy23 (implied)   S, T, G
  eps_fy2024 / eps_fy24             S, T, G
  eps_fy2025 / eps_fy25             S, T, G

PER-FY ESTIMATES (Rs Crs) - from T, G:
  revenue_fy2026e / revenue_fy26    T, G
  revenue_fy2027e / revenue_fy27    T, G
  revenue_fy2028e / revenue_fy28    T, G
  ebitda_fy2026e / ebitda_fy26      T, G
  ebitda_fy2027e / ebitda_fy27      T, G
  ebitda_fy2028e / ebitda_fy28      T, G
  pat_fy2026e / pat_fy26            T, G
  pat_fy2027e / pat_fy27            T, G
  pat_fy2028e / pat_fy28            T, G
  eps_fy2026e / eps_fy26            T, G
  eps_fy2027e / eps_fy27            T, G
  eps_fy2028e / eps_fy28            T, G

PER-FY MARGINS (calculated):
  ebitda_margin_fy2023..fy2028e     C
  pat_margin_fy2023..fy2028e        C

PER-FY VALUATIONS (calculated):
  pe_fy24..pe_fy28                  C
  pe_fy2026e..pe_fy2028e            C
  pb_fy24..pb_fy28                  C
  ev_ebitda_fy2026e..fy2028e        C
  ps_fy2026e..ps_fy2028e            C

TARGET PRICES:
  target_price_high                 T, G
  target_price_low                  T, G
  consensus_target_price            T, G
  consensus_upside_pct              C
  potential_upside_high             C
  potential_upside_low              C
  sotp_value                        NOT AUTOMATED (manual entry)

LAST ANNUAL RESULT DATE:
  last_annual_result_date           NOT AUTOMATED (manual or from Screener)

NOT FETCHED (as requested):
  chart_url_1m                      not automated
  chart_url_3m                      not automated
  chart_url_6m                      not automated
  chart_url_12m                     not automated
"""
