"""
TRENDLYNE SCRAPER
Supabase columns filled:
  target_price_high, target_price_low, consensus_target_price
  revenue/ebitda/pat/eps for FY23-FY25 (actuals) and FY26E-FY27E (estimates)
"""
import time
import random
import logging
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from utils import get_chrome_driver, to_float
from config import TRENDLYNE_USERNAME, TRENDLYNE_PASSWORD

logger = logging.getLogger("all_fetching.trendlyne")

ACTUAL_FY_MAP = {
    "23": {"long": "fy2023", "short": "fy23"},
    "24": {"long": "fy2024", "short": "fy24"},
    "25": {"long": "fy2025", "short": "fy25"},
}

ESTIMATE_FY_MAP = {
    "FY26": {"long": "fy2026e", "short": "fy26"},
    "FY27": {"long": "fy2027e", "short": "fy27"},
}


def _find_fy_column(headers, fy_suffix):
    """Find column header matching a FY suffix like '23'."""
    for month in ["Mar", "Jun", "Dec"]:
        col = f"{month} '{fy_suffix}"
        if col in headers:
            return col
    return None


def _find_row(df, indicator_col, keyword):
    """Find row where indicator column CONTAINS keyword (handles hidden codes)."""
    mask = df[indicator_col].str.contains(keyword, case=False, na=False)
    rows = df.loc[mask]
    return rows.iloc[0] if len(rows) > 0 else None


