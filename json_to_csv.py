#!/usr/bin/env python
"""
Convert the JSON produced by scrape_grants.py into a flat CSV.
Nested keys under `details` are expanded using `__` as the separator.
"""
import argparse, json, pandas as pd

def main():
    p = argparse.ArgumentParser()
    p.add_argument("json_file", help="scraped_data_*.json")
    p.add_argument("-o", "--out", default=None, help="output CSV name")
    args = p.parse_args()

    with open(args.json_file, encoding="utf-8") as f:
        data = json.load(f)

    # flatten details dict -> details__Key columns
    df = pd.json_normalize(data, sep="__")

    out = args.out or args.json_file.rsplit(".", 1)[0] + ".csv"
    df.to_csv(out, index=False)
    print(f"CSV written → {out}")

if __name__ == "__main__":
    main()