#!/usr/bin/env python3
"""Minimal Gumroad API v2 client. Reads token from ~/.config/gumroad/credentials.env."""
import json, os, time, urllib.parse, urllib.request, pathlib

CRED = pathlib.Path.home() / ".config/gumroad/credentials.env"
BASE = "https://api.gumroad.com/v2"

def token():
    t = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if t:
        return t
    for line in CRED.read_text().splitlines():
        line = line.strip()
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1]
    raise SystemExit("no GUMROAD_ACCESS_TOKEN found")

TOKEN = token()

def get(path, **params):
    params["access_token"] = TOKEN
    url = f"{BASE}/{path.lstrip('/')}?{urllib.parse.urlencode(params)}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)

def get_url(url):
    if not url.startswith("http"):
        url = "https://api.gumroad.com" + url
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}access_token={TOKEN}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)

def all_sales(after=None):
    """Walk every page of /v2/sales."""
    out, seen = [], set()
    params = {}
    if after:
        params["after"] = after
    d = get("sales", **params)
    while True:
        batch = d.get("sales", [])
        new = 0
        for s in batch:
            if s["id"] not in seen:
                seen.add(s["id"]); out.append(s); new += 1
        print(f"  page: +{new} (total {len(out)})", flush=True)
        nxt = d.get("next_page_url")
        if not nxt or not batch:
            break
        d = get_url(nxt)
    return out


def put(path, **params):
    """Form-encoded PUT against the API. Gumroad product prices are cents here."""
    params["access_token"] = TOKEN
    body = urllib.parse.urlencode(params).encode()
    url = f"{BASE}/{path.lstrip('/')}"
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def delete(path):
    """DELETE against the API. Only called by scripts that ask for --apply."""
    url = f"{BASE}/{path.lstrip('/')}?" + urllib.parse.urlencode({"access_token": TOKEN})
    req = urllib.request.Request(url, method="DELETE")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())
