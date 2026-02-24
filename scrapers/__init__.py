"""Scraper modules registry."""
from scrapers.yahoo_finance import scrape_yahoo_finance
from scrapers.trendlyne import scrape_trendlyne
from scrapers.go_india_stocks import scrape_go_india
from scrapers.screener import scrape_screener_daily, scrape_screener_full

SCRAPER_MAP = {
    "yahoo_finance": scrape_yahoo_finance,
    "screener_daily": scrape_screener_daily,
    "screener_full": scrape_screener_full,
    "trendlyne": scrape_trendlyne,
    "go_india_stocks": scrape_go_india,
}
