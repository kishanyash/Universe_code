import config
from scrapers.yahoo_finance import scrape_yahoo_finance
from scrapers.screener import scrape_screener
from scrapers.trendlyne import scrape_trendlyne
from calculations import calculate_derived_fields

company = {
    "company_name": "Reliance Industries",
    "nse_code": "RELIANCE",
    "bse_code": "500325.0",
    "isin_code": "INE002A01018"
}

combined = {}
try: combined.update(scrape_yahoo_finance(company))
except Exception as e: print("YF Error:", e)

try: combined.update(scrape_screener(company))
except Exception as e: print("Screener Error:", e)

try: combined.update(scrape_trendlyne(company))
except Exception as e: print("Trendlyne Error:", e)

final = calculate_derived_fields(combined)

missing = sorted([c for c in config.VALID_COLUMNS if c not in final])
print(f"Total valid: {len(config.VALID_COLUMNS)}")
print(f"Total populated: {len([c for c in final if c in config.VALID_COLUMNS])}")
print(f"Missing ({len(missing)}):")
for m in missing:
    print(f"  - {m}")
