#!/usr/bin/env python3
"""
Audit and delete stale offer codes on the Gumroad store.

Gumroad's codes here are UNIVERSAL: one code object is attached to every product,
so a single DELETE removes it store-wide. Verified 2026-08-22 — two different
products returned identical code ids for all 65 shared codes.

DRY RUN BY DEFAULT. Prints the full disposition of every code and changes nothing.
  --apply    actually delete the codes in the DELETE list
  --canary   with --apply, delete exactly one obvious development code and stop
  --keep-50  do not delete codes that are 50% off (conservative first pass)

Deletion rules (case-insensitive), all of which are never-expiring codes:
  test* debug* final* direct*   leftover development artifacts
  vault<digits>                 auto-generated batch, all 50% off
  AUG-<digits>[-<digits>]       same generation batch as TEST-1534
  <slug><MMDD> / <digits><MMDD> date-stamped campaign batch (Jul 29 / Oct 16), expired in intent
  BLACKFRIDAY2025 midnightjun18 named seasonal codes long past their date

Everything else is listed under KEEP with its discount, so nothing disappears silently.
"""
import gr, json, re, sys, pathlib

DEV      = re.compile(r"^(test|debug|final|direct)", re.I)
VAULT    = re.compile(r"^vault\d+$", re.I)
AUGBATCH = re.compile(r"^aug-\d+(-\d+)?$", re.I)
DATED    = re.compile(r"^[a-z0-9-]*(0729|07295|1016|10165)$", re.I)
SEASONAL = {"blackfriday2025", "midnightjun18"}

def doomed(name):
    if not name:
        return True                      # unnamed codes cannot be shared or audited
    n = name.strip()
    return bool(DEV.match(n) or VAULT.match(n) or AUGBATCH.match(n)
                or DATED.match(n) or n.lower() in SEASONAL)

def main():
    apply_   = "--apply" in sys.argv
    canary   = "--canary" in sys.argv
    keep50   = "--keep-50" in sys.argv
    if canary and not apply_:
        raise SystemExit("--canary must be paired with --apply")
    prods = json.loads((pathlib.Path(__file__).parent / "data/products.json").read_text())

    # Universal codes: one product enumerates the whole store-wide set.
    probe = prods[0]
    codes = gr.get(f"products/{probe['id']}/offer_codes").get("offer_codes", [])
    print(f"enumerated {len(codes)} store-wide codes via {probe['name'][:44]!r}\n")

    kill, keep = [], []
    for c in codes:
        pct, amt = c.get("percent_off"), c.get("amount_off")
        off = f"{pct}%" if pct else (f"${(amt or 0)/100:.2f}" if amt else "?")
        row = (c["id"], c.get("name") or "<unnamed>", off, pct or 0)
        (kill if doomed(c.get("name")) else keep).append(row)

    if keep50:
        spared = [r for r in kill if r[3] >= 50]
        kill   = [r for r in kill if r[3] < 50]
        keep  += spared
        print(f"--keep-50: sparing {len(spared)} codes at 50% off\n")

    if canary:
        candidates = [r for r in kill if DEV.match(r[1])]
        if not candidates:
            raise SystemExit("no obvious development code is available for a canary")
        selected = sorted(candidates, key=lambda r: r[1].lower())[0]
        keep += [r for r in kill if r != selected]
        kill = [selected]
        print(f"--canary: limiting mutation to {selected[1]!r}\n")

    print(f"DELETE ({len(kill)}):")
    for _, n, off, _pct in sorted(kill, key=lambda r: -r[3]):
        print(f"    {off:>5s} off   {n}")
    print(f"\nKEEP ({len(keep)}) — review these yourself, several are still steep:")
    for _, n, off, pct in sorted(keep, key=lambda r: -r[3]):
        flag = "  <-- still steep and never expires" if pct >= 30 else ""
        print(f"    {off:>5s} off   {n}{flag}")

    if not apply_:
        print(f"\nDRY RUN — nothing deleted. Re-run with --apply to remove the {len(kill)} DELETE codes.")
        print("Each delete is one store-wide call; there is no per-product loop.")
        return

    ok = fail = 0
    for cid, name, off, _pct in kill:
        try:
            gr.delete(f"products/{probe['id']}/offer_codes/{cid}")
            ok += 1
            print(f"  deleted {name}")
        except Exception as e:
            fail += 1
            print(f"  FAILED  {name}: {e}")
    print(f"\ndeleted {ok} | failed {fail}")
    print("Re-run without --apply to verify the remaining set against the live API.")

if __name__ == "__main__":
    main()
