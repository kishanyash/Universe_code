"""
Fix BSE codes in equity_universe that have .0 suffix.
Run this ONCE to clean existing data.
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch all companies with bse_code
response = supabase.table("equity_universe").select("isin_code, bse_code").not_.is_("bse_code", "null").execute()

fixed = 0
total = len(response.data)

for row in response.data:
    bse = row["bse_code"]
    if bse and str(bse).endswith(".0"):
        clean = str(bse).rstrip("0").rstrip(".")  # "500325.0" → "500325"
        supabase.table("equity_universe").update({"bse_code": clean}).eq("isin_code", row["isin_code"]).execute()
        fixed += 1
        print(f"  Fixed: {row['isin_code']} → {bse} → {clean}")

print(f"\nDone! Fixed {fixed}/{total} BSE codes.")
