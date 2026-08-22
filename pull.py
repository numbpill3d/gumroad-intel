#!/usr/bin/env python3
"""Refresh every Gumroad dataset into ./data/. Read-only against the API."""
import gr, json, pathlib, sys

D = pathlib.Path(__file__).parent / "data"; D.mkdir(exist_ok=True)

def paged(path, key):
    out, seen = [], set()
    d = gr.get(path)
    while True:
        batch = d.get(key, [])
        for r in batch:
            if r["id"] not in seen:
                seen.add(r["id"]); out.append(r)
        nxt = d.get("next_page_url")
        if not nxt or not batch:
            return out
        d = gr.get_url(nxt)

def main():
    prods = paged("products", "products")
    (D / "products.json").write_text(json.dumps(prods, indent=2))
    print(f"products: {len(prods)}")

    sales = gr.all_sales()
    (D / "sales.json").write_text(json.dumps(sales, indent=2))
    print(f"sales: {len(sales)}")

    if "--offer-codes" in sys.argv:
        codes = {}
        for p in prods:
            try:
                codes[p["id"]] = gr.get(f"products/{p['id']}/offer_codes").get("offer_codes", [])
            except Exception as e:
                codes[p["id"]] = {"error": str(e)}
        (D / "offer_codes.json").write_text(json.dumps(codes, indent=2))
        print(f"offer codes pulled for {len(codes)} products")

if __name__ == "__main__":
    main()
