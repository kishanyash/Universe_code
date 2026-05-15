"""
=============================================================================
BATCH PROCESSOR - Core engine for processing stocks in batches
=============================================================================
Reads stock list from Supabase equity_universe (keyed by isin_code),
runs the appropriate scraper(s), and writes results back to Supabase.

Supports:
  - Per-source batch sizes and delays (rate-limiting)
  - Sequential processing for browser-based scrapers
  - Parallel processing for API-based scrapers (Yahoo Finance)
  - Progress logging and error tracking
=============================================================================
"""
import os
import time
import logging
import concurrent.futures
from datetime import datetime, timezone

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_TABLE, BATCH_CONFIG, SCHEDULES, VALID_COLUMNS
from scrapers import SCRAPER_MAP
from utils import chunks, clean_bse_code
from calculations import calculate_derived_fields

logger = logging.getLogger("all_fetching.batch")


def get_supabase_client():
    """Create and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all_companies(supabase, limit=None, offset=0, isin_list=None):
    """
    Fetch companies from equity_universe.
    
    Args:
        supabase: Supabase client
        limit: Optional max number of companies
        offset: Starting offset
        isin_list: Optional list of specific ISINs to process
    
    Returns:
        List of company dicts
    """
    query = supabase.table(SUPABASE_TABLE).select(
        "company_id, company_name, nse_code, bse_code, isin_code, quarterly_results_date"
    ).order("company_id")
    
    if isin_list:
        query = query.in_("isin_code", isin_list)
    
    if offset > 0:
        query = query.range(offset, offset + (limit or 10000))
    elif limit:
        query = query.limit(limit)
    
    response = query.execute()
    # Clean bse_code: strip .0 suffix that Supabase may return
    for company in response.data:
        if company.get("bse_code"):
            company["bse_code"] = clean_bse_code(company["bse_code"])
    return response.data


def update_company(supabase, isin_code, data):
    """
    Update a single company in equity_universe by ISIN.
    Filters out any fields not in VALID_COLUMNS before writing.
    """
    if not data:
        return False
    
    # Filter to only valid columns
    dropped = {k for k in data if k not in VALID_COLUMNS}
    if dropped:
        logger.debug(f"Dropping unknown columns for {isin_code}: {dropped}")
    filtered = {k: v for k, v in data.items() if k in VALID_COLUMNS}
    
    if not filtered:
        return False
    
    # Clean bse_code before writing to DB — prevent .0 suffix
    if "bse_code" in filtered and filtered["bse_code"]:
        filtered["bse_code"] = clean_bse_code(filtered["bse_code"])
    
    filtered["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    try:
        supabase.table(SUPABASE_TABLE).update(filtered).eq(
            "isin_code", isin_code
        ).execute()
        return True
    except Exception as e:
        logger.error(f"DB update failed for {isin_code}: {e}")
        return False


def run_scraper_for_company(scraper_func, company):
    """Run a single scraper for a single company, return results."""
    try:
        return scraper_func(company)
    except Exception as e:
        logger.error(f"Scraper error for {company.get('company_name', '?')}: {e}")
        return {}


def process_batch(supabase, companies, source_name):
    """
    Process a batch of companies with a specific scraper.
    
    Args:
        supabase: Supabase client
        companies: List of company dicts
        source_name: Name of the scraper to use
    
    Returns:
        dict with success/error counts
    """
    scraper_func = SCRAPER_MAP.get(source_name)
    if not scraper_func:
        logger.error(f"Unknown scraper: {source_name}")
        return {"success": 0, "errors": len(companies), "skipped": 0}
    
    config = BATCH_CONFIG.get(source_name, {"batch_size": 5, "delay": 2, "max_workers": 1})
    batch_size = config["batch_size"]
    delay = config["delay"]
    max_workers = config["max_workers"]
    
    success = 0
    errors = 0
    skipped = 0
    
    total = len(companies)
    batch_num = 0
    
    for batch in chunks(companies, batch_size):
        batch_num += 1
        logger.info(f"[{source_name}] Batch {batch_num} ({len(batch)} stocks)")
        
        results_to_write = []
        
        if max_workers > 1:
            # Parallel processing (for API-based scrapers like Yahoo Finance)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(run_scraper_for_company, scraper_func, c): c
                    for c in batch
                }
                for future in concurrent.futures.as_completed(future_map):
                    company = future_map[future]
                    isin = company.get("isin_code")
                    try:
                        data = future.result()
                        if data:
                            results_to_write.append((isin, data))
                        else:
                            skipped += 1
                    except Exception as e:
                        errors += 1
                        logger.error(f"Error for {company.get('company_name')}: {e}")
        else:
            # Sequential processing (for browser-based scrapers)
            for company in batch:
                isin = company.get("isin_code")
                name = company.get("company_name", "Unknown")
                
                data = run_scraper_for_company(scraper_func, company)
                if data:
                    results_to_write.append((isin, data))
                else:
                    skipped += 1
                
                # Rate limiting between individual scrapes
                time.sleep(delay)
        
        # Calculate derived fields and write batch results to Supabase
        for isin, data in results_to_write:
            data = calculate_derived_fields(data)
            if update_company(supabase, isin, data):
                success += 1
            else:
                errors += 1
        
        processed = success + errors + skipped
        logger.info(
            f"[{source_name}] Progress: {processed}/{total} "
            f"(OK: {success}, Err: {errors}, Skip: {skipped})"
        )
        
        # Delay between batches
        if batch_num * batch_size < total:
            time.sleep(delay * 2)
    
    return {"success": success, "errors": errors, "skipped": skipped}


def run_schedule(schedule_tier, isin_list=None, limit=None):
    """
    Run all scrapers for a given schedule tier.
    
    Args:
        schedule_tier: "daily", "weekly", "biweekly", or "quarterly"
        isin_list: Optional list of specific ISINs
        limit: Optional max companies to process
    
    Returns:
        dict with summary results per source
    """
    sources = SCHEDULES.get(schedule_tier)
    if not sources:
        return {"error": f"Unknown schedule tier: {schedule_tier}"}
    
    logger.info(f"{'='*60}")
    logger.info(f"RUNNING {schedule_tier.upper()} SYNC")
    logger.info(f"Sources: {', '.join(sources)}")
    logger.info(f"{'='*60}")
    
    supabase = get_supabase_client()
    companies = fetch_all_companies(supabase, limit=limit, isin_list=isin_list)
    
    if not companies:
        return {"error": "No companies found in equity_universe"}
    
    logger.info(f"Found {len(companies)} companies to process")
    
    start_time = time.time()
    results = {}
    
    for source in sources:
        logger.info(f"\n--- Starting {source} ---")
        source_start = time.time()
        
        result = process_batch(supabase, companies, source)
        result["duration_seconds"] = round(time.time() - source_start, 1)
        results[source] = result
        
        logger.info(
            f"--- {source} complete: {result['success']} OK, "
            f"{result['errors']} errors, {result['skipped']} skipped "
            f"({result['duration_seconds']}s) ---"
        )
    
    total_duration = round(time.time() - start_time, 1)
    
    summary = {
        "schedule": schedule_tier,
        "total_companies": len(companies),
        "total_duration_seconds": total_duration,
        "sources": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"{schedule_tier.upper()} SYNC COMPLETE ({total_duration}s)")
    logger.info(f"{'='*60}")
    
    return summary


def run_single_stock(isin_code, sources=None):
    """
    Run scrapers for a single stock by ISIN.
    
    Args:
        isin_code: ISIN of the stock
        sources: Optional list of source names. If None, runs all.
    
    Returns:
        dict with results
    """
    supabase = get_supabase_client()
    companies = fetch_all_companies(supabase, isin_list=[isin_code])
    
    if not companies:
        return {"error": f"ISIN {isin_code} not found in equity_universe"}
    
    company = companies[0]
    all_sources = sources or list(SCRAPER_MAP.keys())
    
    combined_data = {}
    results = {}
    
    for source in all_sources:
        scraper_func = SCRAPER_MAP.get(source)
        if not scraper_func:
            continue
        
        try:
            data = scraper_func(company)
            if data:
                combined_data.update(data)
                results[source] = {"status": "ok", "fields": len(data)}
            else:
                results[source] = {"status": "skipped", "fields": 0}
        except Exception as e:
            results[source] = {"status": "error", "message": str(e)}
    
    # Calculate derived fields and write combined results
    if combined_data:
        combined_data = calculate_derived_fields(combined_data)
        update_company(supabase, isin_code, combined_data)
    
    return {
        "isin": isin_code,
        "company": company.get("company_name"),
        "total_fields_updated": len(combined_data),
        "sources": results,
    }
