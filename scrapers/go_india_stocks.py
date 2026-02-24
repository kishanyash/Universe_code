"""
GO INDIA STOCKS SCRAPER
Supabase columns filled:
  target_price_high, target_price_low, consensus_target_price
  revenue/ebitda/pat/eps for FY23-FY25 (actuals) and FY26E-FY28E (estimates)
"""
import time
import logging
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import get_chrome_driver, to_float

logger = logging.getLogger("all_fetching.goindia")

# GoIndia column headers → Supabase column names
FY_MAP = {
    'FY2023': {'long': 'fy2023', 'short': 'fy23'},
    'FY2024': {'long': 'fy2024', 'short': 'fy24'},
    'FY2025': {'long': 'fy2025', 'short': 'fy25'},
    'FY2025E': {'long': 'fy2025', 'short': 'fy25'},
    'FY2026E': {'long': 'fy2026e', 'short': 'fy26'},
    'FY2027E': {'long': 'fy2027e', 'short': 'fy27'},
    'FY2028E': {'long': 'fy2028e', 'short': 'fy28'},
}


def scrape_go_india(company):
    """Scrape GoIndiaStocks for one company. Returns dict with Supabase column names."""
    nse_code = company.get("nse_code")
    bse_code = company.get("bse_code")
    name = company.get("company_name", "Unknown")

    accord_code = nse_code or (str(bse_code).replace('.0', '') if bse_code else None)
    if not accord_code:
        logger.warning(f"GoIndia: No code for {name}")
        return {}

    result = {}
    driver = get_chrome_driver()

    try:
        driver.get(f'https://www.goindiastocks.com/companyinfo/{accord_code}')

        # Wait for financials table
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "financialsTableID"))
            )
        except Exception:
            logger.warning(f"GoIndia: Table not found for {name}")
            driver.quit()
            return {}

        # === TARGET PRICES ===
        try:
            high = driver.find_element(By.XPATH,
                '//*[@id="basicID"]/div/div/div/div[2]/div/div[3]/fieldset/div[1]/div/div[2]/div/div[1]/div/span[2]')
            avg = driver.find_element(By.XPATH,
                '//*[@id="basicID"]/div/div/div/div[2]/div/div[3]/fieldset/div[1]/div/div[2]/div/div[2]/div/span[2]')
            low = driver.find_element(By.XPATH,
                '//*[@id="basicID"]/div/div/div/div[2]/div/div[3]/fieldset/div[1]/div/div[2]/div/div[3]/div/span[2]')
            result['target_price_high'] = to_float(high.text)
            result['consensus_target_price'] = to_float(avg.text)
            result['target_price_low'] = to_float(low.text)
        except Exception:
            pass

        # === CLICK "ACTUALS & FORWARD ESTIMATES" TAB ===
        try:
            button = driver.find_element(
                By.XPATH, '//*[@id="financialsID"]/div/div/div[1]/div[2]/span[3]'
            )
            button.click()
            time.sleep(4)
        except Exception:
            pass

        # === PARSE TABLE ===
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        fin_div = soup.find('div', {'id': 'financialsID'})
        if not fin_div:
            driver.quit()
            return result

        overflow = fin_div.find('div', {'class': 'overflow-x-auto rounded-md'})
        if not overflow:
            driver.quit()
            return result

        table = overflow.find('table', {'id': 'financialsTableID'})
        if not table:
            driver.quit()
            return result

        headers = [th.text.strip() for th in table.find_all('th')]
        rows = [
            [cell.text.strip() for cell in tr.find_all('td')]
            for tr in table.find_all('tr') if tr.find_all('td')
        ]

        if not rows:
            driver.quit()
            return result

        df_go = pd.DataFrame(rows, columns=headers)
        indicator_col = headers[0] if headers else 'Actuals & Forward Estimates'

        # === EXTRACT DATA FOR EACH FY ===
        for gi_col, fy_names in FY_MAP.items():
            if gi_col not in df_go.columns:
                continue

            fy_long = fy_names['long']
            fy_short = fy_names['short']

            # Revenue (row 0)
            try:
                v = to_float(df_go.loc[0, gi_col])
                if v is not None:
                    result[f'revenue_{fy_long}'] = v
                    result[f'revenue_{fy_short}'] = v
            except Exception:
                pass

            # EBITDA (or PPOP for banks)
            for indicator in ['EBITDA', 'PPOP']:
                try:
                    v = to_float(df_go.loc[df_go[indicator_col] == indicator, gi_col].values[0])
                    if v is not None:
                        result[f'ebitda_{fy_long}'] = v
                        result[f'ebitda_{fy_short}'] = v
                        break
                except (IndexError, KeyError):
                    continue

            # PAT
            try:
                v = to_float(df_go.loc[df_go[indicator_col] == 'PAT', gi_col].values[0])
                if v is not None:
                    result[f'pat_{fy_long}'] = v
                    result[f'pat_{fy_short}'] = v
            except (IndexError, KeyError):
                pass

            # EPS (Diluted EPS)
            try:
                v = to_float(df_go.loc[df_go[indicator_col] == 'Diluted EPS', gi_col].values[0])
                if v is not None:
                    result[f'eps_{fy_long}'] = v
            except (IndexError, KeyError):
                pass

        logger.info(f"GoIndia OK: {name} - {len(result)} fields")
        return result

    except Exception as e:
        logger.error(f"GoIndia ERROR: {name}: {e}")
        return {}
    finally:
        driver.quit()
        time.sleep(2)
