"""
Quick test: Fetch one company from Supabase, run Yahoo + Screener scrapers,
show results, and write back to Supabase.
"""
if __name__ != "__main__":
    import pytest
    pytest.skip("utility script; not a pytest test module", allow_module_level=True)

import os, sys, json, logging
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("test")

# Step 1: Connect to Supabase and fetch one company
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE

print(f"\n{'='*60}")
print("STEP 1: Connecting to Supabase...")
print(f"{'='*60}")

try:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    print(f"Connected to: {SUPABASE_URL[:50]}...")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)

# Fetch first company that has an NSE code (for Yahoo + Screener)
resp = sb.table(SUPABASE_TABLE).select(
    "company_name, nse_code, bse_code, isin_code"
).not_.is_("nse_code", "null").limit(1).execute()

if not resp.data:
    print("No companies found in equity_universe!")
    sys.exit(1)

company = resp.data[0]
print(f"\nTest company: {company['company_name']}")
print(f"  NSE: {company['nse_code']}")
print(f"  BSE: {company['bse_code']}")
print(f"  ISIN: {company['isin_code']}")

# Step 2: Run Yahoo Finance scraper
print(f"\n{'='*60}")
print("STEP 2: Running Yahoo Finance scraper...")
print(f"{'='*60}")

from scrapers.yahoo_finance import scrape_yahoo_finance
yf_data = scrape_yahoo_finance(company)
print(f"\nYahoo Finance returned {len(yf_data)} fields:")
for k, v in sorted(yf_data.items()):
    print(f"  {k:35s} = {v}")

# Step 3: Run Screener scraper
print(f"\n{'='*60}")
print("STEP 3: Running Screener.in scraper...")
print(f"{'='*60}")

from scrapers.screener import scrape_screener_daily
screener_data = scrape_screener_daily(company)
print(f"\nScreener returned {len(screener_data)} fields:")
for k, v in sorted(screener_data.items()):
    print(f"  {k:35s} = {v}")

# Step 4: Merge data and run calculations
print(f"\n{'='*60}")
print("STEP 4: Merging + calculating derived fields...")
print(f"{'='*60}")

combined = {}
combined.update(yf_data)
combined.update(screener_data)  # Screener overwrites Yahoo for overlapping fields

from calculations import calculate_derived_fields
final_data = calculate_derived_fields(combined)

print(f"\nFinal data has {len(final_data)} fields:")
for k, v in sorted(final_data.items()):
    print(f"  {k:35s} = {v}")

# Step 5: Write to Supabase
print(f"\n{'='*60}")
print("STEP 5: Writing to Supabase...")
print(f"{'='*60}")

from datetime import datetime, timezone
final_data["updated_at"] = datetime.now(timezone.utc).isoformat()
isin = company["isin_code"]

try:
    sb.table(SUPABASE_TABLE).update(final_data).eq("isin_code", isin).execute()
    print(f"\nSUCCESS! Updated {len(final_data)} fields for {company['company_name']} (ISIN: {isin})")
except Exception as e:
    print(f"\nFAILED to write: {e}")

print(f"\n{'='*60}")
print("TEST COMPLETE")
print(f"{'='*60}")
