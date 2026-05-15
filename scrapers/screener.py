"""
=============================================================================
SCREENER.IN SCRAPER - Daily & Full modes
=============================================================================
Maps all extracted data to exact Supabase equity_universe column names.
All monetary values in Rs Crs.

FIELDS POPULATED:
  Market:       current_price, market_cap, high_52_week, low_52_week,
                book_value, face_value, dividend_yield, volume
  Valuation:    pe_ttm, ev_ebitda_ttm, ps_ttm, pe_avg_3yr, enterprise_value
  Profitability: roe, roce, roic, ebitda_margin_ttm, pat_margin_ttm,
                 opm_last_year, asset_turnover_ratio, working_capital_to_sales_ratio
  P&L TTM:      sales_ttm_screener, revenue_ttm, op_profit_ttm, ebitda_ttm,
                pat_ttm, pat_ttm_screener, eps_ttm, eps_ttm_actual
  Growth:       revenue_cagr_hist_2yr, ebitda_cagr_hist_2yr, pat_cagr_hist_2yr,
                eps_cagr_hist_2yr
  Quarterly:    sales_latest_qtr, op_profit_latest_qtr, pat_latest_qtr, etc.
  Balance Sheet: debt, net_worth, net_debt, cash_equivalents, num_equity_shares,
                 cwip, net_block, cwip_to_net_block_ratio
  Shareholding: promoter_holding_pct, unpledged_promoter_holding_pct
  Sectors:      broad_sector, sector, broad_industry, industry
  Per-FY (Rs Crs): revenue_fy2023..fy2025, ebitda_fy2023..fy2025,
                   pat_fy2023..fy2025, eps_fy2023..fy2025
=============================================================================
"""
import re
import requests
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
from config import SCREENER_HEADERS
from utils import parse_number, safe_round, find_key, calculate_cagr, clean_bse_code
import logging

logger = logging.getLogger("all_fetching.screener")


def fetch_screener_page(nse_code, bse_code):
    """Fetch and parse a Screener.in company page."""
    codes = []
    if nse_code:
        codes.append(nse_code.strip())
    bse = clean_bse_code(bse_code)
    if bse:
        codes.append(bse)

    for code in codes:
        for suffix in ['/consolidated/', '/']:
            url = f"https://www.screener.in/company/{code}{suffix}"
            try:
                resp = requests.get(url, headers=SCREENER_HEADERS, timeout=15)
                if resp.status_code == 200 and 'data-table' in resp.text:
                    return BeautifulSoup(resp.text, 'lxml')
            except requests.exceptions.RequestException:
                continue
    return None


def parse_table(soup, section_id):
    """Parse a data table from a Screener section."""
    section = soup.find('section', id=section_id)
    if not section:
        return {}, []
    table = section.find('table', class_='data-table') or section.find('table')
    if not table:
        return {}, []

    headers = []
    thead = table.find('thead')
    if thead:
        headers = [th.get_text(strip=True) for th in thead.find_all('th')]

    data = {}
    tbody = table.find('tbody')
    if tbody:
        for tr in tbody.find_all('tr'):
            tds = tr.find_all('td')
            if not tds:
                continue
            row_name = tds[0].get_text(strip=True)
            row_values = [parse_number(td.get_text(strip=True)) for td in tds[1:]]
            data[row_name] = row_values

    return data, headers[1:]


def _parse_quarter_header(header):
    """Convert a Screener quarter header like 'Dec 2025' to an ISO date."""
    try:
        qtr_date = datetime.strptime(header, "%b %Y").date()
    except (TypeError, ValueError):
        return None

    import calendar
    last_day = calendar.monthrange(qtr_date.year, qtr_date.month)[1]
    return f"{qtr_date.year}-{qtr_date.month:02d}-{last_day:02d}"


def extract_quarterly_results_date(soup):
    """Read only the latest quarter date from the Screener quarters table."""
    _, qtr_hdrs = parse_table(soup, 'quarters')
    if not qtr_hdrs:
        return None
    return _parse_quarter_header(qtr_hdrs[-1])


