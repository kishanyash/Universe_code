"""
=============================================================================
FLASK API - Webhook endpoints for n8n
=============================================================================
n8n calls these endpoints on schedule (daily, weekly, biweekly, quarterly).
Each endpoint triggers the batch processor with the appropriate scrapers.

Endpoints:
  POST /webhook/daily      → Yahoo Finance + Screener (price, returns, ratios)
  POST /webhook/weekly     → Screener full (financials, bal sheet, ratios)
  POST /webhook/biweekly   → Trendlyne + GoIndiaStocks (estimates, targets)
  POST /webhook/quarterly  → All sources (full refresh)
  POST /webhook/single     → Single stock by ISIN (on demand)
  GET  /health             → Health check
=============================================================================
"""
import os
import sys
import hmac
import logging
import threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from config import API_PORT, API_SECRET
from batch_processor import run_schedule, run_single_stock

# ── Logging Setup ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("all_fetching.log", mode="a"),
    ],
)
logger = logging.getLogger("all_fetching")

app = Flask(__name__)

# Track running jobs
_running_jobs = {}


def verify_secret(req):
    """Verify API secret from request header."""
    if not API_SECRET or API_SECRET == "change-me-in-production":
        logger.error("API_SECRET is not securely configured. Denying authenticated request.")
        return False

    secret = req.headers.get("X-API-Secret")
    if not secret:
        return False

    if not hmac.compare_digest(secret, API_SECRET):
        return False

    return True


def run_async_job(job_id, schedule_tier, isin_list=None, limit=None):
    """Run a sync job in a background thread."""
    try:
        _running_jobs[job_id] = {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "schedule": schedule_tier,
        }
        result = run_schedule(schedule_tier, isin_list=isin_list, limit=limit)
        _running_jobs[job_id] = {
            "status": "completed",
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        _running_jobs[job_id] = {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }


# ═════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════════════

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "all_fetching",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "running_jobs": {
            k: v["status"] for k, v in _running_jobs.items()
        },
    })


@app.route("/webhook/<schedule_tier>", methods=["POST"])
def webhook(schedule_tier):
    """
    Trigger a batch sync for the given schedule tier.
    
    Body (optional JSON):
    {
        "isin_list": ["INE002A01018", "INE009A01021"],  // specific stocks
        "limit": 50,          // max stocks to process
        "async": true         // run in background (default: true)
    }
    """
    if not verify_secret(request):
        return jsonify({"error": "Unauthorized"}), 401
    
    valid_tiers = ["daily", "weekly", "biweekly", "quarterly"]
    if schedule_tier not in valid_tiers:
        return jsonify({
            "error": f"Invalid schedule tier: {schedule_tier}",
            "valid_tiers": valid_tiers,
        }), 400
    
    # Parse request body
    body = request.get_json(silent=True) or {}
    isin_list = body.get("isin_list")
    limit = body.get("limit")
    run_async = body.get("async", True)
    
    job_id = f"{schedule_tier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if run_async:
        # Run in background thread so n8n doesn't timeout
        thread = threading.Thread(
            target=run_async_job,
            args=(job_id, schedule_tier, isin_list, limit),
            daemon=True,
        )
        thread.start()
        
        return jsonify({
            "status": "started",
            "job_id": job_id,
            "schedule": schedule_tier,
            "message": f"Background job started. Check /job/{job_id} for status.",
        }), 202
    else:
        # Synchronous for small batches / testing
        try:
            result = run_schedule(schedule_tier, isin_list=isin_list, limit=limit)
            return jsonify({"status": "completed", "result": result})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/webhook/single", methods=["POST"])
def webhook_single():
    """
    Trigger scraping for a single stock by ISIN.
    
    Body (JSON):
    {
        "isin": "INE002A01018",
        "sources": ["yahoo_finance", "screener_daily"]  // optional
    }
    """
    if not verify_secret(request):
        return jsonify({"error": "Unauthorized"}), 401
    
    body = request.get_json(silent=True) or {}
    isin = body.get("isin")
    
    if not isin:
        return jsonify({"error": "Missing 'isin' in request body"}), 400
    
    sources = body.get("sources")
    
    try:
        result = run_single_stock(isin, sources=sources)
        return jsonify({"status": "completed", "result": result})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/job/<job_id>", methods=["GET"])
def job_status(job_id):
    """Check the status of a background job."""
    if not verify_secret(request):
        return jsonify({"error": "Unauthorized"}), 401

    job = _running_jobs.get(job_id)
    if not job:
        return jsonify({"error": f"Job {job_id} not found"}), 404
    return jsonify({"job_id": job_id, **job})


@app.route("/sources", methods=["GET"])
def list_sources():
    """List available scraper sources and schedules."""
    if not verify_secret(request):
        return jsonify({"error": "Unauthorized"}), 401

    from scrapers import SCRAPER_MAP
    from config import SCHEDULES, BATCH_CONFIG
    
    return jsonify({
        "available_sources": list(SCRAPER_MAP.keys()),
        "schedules": SCHEDULES,
        "batch_config": BATCH_CONFIG,
    })


# ═════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info(f"Starting all_fetching API on port {API_PORT}")
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
