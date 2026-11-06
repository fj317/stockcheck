# check.py
import os, re, json, sys
import requests

URL = ("https://www.boots.com/shark-flexstyle-limited-edition-orchid-sunrise-"
       "4-in-1-air-styler-and-hair-dryer-with-storage-bag-10387655")
NTFY_TOPIC = "stockcheck"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9",
}

def notify(msg):
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
                  headers={"Title": "Boots stock alert", "Click": URL})

def in_stock(html):
    # 1) Structured data, if the page has it
    for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except Exception:
            continue
        for item in (data if isinstance(data, list) else [data]):
            offers = item.get("offers") if isinstance(item, dict) else None
            if isinstance(offers, dict):
                offers = [offers]
            for o in offers or []:
                avail = str(o.get("availability", ""))
                if "InStock" in avail:
                    return True
                if "OutOfStock" in avail:
                    return False
    # 2) Text fallback
    text = html.lower()
    if "stock coming soon" in text or "temporarily unavailable online" in text:
        return False
    return "add to basket" in text

r = requests.get(URL, headers=HEADERS, timeout=30)
print("Status:", r.status_code)

if r.status_code != 200:
    print("Blocked or error, can't check.")
    sys.exit(1)  # makes the GitHub Action show as failed

if in_stock(r.text):
    notify("It looks like the Shark FlexStyle is back in stock!")
    print("IN STOCK")
else:
    print("Still out of stock")