def _parse_db_date(value):
    """Parse a Supabase date/datetime value into a date."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def should_fetch_after_quarter_check(db_quarterly_date, scraped_quarterly_date, today=None):
    """
    Fetch full Screener data only when the stored quarter is stale or changed.

    Rule:
      current date > database quarterly_results_date + 100 days
      OR database quarterly_results_date != scraped quarterly_results_date
    """
    today = today or date.today()
    db_date = _parse_db_date(db_quarterly_date)
    scraped_date = _parse_db_date(scraped_quarterly_date)

    if not db_date or not scraped_date:
        return True

    return today > db_date + timedelta(days=100) or db_date != scraped_date


# FY mapping: Screener header → Supabase column suffix
# Screener shows "Mar 2021", "Mar 2022", etc.
FY_HEADER_MAP = {
    '2021': ('fy2021', None),       # No column in table for FY21
    '2022': ('fy2022', None),       # No column in table for FY22
    '2023': ('fy2023', 'fy23'),
    '2024': ('fy2024', 'fy24'),
    '2025': ('fy2025', 'fy25'),
}


def _find_fy_column_index(headers, year_str):
    """Find column index for a fiscal year in Screener headers."""
    for month in ['Mar', 'Jun', 'Sep', 'Dec']:
        target = f"{month} {year_str}"
        if target in headers:
            return headers.index(target)
    return None


def extract_all_metrics(soup):
    """Extract all available metrics from a Screener.in page."""
    result = {}

    # ==================================================================
    # TOP RATIOS BAR
    # ==================================================================
    top = soup.find(id='top-ratios')
    if top:
        for li in top.find_all('li'):
            name_el = li.find('span', class_='name')
            number_el = li.find('span', class_='number')
            if not name_el:
                continue
            name = name_el.get_text(strip=True)

            if 'High' in name and 'Low' in name:
                full_text = li.get_text().replace('\u20b9', '').replace(',', '')
                nums = re.findall(r'[\d]+\.?\d*', full_text)
                nums = [float(n) for n in nums if float(n) > 10]
                if len(nums) >= 2:
                    result['high_52_week'] = nums[0]
                    result['low_52_week'] = nums[1]
            elif number_el:
                val = parse_number(number_el.get_text(strip=True))
                mapping = {
                    'Market Cap': 'market_cap',
                    'Current Price': 'current_price',
                    'Stock P/E': 'pe_ttm',
                    'Book Value': 'book_value',
                    'Dividend Yield': 'dividend_yield',
                    'ROCE': 'roce',
                    'ROE': 'roe',
                    'Face Value': 'face_value',
                }
                db_col = mapping.get(name)
                if db_col and val is not None:
                    result[db_col] = val

    # -- Calculated from top ratios
    if result.get('current_price') and result.get('high_52_week') and result['high_52_week'] > 0:
        result['return_down_from_52w_high'] = safe_round(
            (result['current_price'] - result['high_52_week']) / result['high_52_week'] * 100
        )
    if result.get('current_price') and result.get('low_52_week') and result['low_52_week'] > 0:
        result['return_up_from_52w_low'] = safe_round(
            (result['current_price'] - result['low_52_week']) / result['low_52_week'] * 100
        )

    # ==================================================================
    # SECTOR
    # ==================================================================
    peers = soup.find('section', id='peers')
    if peers:
        sector_links = []
        for link in peers.find_all('a', href=True):
            if '/market/' in link.get('href', '') and link.get_text(strip=True):
                sector_links.append(link.get_text(strip=True))
        if len(sector_links) >= 1:
            result['broad_sector'] = sector_links[0]
        if len(sector_links) >= 2:
            result['sector'] = sector_links[1]
        if len(sector_links) >= 3:
            result['broad_industry'] = sector_links[2]
        if len(sector_links) >= 4:
            result['industry'] = sector_links[3]

    # ==================================================================
    # QUARTERLY RESULTS
    # ==================================================================
    qtr_data, qtr_hdrs = parse_table(soup, 'quarters')

    qtr_sales_key = find_key(qtr_data, ['Sales', 'Revenue', 'Net Sales', 'Income'])
    qtr_op_key = find_key(qtr_data, ['Operating Profit', 'EBITDA'])
    qtr_pat_key = find_key(qtr_data, ['Net Profit', 'Profit after tax', 'PAT'])
    qtr_opm_key = find_key(qtr_data, ['OPM %', 'OPM'])

    if qtr_sales_key and qtr_data[qtr_sales_key]:
        result['sales_latest_qtr'] = qtr_data[qtr_sales_key][-1]
    if qtr_op_key and qtr_data[qtr_op_key]:
        result['op_profit_latest_qtr'] = qtr_data[qtr_op_key][-1]
    if qtr_pat_key and qtr_data[qtr_pat_key]:
        result['pat_latest_qtr'] = qtr_data[qtr_pat_key][-1]
    if qtr_opm_key and qtr_data[qtr_opm_key]:
        result['ebitda_margin_latest_qtr'] = qtr_data[qtr_opm_key][-1]

    if result.get('sales_latest_qtr') and result.get('pat_latest_qtr') and result['sales_latest_qtr'] > 0:
        result['pat_margin_latest_qtr'] = safe_round(
            result['pat_latest_qtr'] / result['sales_latest_qtr'] * 100
        )

    # Preceding quarter
    if qtr_sales_key and len(qtr_data[qtr_sales_key]) >= 2:
        result['sales_preceding_qtr'] = qtr_data[qtr_sales_key][-2]
    if qtr_op_key and len(qtr_data[qtr_op_key]) >= 2:
        result['op_profit_preceding_qtr'] = qtr_data[qtr_op_key][-2]
    if qtr_pat_key and len(qtr_data[qtr_pat_key]) >= 2:
        result['pat_preceding_qtr'] = qtr_data[qtr_pat_key][-2]

    # QoQ Growth
    if result.get('sales_latest_qtr') and result.get('sales_preceding_qtr') and result['sales_preceding_qtr'] != 0:
        result['revenue_growth_qoq'] = safe_round(
            (result['sales_latest_qtr'] - result['sales_preceding_qtr']) / abs(result['sales_preceding_qtr']) * 100
        )
    if result.get('op_profit_latest_qtr') and result.get('op_profit_preceding_qtr') and result['op_profit_preceding_qtr'] != 0:
        result['ebitda_growth_qoq'] = safe_round(
            (result['op_profit_latest_qtr'] - result['op_profit_preceding_qtr']) / abs(result['op_profit_preceding_qtr']) * 100
        )
    if result.get('pat_latest_qtr') is not None and result.get('pat_preceding_qtr') is not None and result['pat_preceding_qtr'] != 0:
        result['pat_growth_qoq'] = safe_round(
            (result['pat_latest_qtr'] - result['pat_preceding_qtr']) / abs(result['pat_preceding_qtr']) * 100
        )

    # YoY Quarterly Growth
    if qtr_sales_key and len(qtr_data[qtr_sales_key]) >= 5:
        latest = qtr_data[qtr_sales_key][-1]
        yoy = qtr_data[qtr_sales_key][-5]
        if latest is not None and yoy is not None and yoy != 0:
            result['sales_growth_yoy_qtr'] = safe_round((latest - yoy) / abs(yoy) * 100)
    if qtr_pat_key and len(qtr_data[qtr_pat_key]) >= 5:
        latest = qtr_data[qtr_pat_key][-1]
        yoy = qtr_data[qtr_pat_key][-5]
        if latest is not None and yoy is not None and yoy != 0:
            result['profit_growth_yoy_qtr'] = safe_round((latest - yoy) / abs(yoy) * 100)

    qtr_result_date = extract_quarterly_results_date(soup)
    if qtr_result_date:
        result['quarterly_results_date'] = qtr_result_date

    # ==================================================================
    # PROFIT & LOSS (Annual + TTM) - all in Rs Crs
    # ==================================================================
    pl_data, pl_hdrs = parse_table(soup, 'profit-loss')

    pl_sales_key = find_key(pl_data, ['Sales', 'Revenue', 'Net Sales', 'Income'])
    pl_op_key = find_key(pl_data, ['Operating Profit', 'EBITDA'])
    pl_pat_key = find_key(pl_data, ['Net Profit', 'Profit after tax', 'PAT'])
    pl_opm_key = find_key(pl_data, ['OPM %', 'OPM'])
    pl_eps_key = find_key(pl_data, ['EPS in Rs', 'EPS in Rs.', 'EPS (Rs)', 'EPS'])

    # -- Sales / Revenue TTM
    if pl_sales_key and pl_data[pl_sales_key]:
        sales = pl_data[pl_sales_key]
        result['sales_ttm_screener'] = sales[-1]
        result['revenue_ttm'] = sales[-1]
        valid = [s for s in sales if s is not None and s > 0]
        if len(valid) >= 3:
            result['revenue_cagr_hist_2yr'] = calculate_cagr(valid[-3], valid[-1], 2)

    # -- Operating Profit / EBITDA TTM
    if pl_op_key and pl_data[pl_op_key]:
        op = pl_data[pl_op_key]
        result['op_profit_ttm'] = op[-1]
        result['ebitda_ttm'] = op[-1]
        if result.get('revenue_ttm') and op[-1] is not None and result['revenue_ttm'] > 0:
            result['ebitda_margin_ttm'] = safe_round(op[-1] / result['revenue_ttm'] * 100)
        valid = [o for o in op if o is not None and o > 0]
        if len(valid) >= 3:
            result['ebitda_cagr_hist_2yr'] = calculate_cagr(valid[-3], valid[-1], 2)

    # -- OPM Last Year
    if pl_opm_key and pl_data[pl_opm_key] and len(pl_data[pl_opm_key]) >= 2:
        result['opm_last_year'] = pl_data[pl_opm_key][-2]

    # -- PAT TTM
    if pl_pat_key and pl_data[pl_pat_key]:
        pat = pl_data[pl_pat_key]
        result['pat_ttm_screener'] = pat[-1]
        result['pat_ttm'] = pat[-1]
        if result.get('revenue_ttm') and pat[-1] is not None and result['revenue_ttm'] > 0:
            result['pat_margin_ttm'] = safe_round(pat[-1] / result['revenue_ttm'] * 100)
        valid = [p for p in pat if p is not None and p > 0]
        if len(valid) >= 3:
            result['pat_cagr_hist_2yr'] = calculate_cagr(valid[-3], valid[-1], 2)

    # -- EPS TTM
    if pl_eps_key and pl_data[pl_eps_key]:
        eps = pl_data[pl_eps_key]
        result['eps_ttm'] = eps[-1]
        result['eps_ttm_actual'] = eps[-1]
        valid = [e for e in eps if e is not None and e > 0]
        if len(valid) >= 3:
            result['eps_cagr_hist_2yr'] = calculate_cagr(valid[-3], valid[-1], 2)

    # ==================================================================
    # PER-FISCAL-YEAR DATA (FY23, FY24, FY25)
    # Maps to: revenue_fy2023/revenue_fy23, ebitda_fy2023/ebitda_fy23,
    #          pat_fy2023/pat_fy23, eps_fy2023/eps_fy23
    # ==================================================================
    for year_str, (fy_long, fy_short) in FY_HEADER_MAP.items():
        col_idx = _find_fy_column_index(pl_hdrs, year_str)
        if col_idx is None:
            continue

        # Revenue
        if pl_sales_key and pl_data[pl_sales_key] and col_idx < len(pl_data[pl_sales_key]):
            val = pl_data[pl_sales_key][col_idx]
            if val is not None:
                result[f'revenue_{fy_long}'] = val
                if fy_short:
                    result[f'revenue_{fy_short}'] = val

        # EBITDA
        if pl_op_key and pl_data[pl_op_key] and col_idx < len(pl_data[pl_op_key]):
            val = pl_data[pl_op_key][col_idx]
            if val is not None:
                result[f'ebitda_{fy_long}'] = val
                if fy_short:
                    result[f'ebitda_{fy_short}'] = val

        # PAT
        if pl_pat_key and pl_data[pl_pat_key] and col_idx < len(pl_data[pl_pat_key]):
            val = pl_data[pl_pat_key][col_idx]
            if val is not None:
                result[f'pat_{fy_long}'] = val
                if fy_short:
                    result[f'pat_{fy_short}'] = val

        # EPS
        if pl_eps_key and pl_data[pl_eps_key] and col_idx < len(pl_data[pl_eps_key]):
            val = pl_data[pl_eps_key][col_idx]
            if val is not None:
                result[f'eps_{fy_long}'] = val
                if fy_short:
                    result[f'eps_{fy_short}'] = val

    # -- P/S TTM
    if result.get('market_cap') and result.get('revenue_ttm') and result['revenue_ttm'] > 0:
        result['ps_ttm'] = safe_round(result['market_cap'] / result['revenue_ttm'])

    # ==================================================================
    # BALANCE SHEET - all in Rs Crs
    # ==================================================================
    bs_data, bs_hdrs = parse_table(soup, 'balance-sheet')

    borrow_key = find_key(bs_data, ['Borrowings', 'Total Debt'])
    if borrow_key and bs_data[borrow_key]:
        result['debt'] = bs_data[borrow_key][-1]

    eq_key = find_key(bs_data, ['Equity Capital'])
    res_key = find_key(bs_data, ['Reserves'])
    if eq_key and res_key and bs_data.get(eq_key) and bs_data.get(res_key):
        eq = bs_data[eq_key][-1]
        res = bs_data[res_key][-1]
        if eq is not None and res is not None:
            result['net_worth'] = safe_round(eq + res)

    if eq_key and bs_data.get(eq_key) and result.get('face_value') and result['face_value'] > 0:
        eq_cap = bs_data[eq_key][-1]
        if eq_cap is not None:
            result['num_equity_shares'] = safe_round(eq_cap / result['face_value'])

    cwip_key = find_key(bs_data, ['CWIP'])
    if cwip_key and bs_data.get(cwip_key):
        result['cwip'] = bs_data[cwip_key][-1]

    fixed_key = find_key(bs_data, ['Fixed Assets', 'Net Block'])
    if fixed_key and bs_data.get(fixed_key):
        result['net_block'] = bs_data[fixed_key][-1]

    if result.get('cwip') and result.get('net_block') and result['net_block'] > 0:
        result['cwip_to_net_block_ratio'] = safe_round(result['cwip'] / result['net_block'] * 100)

    inv_key = find_key(bs_data, ['Investments'])
    investments = bs_data[inv_key][-1] if inv_key and bs_data.get(inv_key) else None

    other_assets_key = find_key(bs_data, ['Other Assets'])
    other_assets = bs_data[other_assets_key][-1] if other_assets_key and bs_data.get(other_assets_key) else None

    if investments is not None and other_assets is not None:
        result['cash_equivalents'] = safe_round(investments + other_assets * 0.3)
    elif investments is not None:
        result['cash_equivalents'] = safe_round(investments)
    elif other_assets is not None:
        result['cash_equivalents'] = safe_round(other_assets * 0.4)

    debt_val = result.get('debt') or 0
    cash_val = result.get('cash_equivalents') or 0
    if result.get('debt') is not None:
        result['net_debt'] = safe_round(debt_val - cash_val)

    if result.get('market_cap') and result.get('net_debt') is not None:
        result['enterprise_value'] = safe_round(result['market_cap'] + result['net_debt'])

    if result.get('enterprise_value') and result.get('op_profit_ttm') and result['op_profit_ttm'] > 0:
        result['ev_ebitda_ttm'] = safe_round(result['enterprise_value'] / result['op_profit_ttm'])

    # ==================================================================
    # RATIOS
    # ==================================================================
    ratios_data, _ = parse_table(soup, 'ratios')

    wc_key = find_key(ratios_data, ['Working Capital Days'])
    if wc_key and ratios_data[wc_key]:
        wc_days = ratios_data[wc_key][-1]
        if wc_days is not None:
            result['working_capital_to_sales_ratio'] = safe_round(wc_days / 365, 4)

    roce_key = find_key(ratios_data, ['ROCE %', 'ROCE'])
    if roce_key and ratios_data[roce_key]:
        val = ratios_data[roce_key][-1]
        if val is not None:
            result['roce'] = val

    roe_key = find_key(ratios_data, ['ROE %', 'ROE', 'Return on Equity'])
    if roe_key and ratios_data[roe_key]:
        val = ratios_data[roe_key][-1]
        if val is not None:
            result['roe'] = val

    at_key = find_key(ratios_data, ['Asset Turnover', 'Asset Turnover Ratio', 'Fixed Asset Turnover', 'Total Asset Turnover'])
    if at_key and ratios_data[at_key]:
        val = ratios_data[at_key][-1]
        if val is not None:
            result['asset_turnover_ratio'] = val

    roic_key = find_key(ratios_data, ['ROIC', 'ROIC %', 'Return on Invested Capital'])
    if roic_key and ratios_data[roic_key]:
        val = ratios_data[roic_key][-1]
        if val is not None:
            result['roic'] = val
    elif result.get('op_profit_ttm') and result.get('net_worth') and result.get('debt'):
        nopat = result['op_profit_ttm'] * 0.75
        invested = (result['net_worth'] or 0) + (result.get('debt') or 0)
        if invested > 0:
            result['roic'] = safe_round(nopat / invested * 100)

    # ==================================================================
    # SHAREHOLDING PATTERN
    # ==================================================================
    sh_data, _ = parse_table(soup, 'shareholding')

    promoter_key = find_key(sh_data, ['Promoters', 'Promoter & Promoter Group',
                                       'Promoters+', 'Promoter'])
    if promoter_key and sh_data[promoter_key]:
        vals = [v for v in sh_data[promoter_key] if v is not None]
        if vals:
            result['promoter_holding_pct'] = vals[-1]

    pledge_key = find_key(sh_data, ['Pledged', 'Pledged %', 'Shares Pledged',
                                     'Pledged percentage'])
    if pledge_key and sh_data[pledge_key]:
        vals = [v for v in sh_data[pledge_key] if v is not None]
        if vals and result.get('promoter_holding_pct'):
            pledged_pct = vals[-1]
            result['unpledged_promoter_holding_pct'] = safe_round(
                result['promoter_holding_pct'] * (1 - pledged_pct / 100)
            )
    elif result.get('promoter_holding_pct'):
        result['unpledged_promoter_holding_pct'] = result['promoter_holding_pct']

    # ==================================================================
    # P/E AVG 3yr, 5yr, HIGH, LOW
    # ==================================================================
    if pl_eps_key and pl_data.get(pl_eps_key) and result.get('current_price'):
        eps_list = pl_data[pl_eps_key]

        # P/E Avg 3yr
        if len(eps_list) >= 4:
            fy_eps_3 = eps_list[-4:-1]
            valid_eps = [e for e in fy_eps_3 if e is not None and e > 0]
            if valid_eps:
                avg_eps = sum(valid_eps) / len(valid_eps)
                if avg_eps > 0:
                    result['pe_avg_3yr'] = safe_round(result['current_price'] / avg_eps)

        # P/E Avg 5yr
        if len(eps_list) >= 6:
            fy_eps_5 = eps_list[-6:-1]
            valid_eps = [e for e in fy_eps_5 if e is not None and e > 0]
            if valid_eps:
                avg_eps = sum(valid_eps) / len(valid_eps)
                if avg_eps > 0:
                    result['pe_avg_5yr'] = safe_round(result['current_price'] / avg_eps)

        # P/E High & Low (from historical EPS)
        valid_eps = [e for e in eps_list[:-1] if e is not None and e > 0]
        if valid_eps and result.get('current_price'):
            pe_values = [result['current_price'] / e for e in valid_eps]
            result['pe_high_hist'] = safe_round(max(pe_values))
            result['pe_low_hist'] = safe_round(min(pe_values))

    # Remove None values
    return {k: v for k, v in result.items() if v is not None}


def scrape_screener_daily(company):
    """Daily scrape: all metrics from Screener.in"""
    name = company.get("company_name", "Unknown")
    nse_code = company.get("nse_code")
    bse_code = company.get("bse_code")
    db_quarterly_date = company.get("quarterly_results_date")

    try:
        soup = fetch_screener_page(nse_code, bse_code)
        if not soup:
            logger.warning(f"Screener: {name} - page not found")
            return {}

        scraped_quarterly_date = extract_quarterly_results_date(soup)
        if not should_fetch_after_quarter_check(db_quarterly_date, scraped_quarterly_date):
            logger.info(
                f"Screener SKIP: {name} - quarterly_results_date unchanged "
                f"({scraped_quarterly_date}) and DB date is within 100 days"
            )
            return {}

        metrics = extract_all_metrics(soup)
        logger.info(f"Screener OK: {name} - {len(metrics)} fields")
        return metrics

    except Exception as e:
        logger.error(f"Screener ERROR: {name}: {e}")
        return {}


def scrape_screener_full(company):
    """Full weekly scrape: same as daily + all per-FY consensus data."""
    return scrape_screener_daily(company)
