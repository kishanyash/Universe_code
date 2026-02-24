from scrapers.screener import fetch_screener_page, parse_table
soup = fetch_screener_page("RELIANCE", "500325")
ratios_data, _ = parse_table(soup, 'ratios')
with open("ratios_keys.txt", "w") as f:
    for k, v in ratios_data.items():
        f.write(f"{k}: {v}\n")
