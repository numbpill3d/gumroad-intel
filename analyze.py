#!/usr/bin/env python3
"""Reproduce every number in REPORT.md from ./data/. No API calls, no writes."""
import json, collections, itertools, datetime as dt, pathlib, statistics

D = pathlib.Path(__file__).parent / "data"
S = json.loads((D / "sales.json").read_text())
P = json.loads((D / "products.json").read_text())
byid = {p["id"]: p for p in P}

paid = [s for s in S if s.get("paid")]
free = [s for s in S if not s.get("paid")]
pub  = [p for p in P if p.get("published")]

def h(t): print(f"\n{'='*72}\n{t}\n{'='*72}")

h("HEADLINE")
gross = sum(s["price"] for s in paid) / 100
fees  = sum(s.get("gumroad_fee", 0) for s in paid) / 100
d = [dt.datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")) for s in paid]
print(f"lifetime gross ${gross:,.2f} | fees ${fees:,.2f} ({fees/gross*100:.1f}%) | net ${gross-fees:,.2f}")
print(f"{len(paid)} paid orders + {len(free)} free downloads | {min(d).date()} .. {max(d).date()}")
print(f"AOV ${gross/len(paid):.2f} | median ${statistics.median(s['price'] for s in paid)/100:.2f}")
# cross-check against lifetime totals in the products payload (truncation guard)
life = sum((p.get("sales_usd_cents") or 0) for p in P) / 100
print(f"truncation guard: products-payload lifetime ${life:,.2f} vs pulled ${gross:,.2f} (delta ${life-gross:,.2f})")

h("MONTHLY")
m = collections.defaultdict(lambda: [0, 0.0])
for s in paid:
    k = s["created_at"][:7]; m[k][0] += 1; m[k][1] += s["price"] / 100
for k in sorted(m): print(f"  {k}  {m[k][0]:4d} orders  ${m[k][1]:9,.2f}")

h("FUNNEL — free tier (order-aware, not naive overlap)")
ff = collections.defaultdict(list); fp = collections.defaultdict(list)
for s in free: ff[s["email"]].append(s["created_at"])
for s in paid: fp[s["email"]].append(s["created_at"])
both = set(ff) & set(fp)
conv = [e for e in both if min(ff[e]) < min(fp[e])]
print(f"  free downloaders {len(ff)} | buyers {len(fp)}")
print(f"  free THEN paid: {len(conv)} ({len(conv)/len(ff)*100:.1f}% of free list)")
print(f"  paid THEN grabbed a freebie: {len(both)-len(conv)}  (do NOT count these as conversions)")
print(f"  free downloaders who never bought: {len(set(ff)-set(fp))}")

h("REPEAT BUYERS / CONCENTRATION")
byemail = collections.defaultdict(list)
for s in paid: byemail[s["email"]].append(s)
rep = {e: v for e, v in byemail.items() if len(v) > 1}
rev_rep = sum(s["price"] for v in rep.values() for s in v) / 100
print(f"  buyers {len(byemail)} | repeat {len(rep)} ({len(rep)/len(byemail)*100:.0f}%) = ${rev_rep:,.2f} ({rev_rep/gross*100:.0f}% of revenue)")
ltv = sorted(((sum(s["price"] for s in v)/100, len(v), e) for e, v in byemail.items()), reverse=True)
print(f"  top 3 buyers = ${sum(x[0] for x in ltv[:3]):,.2f} ({sum(x[0] for x in ltv[:3])/gross*100:.0f}% of revenue)")
for v, n, e in ltv[:5]: print(f"    ${v:8,.2f}  {n:2d} orders  {e}")

h("CHANNELS")
def norm(r):
    if not r or r == "direct": return "direct"
    from urllib.parse import urlparse
    return (urlparse(r).netloc or r).replace("www.", "")
rev = collections.defaultdict(float); cnt = collections.Counter()
for s in paid:
    k = norm(s.get("referrer")); rev[k] += s["price"]/100; cnt[k] += 1
for k, v in sorted(rev.items(), key=lambda x: -x[1])[:8]:
    print(f"  ${v:8,.2f}  x{cnt[k]:3d}  {v/gross*100:4.1f}%  {k}")
disc = [s for s in paid if s.get("discover_fee_charged")]
dr = sum(s["price"] for s in disc)/100; df = sum(s.get("gumroad_fee",0) for s in disc)/100
print(f"  Gumroad Discover: {len(disc)} orders ${dr:,.2f} at {df/dr*100:.0f}% fee ({dr/gross*100:.1f}% of revenue)")

h("LIST-vs-PAID BY RECENCY (NOT a discount rate — confounded by price history)")
print("  The catalog snapshot is today's prices. Prices rose 4-6x across the year, so an")
print("  all-time subtraction reads historical prices as discounts. Only recent windows are valid.")
def window(days):
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    rows = [s for s in paid if dt.datetime.fromisoformat(s["created_at"].replace("Z","+00:00")) > cut]
    tl = tp = 0; below = 0
    for s in rows:
        p = byid.get(s["product_id"])
        if not p or p.get("customizable_price"): continue
        lp = p.get("price") or 0
        if lp <= 0: continue
        tl += lp; tp += s["price"]
        if s["price"] < lp * 0.98: below += 1
    return tl, tp, below, len(rows)
for days, lab in [(30,"last 30d"),(90,"last 90d"),(180,"last 180d"),(9999,"all time")]:
    tl, tp, below, n = window(days)
    if not tl: continue
    print(f"  {lab:10s} {n:3d} orders | list ${tl/100:9,.2f} -> paid ${tp/100:9,.2f} | delta {(tl-tp)/tl*100:6.1f}% | below list {below}")
print("  -> the last-90d figure is the trustworthy one; treat all-time as price history, not discounting.")

h("PRICE TRAJECTORY (step functions = repricing, scatter = discounting)")
seq = collections.defaultdict(list)
for s in sorted(paid, key=lambda x: x["created_at"]): seq[s["product_id"]].append(s["price"])
shown = 0
for pid, prices in sorted(seq.items(), key=lambda x: -len(x[1])):
    if len(prices) < 6 or shown >= 8: continue
    print(f"  {byid.get(pid,{}).get('name','?')[:42]:44s} list ${(byid.get(pid,{}).get('price') or 0)/100:6.2f}  {[round(p/100) for p in prices]}")
    shown += 1

h("SUB-$10 ORDERS OVER TIME")
m = collections.defaultdict(lambda: [0, 0])
for s in paid:
    k = s["created_at"][:7]; m[k][0] += 1
    if s["price"] < 1000: m[k][1] += 1
for k in sorted(m): print(f"  {k}  {m[k][0]:4d} orders  {m[k][1]:4d} under $10")

h("FEE DRAG BY PRICE BAND")
for lo, hi, lab in [(0,1000,"< $10"),(1000,2000,"$10-20"),(2000,4000,"$20-40"),(4000,7500,"$40-75"),(7500,10**9,"$75+")]:
    g = [s for s in paid if lo <= s["price"] < hi]
    if not g: continue
    r = sum(s["price"] for s in g); f = sum(s.get("gumroad_fee",0) for s in g)
    print(f"  {lab:8s} {len(g):3d} orders  ${r/100:8,.2f} ({r/100/gross*100:4.1f}% rev)  fee {f/r*100:5.1f}%  net/order ${(r-f)/len(g)/100:6.2f}")

h("CATALOG HEALTH")
zero = [p for p in pub if (p.get("sales_count") or 0) == 0]
print(f"  {len(P)} products | {len(pub)} published | {len(zero)} published with zero lifetime sales ({len(zero)/len(pub)*100:.0f}%)")
print(f"  PWYW products: {sum(1 for p in P if p.get('customizable_price'))} (zero-sale: {sum(1 for p in P if p.get('customizable_price') and not (p.get('sales_count') or 0))})")
print(f"  memberships/subscriptions: {sum(1 for p in P if p.get('is_tiered_membership') or p.get('recurrences'))}  |  recurring orders: {sum(1 for s in paid if s.get('is_recurring_billing'))}")

h("BUNDLES")
bp = [s for s in paid if s.get("is_bundle_purchase")]
bundles = [p for p in P if p.get("bundle_products")]
print(f"  {len(bp)} bundle orders = ${sum(s['price'] for s in bp)/100:,.2f} ({sum(s['price'] for s in bp)/100/gross*100:.0f}% of revenue) from {len(bundles)} bundle SKUs")
for p in sorted(bundles, key=lambda x: -(x.get("sales_usd_cents") or 0)):
    print(f"    ${(p.get('sales_usd_cents') or 0)/100:8,.2f}  list ${(p.get('price') or 0)/100:6.2f}  x{len(p.get('bundle_products') or [])} items  {p['name'][:50]}")

h("AFFINITY (whale-adjusted: top-3 LTV excluded, baskets <= 10 items)")
sets = collections.defaultdict(set)
for s in paid: sets[s["email"]].add(s["product_id"])
top3 = {e for _, _, e in ltv[:3]}
pair = collections.Counter()
for e, ids in sets.items():
    if e in top3 or not (1 < len(ids) <= 10): continue
    for a, b in itertools.combinations(sorted(ids), 2): pair[(a, b)] += 1
print(f"  qualifying baskets: {sum(1 for e,i in sets.items() if e not in top3 and 1<len(i)<=10)} (weak signal — treat as directional only)")
for (a, b), c in pair.most_common(8):
    print(f"    {c}x  {byid.get(a,{}).get('name','?')[:40]:42s} + {byid.get(b,{}).get('name','?')[:40]}")

h("TOP PRODUCTS")
r = collections.defaultdict(lambda: [0, 0.0])
for s in paid: r[s["product_name"]][0] += 1; r[s["product_name"]][1] += s["price"]/100
for k, (c, v) in sorted(r.items(), key=lambda x: -x[1][1])[:15]:
    print(f"  ${v:8,.2f}  x{c:3d}  {k[:62]}")
cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)
recent = [s for s in paid if dt.datetime.fromisoformat(s["created_at"].replace("Z","+00:00")) > cut]
rr = collections.defaultdict(float)
for s in recent: rr[s["product_name"]] += s["price"]/100
print(f"\n  --- last 90 days: {len(recent)} orders / ${sum(s['price'] for s in recent)/100:,.2f} ---")
for k, v in sorted(rr.items(), key=lambda x: -x[1])[:10]: print(f"  ${v:8,.2f}  {k[:62]}")

h("RATINGS")
rated = [s for s in paid if s.get("product_rating")]
rp = collections.defaultdict(list)
for s in rated: rp[s["product_name"]].append(s["product_rating"])
print(f"  {len(rated)}/{len(paid)} orders rated ({len(rated)/len(paid)*100:.0f}%) | distribution {dict(collections.Counter(s['product_rating'] for s in rated))}")
for k, v in rp.items():
    if sum(v)/len(v) < 4: print(f"    {sum(v)/len(v):.1f}★ (n={len(v)})  {k[:60]}")
