"""
Full test with a specific non-banking stock + detailed debug logging.
"""
import sys
import json
import traceback
import logging
from dotenv import load_dotenv
load_dotenv()

LOG_FILE = "full_test_log.txt"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)

with open(LOG_FILE, "w", encoding="utf-8") as f:
    def log(msg):
        f.write(msg + "\n")
        f.flush()
        print(msg)

    try:
        log("=" * 60)
        log("FULL TEST: ALL 4 SCRAPERS (non-banking stock)")
        log("=" * 60)

        log("\n1. Connecting to Supabase...")
        import config
        from supabase import create_client
        sb = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        log("   Connected OK")

        log("\n2. Fetching a non-banking stock...")
        # Try to find a well-known non-banking stock
        for code in ['RELIANCE', 'TCS', 'INFY', 'HDFCLIFE', 'TITAN']:
            resp = sb.table(config.SUPABASE_TABLE).select(
                "company_name, nse_code, bse_code, isin_code"
            ).eq("nse_code", code).limit(1).execute()
            if resp.data:
                break

        if not resp.data:
            # Fallback: any non-bank stock
            resp = sb.table(config.SUPABASE_TABLE).select(
                "company_name, nse_code, bse_code, isin_code"
            ).not_.is_("nse_code", "null").limit(5).execute()
            # Pick one that's not a bank
            for c in resp.data:
                if 'bank' not in c.get('company_name', '').lower():
                    resp.data = [c]
                    break

        company = resp.data[0]
        log(f"   Company: {company['company_name']}")
        log(f"   NSE: {company['nse_code']} | BSE: {company['bse_code']} | ISIN: {company['isin_code']}")

        combined = {}

        # -- SCRAPER 1: Yahoo Finance --
        log("\n3. Yahoo Finance...")
        from scrapers.yahoo_finance import scrape_yahoo_finance
        yf_data = scrape_yahoo_finance(company)
        log(f"   Yahoo: {len(yf_data)} fields")
        combined.update(yf_data)

        # -- SCRAPER 2: Screener --
        log("\n4. Screener.in...")
        from scrapers.screener import scrape_screener_daily
        sc_data = scrape_screener_daily(company)
        log(f"   Screener: {len(sc_data)} fields")
        combined.update(sc_data)

        # -- SCRAPER 3: Trendlyne (uses scrapers/trendlyne.py module) --
        log("\n5. Trendlyne...")
        try:
            from scrapers.trendlyne import scrape_trendlyne
            tl_result = scrape_trendlyne(company)
            log(f"   Trendlyne: {len(tl_result)} fields")
            for k, v in sorted(tl_result.items()):
                log(f"     {k:35s} = {v}")
            combined.update(tl_result)
        except Exception as e:
            log(f"   Trendlyne ERROR: {e}")
            log(traceback.format_exc())

        # -- SCRAPER 4: GoIndiaStocks (with debug) --
        log("\n6. GoIndiaStocks (debug mode)...")
        try:
            from scrapers.go_india_stocks import scrape_go_india
            gi_data = scrape_go_india(company)
            log(f"   GoIndia: {len(gi_data)} fields")
            for k, v in sorted(gi_data.items()):
                log(f"     {k:35s} = {v}")
            combined.update(gi_data)
        except Exception as e:
            log(f"   GoIndia ERROR: {e}")
            log(traceback.format_exc())

        # -- CALCULATIONS --
        log("\n7. Calculations...")
        from calculations import calculate_derived_fields
        final = calculate_derived_fields(combined)
        log(f"   Fields after calc: {len(final)}")

        # -- FILTER --
        log("\n8. Filtering...")
        dropped = sorted(k for k in final if k not in config.VALID_COLUMNS)
        if dropped:
            log(f"   Dropped: {dropped}")
        filtered = {k: v for k, v in final.items() if k in config.VALID_COLUMNS}
        log(f"   Valid: {len(filtered)}")

        # -- WRITE --
        log("\n9. Writing to Supabase...")
        from datetime import datetime, timezone
        filtered["updated_at"] = datetime.now(timezone.utc).isoformat()
        isin = company["isin_code"]
        sb.table(config.SUPABASE_TABLE).update(filtered).eq("isin_code", isin).execute()
        log(f"\n   SUCCESS! {len(filtered)} fields for {company['company_name']}")

        log("\n" + "=" * 60)
        log("DONE!")
        log("=" * 60)

    except Exception as e:
        log(f"\n!!! ERROR !!!\n{traceback.format_exc()}")

print(f"\nLog: {LOG_FILE}")