def scrape_trendlyne(company):
    """Scrape Trendlyne for one company. Returns dict with Supabase column names."""
    nse_code = company.get("nse_code")
    bse_code = company.get("bse_code")
    name = company.get("company_name", "Unknown")
    result = {}

    if not nse_code and not bse_code:
        logger.warning(f"Trendlyne: No code for {name}")
        return {}

    driver = get_chrome_driver()

    try:
        # === LOGIN ===
        driver.get("https://trendlyne.com/accounts/login/")
        time.sleep(3)
        driver.find_element(By.NAME, 'login').send_keys(TRENDLYNE_USERNAME)
        driver.find_element(By.NAME, 'password').send_keys(TRENDLYNE_PASSWORD)
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()
        time.sleep(random.uniform(3, 5))

        # === NAVIGATE TO STOCK PAGE ===
        if nse_code:
            driver.get(f"https://trendlyne.com/equity/{nse_code.strip()}/stock-page")
        else:
            driver.get("https://trendlyne.com/features")
            time.sleep(1)
            driver.find_element(By.NAME, 'search').send_keys(str(bse_code).replace('.0', ''))
            time.sleep(1)
            driver.find_element(By.CLASS_NAME, 'ui-menu-item').click()
        time.sleep(random.uniform(2, 3))

        # === TARGET PRICE (from forecaster block) ===
        try:
            forecaster = driver.find_element(By.CLASS_NAME, 'forecaster-block')
            avg_el = forecaster.find_element(By.CLASS_NAME, 'bottom-right').find_element(By.CLASS_NAME, 'right-number')
            if avg_el.text and avg_el.text[0].isdigit():
                result['consensus_target_price'] = to_float(avg_el.text)
        except Exception:
            pass

        # === NAVIGATE TO FINANCIALS ===
        try:
            navbar = driver.find_elements(By.XPATH, '/html/body/main/nav/ul/li')
            for item in navbar:
                if 'Financials' in item.text:
                    ActionChains(driver).move_to_element(item).click(item).perform()
                    break
            time.sleep(2)

            # Switch to consolidated
            try:
                fund = driver.find_element(By.ID, 'fundamental_tables')
                chk = fund.find_element(By.CSS_SELECTOR, '.tl__checkmark--1HU9T')
                ActionChains(driver).move_to_element(chk).click(chk).perform()
                driver.refresh()
                time.sleep(3)
            except Exception:
                pass
        except Exception:
            pass

        # === PARSE ANNUAL RESULTS TABLE ===
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        fin_div = soup.find('div', class_=lambda x: x and 'annual-results' in x)

        if fin_div:
            fin_table = fin_div.find('table')
            if fin_table:
                fin_headers = [th.text.strip() for th in fin_table.find_all('th')]
                fin_rows = []
                for tr in fin_table.find_all('tr'):
                    if tr.find_all('td'):
                        row = []
                        for idx, cell in enumerate(tr.find_all('td')):
                            div = cell.find('div', class_='indicator-value-container' if idx == 0 else 'value')
                            row.append(div.text.strip() if div else cell.text.strip())
                        if row:
                            fin_rows.append(row)

                if fin_rows and fin_headers:
                    df_fin = pd.DataFrame(fin_rows, columns=fin_headers)
                    ind_col = fin_headers[0]  # 'Indicator'

                    for fy_suffix, fy_names in ACTUAL_FY_MAP.items():
                        col = _find_fy_column(fin_headers, fy_suffix)
                        if not col:
                            continue

                        # Revenue - match "Operating Rev" (handles hidden codes)
                        row = _find_row(df_fin, ind_col, 'Operating Rev')
                        if row is not None:
                            v = to_float(row[col])
                            if v is not None:
                                result[f'revenue_{fy_names["long"]}'] = v
                                result[f'revenue_{fy_names["short"]}'] = v

                        # EBITDA - match "EBITDA" (indicator: EBIDT_AEBITDA Ann.)
                        row = _find_row(df_fin, ind_col, 'EBITDA')
                        if row is not None:
                            v = to_float(row[col])
                            if v is not None:
                                result[f'ebitda_{fy_names["long"]}'] = v
                                result[f'ebitda_{fy_names["short"]}'] = v

                        # PAT - match "Net Profit"
                        row = _find_row(df_fin, ind_col, 'Net Profit')
                        if row is not None:
                            v = to_float(row[col])
                            if v is not None:
                                result[f'pat_{fy_names["long"]}'] = v
                                result[f'pat_{fy_names["short"]}'] = v

                        # EPS - match "EPS"
                        row = _find_row(df_fin, ind_col, 'EPS')
                        if row is not None:
                            v = to_float(row[col])
                            if v is not None:
                                result[f'eps_{fy_names["long"]}'] = v

        # === CONSENSUS ESTIMATES PAGE ===
        try:
            # Navigate directly to consensus estimates URL
            current_url = driver.current_url
            # Extract stock ID from URL like /fundamentals/financials/1127/RELIANCE/...
            parts = current_url.split('/')
            stock_id = None
            stock_slug = None
            for i, p in enumerate(parts):
                if p.isdigit() and i + 1 < len(parts):
                    stock_id = p
                    stock_slug = '/'.join(parts[i:])
                    break
            if stock_id:
                consensus_url = f"https://trendlyne.com/equity/consensus-estimates/{stock_slug}"
                driver.get(consensus_url)
                time.sleep(3)
            else:
                # Fallback: click forecaster button
                btn = driver.find_element(By.CLASS_NAME, "sprite-stock.sprite-forecaster-logo")
                ActionChains(driver).move_to_element(btn).click(btn).perform()
                time.sleep(3)

            # Click "Detailed" tab - try multiple approaches
            tabs = driver.find_elements(By.CSS_SELECTOR, 'ul.nav li a, .nav-tabs li a, [role="tab"]')
            for tab in tabs:
                if 'detail' in tab.text.lower():
                    ActionChains(driver).move_to_element(tab).click(tab).perform()
                    time.sleep(2)
                    break

            soup2 = BeautifulSoup(driver.page_source, 'html.parser')

            # Target prices (high / low)
            try:
                high_div = soup2.find('div', class_=lambda x: x and 'high-estimate' in x)
                if high_div:
                    price_el = high_div.find('div', class_=lambda x: x and 'price' in x)
                    if price_el:
                        result['target_price_high'] = to_float(price_el.text)
            except Exception:
                pass
            try:
                low_div = soup2.find('div', class_=lambda x: x and 'low-estimate' in x)
                if low_div:
                    price_el = low_div.find('div', class_=lambda x: x and 'price' in x)
                    if price_el:
                        result['target_price_low'] = to_float(low_div.find_all('div', class_=lambda x: x and 'price' in x)[-1].text)
            except Exception:
                pass

            # Estimates table
            est_table = soup2.find('table')
            if est_table:
                est_headers = [th.text.strip() for th in est_table.find_all('th')]
                est_rows = []
                for tr in est_table.find_all('tr'):
                    tds = tr.find_all('td')
                    if tds:
                        row = []
                        for td in tds:
                            val_div = td.find('div', class_='value')
                            row.append(val_div.text.strip() if val_div else td.text.strip())
                        if row:
                            est_rows.append(row)

                if est_rows and est_headers:
                    df_est = pd.DataFrame(est_rows, columns=est_headers)
                    est_ind = est_headers[0]

                    # Calculate EBITDA = EBIT + Depreciation for estimates
                    for fy_col in ['FY26', 'FY27']:
                        if fy_col not in df_est.columns:
                            continue
                        try:
                            ebit_row = _find_row(df_est, est_ind, 'EBIT Avg')
                            dep_row = _find_row(df_est, est_ind, 'Depreciation.*Avg')
                            if ebit_row is not None and dep_row is not None:
                                ebit = to_float(ebit_row[fy_col])
                                dep = to_float(dep_row[fy_col])
                                if ebit is not None and dep is not None:
                                    ebitda_val = round(ebit + dep, 2)
                                    new_row = pd.Series(['EBITDA_calc'] + [''] * (len(est_headers) - 1), index=est_headers)
                                    new_row[fy_col] = str(ebitda_val)
                                    df_est = pd.concat([df_est, pd.DataFrame([new_row])], ignore_index=True)
                        except Exception:
                            pass

                    # Extract FY26, FY27 estimates
                    for fy_col, fy_names in ESTIMATE_FY_MAP.items():
                        if fy_col not in df_est.columns:
                            continue

                        # Revenue
                        row = _find_row(df_est, est_ind, 'Operating Revenue.*Avg')
                        if row is not None:
                            v = to_float(row[fy_col])
                            if v is not None:
                                result[f'revenue_{fy_names["long"]}'] = v
                                result[f'revenue_{fy_names["short"]}'] = v

                        # EBITDA (calculated)
                        row = _find_row(df_est, est_ind, 'EBITDA_calc')
                        if row is not None:
                            v = to_float(row[fy_col])
                            if v is not None:
                                result[f'ebitda_{fy_names["long"]}'] = v
                                result[f'ebitda_{fy_names["short"]}'] = v

                        # PAT
                        row = _find_row(df_est, est_ind, 'Net income.*Avg')
                        if row is not None:
                            v = to_float(row[fy_col])
                            if v is not None:
                                result[f'pat_{fy_names["long"]}'] = v
                                result[f'pat_{fy_names["short"]}'] = v

                        # EPS
                        row = _find_row(df_est, est_ind, 'EPS.*Avg')
                        if row is not None:
                            v = to_float(row[fy_col])
                            if v is not None:
                                result[f'eps_{fy_names["long"]}'] = v

        except Exception as e:
            logger.debug(f"Trendlyne: Forecaster error for {name}: {e}")

        logger.info(f"Trendlyne OK: {name} - {len(result)} fields")
        return result

    except Exception as e:
        logger.error(f"Trendlyne ERROR: {name}: {e}")
        return {}
    finally:
        driver.quit()
        time.sleep(2)
