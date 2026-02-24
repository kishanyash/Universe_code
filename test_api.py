import requests
import time
import sys

API_URL = "http://127.0.0.1:5001"
SECRET = "change-me-in-production"
HEADERS = {"X-API-Secret": SECRET, "Content-Type": "application/json"}

def print_result(name, res):
    print(f"--- {name} ---")
    print(f"Status: {res.status_code}")
    try:
        print(f"Response: {res.json()}")
    except:
        print(f"Response (Text): {res.text}")
    print()

def test():
    # 1. Health check
    try:
        res = requests.get(f"{API_URL}/health")
        print_result("GET /health", res)
    except Exception as e:
        print(f"Failed to connect to API: {e}")
        sys.exit(1)

    # 2. Check sources
    res = requests.get(f"{API_URL}/sources")
    print_result("GET /sources", res)

    # 3. Test single stock endpoint (Reliance)
    payload = {
        "isin": "INE002A01018"
    }
    print("Testing single stock data fetch (this may take a minute or two as it calls the scrapers)...")
    res = requests.post(f"{API_URL}/webhook/single", json=payload, headers=HEADERS)
    print_result("POST /webhook/single", res)

if __name__ == "__main__":
    test()
