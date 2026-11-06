# check.py
import os, re, sys, urllib.request
from datetime import datetime
from cloakbrowser import launch  # stealth Chromium; plain requests gets Boots' bot wall

URLS = [
    "https://www.boots.com/shark-flexstyle-limited-edition-orchid-sunrise-4-in-1-air-styler-and-hair-dryer-with-storage-bag-10387655",
    "https://www.boots.com/shark-flexstyle-4-in-1-air-styler-and-hair-dryer-stone-hd436sluk-10359019",
]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]


def notify(msg, url):
    urllib.request.urlopen(urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode(),
        headers={"Title": "Boots stock alert", "Click": url}), timeout=30)


def in_stock(html):
    # Boots renders <input type="hidden" id="isInStock" value="true|false">
    m = re.search(r'id="isInStock"\s+value="(true|false)"', html)
    return None if not m else m.group(1) == "true"  # None: bot wall or page changed


print("Run", datetime.now().strftime("%Y-%m-%d %H:%M"))
failed, alerts = False, []  # (msg, url); sent as one ntfy message at the end
browser = launch()
page = browser.new_page()
for url in URLS:
    name = url.rsplit("/", 1)[-1]
    try:
        r = page.goto(url, timeout=60_000)
        try:  # bot-check JS can reload the page; wait for the stock field itself
            page.wait_for_selector("#isInStock", state="attached", timeout=30_000)
        except Exception:
            pass  # in_stock() returns None below and we alert
        for attempt in range(3):  # content() throws if the bot check reloads mid-read
            try:
                html = page.content()
                break
            except Exception:
                if attempt == 2:
                    raise
                page.wait_for_load_state("load", timeout=30_000)
        status = r.status if r else None
        print(name, "Status:", status)
        problem = None if status == 200 else f"HTTP {status}"
    except Exception as e:
        html, problem = "", f"page load failed: {e}"

    stock = in_stock(html) if not problem else None
    if stock is None:
        problem = problem or f"no stock info on page: {page.title()!r}"
        print(" ", problem)
        print("  page starts:", html[:500].replace("\n", " "))  # shows what the bot wall served
        alerts.append((f"Check failed for {name}: {problem}", url))
        failed = True  # keep checking the others, fail the run at the end
    elif stock:
        alerts.append((f"Back in stock: {url}", url))
        print("  IN STOCK")
    else:
        print("  Still out of stock")
browser.close()

if alerts:  # click opens the first in-stock product, else the first failed one
    in_stock_urls = [u for m, u in alerts if m.startswith("Back")]
    notify("\n\n".join(m for m, _ in alerts), (in_stock_urls or [alerts[0][1]])[0])

sys.exit(1 if failed else 0)  # makes the GitHub Action show as failed
