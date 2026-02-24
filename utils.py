"""
=============================================================================
UTILS - Shared utility functions
=============================================================================
"""
import logging
import time
import math
import re
import random
from selenium import webdriver
from config import CHROME_ARGS

logger = logging.getLogger("all_fetching")


def get_chrome_driver(download_dir=None):
    """Create and return a configured headless Chrome WebDriver."""
    opts = webdriver.ChromeOptions()
    for arg in CHROME_ARGS:
        opts.add_argument(arg)
    if download_dir:
        prefs = {"download.default_directory": download_dir, "directory_upgrade": True}
        opts.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=opts)


def parse_number(text):
    """Parse a number from text, stripping currency symbols, commas, etc."""
    if not text:
        return None
    text = str(text).strip()
    text = text.replace('₹', '').replace(',', '').replace('%', '').replace('Cr.', '').strip()
    if not text or text in ('--', '', '+', '-'):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_float(x):
    """Safely convert a string (possibly with commas) to float."""
    if x is None or x == "-" or x == "":
        return None
    try:
        return round(float(str(x).replace(",", "")), 2)
    except (ValueError, TypeError):
        return None


def safe_round(value, decimals=2):
    """Safely round a value, returning None if not a valid number."""
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, decimals)
    except (ValueError, TypeError):
        return None


def calculate_cagr(start_val, end_val, years):
    """Calculate Compound Annual Growth Rate."""
    if start_val is None or end_val is None or years <= 0:
        return None
    if start_val <= 0 or end_val <= 0:
        return None
    try:
        return round(((end_val / start_val) ** (1 / years) - 1) * 100, 2)
    except (ZeroDivisionError, ValueError, OverflowError):
        return None


def find_key(data_dict, possible_names):
    """Find matching key in dict, handling 'Sales+' style names."""
    for name in possible_names:
        if name in data_dict:
            return name
    for key in data_dict:
        clean_key = key.rstrip('+').strip()
        for name in possible_names:
            clean_name = name.rstrip('+').strip()
            if clean_key == clean_name:
                return key
    return None


def clean_bse_code(bse_code):
    """Clean BSE code: strip .0 suffix and whitespace."""
    if not bse_code:
        return None
    bse = str(bse_code).strip()
    if bse.endswith(".0"):
        bse = bse[:-2]
    return bse if bse else None


def random_delay(low=1.0, high=3.0):
    """Sleep for a random duration to mimic human behavior."""
    time.sleep(random.uniform(low, high))


def chunks(lst, n):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
