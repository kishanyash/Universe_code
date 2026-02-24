import os
import supabase
from dotenv import load_dotenv
import config

load_dotenv()
sb = supabase.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

response = sb.table(config.SUPABASE_TABLE).select("*").eq("nse_code", "RELIANCE").execute()
if not response.data:
    with open("missing_fields.txt", "w") as f:
        f.write("No data found")
else:
    data = response.data[0]
    missing = []
    for col in config.VALID_COLUMNS:
        if data.get(col) is None:
            missing.append(col)
    
    with open("missing_fields.txt", "w") as f:
        f.write(f"Populated: {len(config.VALID_COLUMNS) - len(missing)}\n")
        f.write(f"Missing ({len(missing)}):\n")
        for m in sorted(missing):
            f.write(f" - {m}\n")
