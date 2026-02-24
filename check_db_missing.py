import os
import sys
import supabase
from dotenv import load_dotenv

load_dotenv()
sb = supabase.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

import config

response = sb.table(config.SUPABASE_TABLE).select("*").eq("nse_code", "RELIANCE").execute()
if not response.data:
    print("Could not find RELIANCE in the database.")
    sys.exit()

data = response.data[0]
missing = []
for col in config.VALID_COLUMNS:
    if data.get(col) is None:
        missing.append(col)

print(f"Total valid: {len(config.VALID_COLUMNS)}")
print(f"Total populated: {len(config.VALID_COLUMNS) - len(missing)}")
print(f"Missing ({len(missing)}):")
for m in sorted(missing):
    print(f"  - {m}")
