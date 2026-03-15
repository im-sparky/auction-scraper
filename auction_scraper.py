import requests
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================================
#  YOUR SETTINGS --- Edit this section only
# ============================================================

SEARCH_TERMS = [
   "Taylor guitar",
    "baby tayor guitar",
    "big baby Taylor",
    "Martin guitar",
    "Little Martin guitar",
    "parlor guitar",
    "Fender strat",
    "fender stratocaster"
    "American strat",
    "USA strat",
    "Yamaha Acoustic"
]

MAX_PRICE = 500

EMAIL_FROM = "scottawright1970@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "your_app_password_here")
EMAIL_TO = "scottawright1970@gmail.com"

# ============================================================
#  DO NOT EDIT BELOW THIS LINE
# ============================================================

SEEN_FILE = "seen_listings.json"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)


def search_shopgoodwill(term):
    url = "https://buyerapi.shopgoodwill.com/api/Search/ItemListing"
    payload = {
        "searchText": term,
        "categoryId": "0",
        "searchType": "1",
        "conditionId": "0",
        "sortColumn": "1",
        "sortDescending": True,
        "page": 1,
        "pageSize": 40,
        "goodwillRegionId": 0,
        "isSearchDesc": False,
        "isSearchPartNumber": False,
        "closedAuctions": False,
        "featured": False
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        data = r.json()
        items = []
        for item in data.get("searchResults", {}).get("items", []):
            price = float(item.get("currentPrice", 0))
            if MAX_PRICE and price > MAX_PRICE:
                continue
            items.append({
                "id": "sgw_" + str(item["itemId"]),
                "title": item.get("title", "No title"),
                "price": price,
                "url": "https://shopgoodwill.com/item/" + str(item["itemId"]),
                "site": "ShopGoodwill",
                "end_time": item.get("endTime", "")
            })
        return items
    except Exception as e:
        print("  [ShopGoodwill error for " + term + ": " + str(e) + "]")
        return []


def search_reverb(term):
    query = term.replace(" ", "+")
    url = "https://reverb.com/marketplace?query=" + query
    if MAX_PRICE:
        url += "&price_max=" + str(MAX_PRICE)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for listing in soup.select("[data-listing-id]"):
            listing_id = listing.get("data-listing-id", "")
            title_el = listing.select_one(".grid-card__title")
            price_el = listing.select_one(".price-display")
            link_el = listing.select_one("a")
            if not title_el or not price_el or not link_el:
                continue
            title = title_el.get_text(strip=True)
            raw_price = price_el.get_text().replace("$", "").replace(",", "").strip()
            try:
                price = float(raw_price.split()[0])
            except Exception:
                price = 0.0
            if MAX_PRICE and price > MAX_PRICE:
                continue
            link = link_el.get("href", "")
            if not link.startswith("http"):
                link = "https://reverb.com" + link
            items.append({
                "id": "reverb_" + listing_id,
                "title": title,
                "price": price,
                "url": link,
                "site": "Reverb",
                "end_time": ""
            })
        return items
    except Exception as e:
        print("  [Reverb error for " + term + ": " + str(e) + "]")
        return []


def send_email(new_items):
    subject = "New Auction Finds - " + str(len(new_items)) + " item(s) - " + datetime.now().strftime("%b %d")
    rows = ""
    for item in new_items:
        end_str = "<br><small>Ends: " + item["end_time"] + "</small>" if item["end_time"] else ""
        if item["site"] == "Reverb":
            site_color = "#e85d00"
        else:
            site_color = "#16a34a"
        rows += (
            "<tr>"
            "<td style='padding:12px; border-bottom:1px solid #e5e7eb;'>"
            "<span style='background:" + site_color + "; color:white; font-size:11px; padding:2px 7px; border-radius:4px;'>" + item["site"] + "</span>"
            "<br><a href='" + item["url"] + "' style='font-weight:bold; color:#111;'>" + item["title"] + "</a>"
            + end_str +
            "</td>"
            "<td style='padding:12px; border-bottom:1px solid #e5e7eb; font-size:18px; font-weight:bold; color:#16a34a;'>"
            "$" + "{:.2f}".format(item["price"]) +
            "</td>"
            "</tr>"
        )
    html = (
        "<html><body style='font-family:Arial,sans-serif; max-width:600px; margin:auto;'>"
        "<h2 style='background:#111; color:white; padding:16px; border-radius:8px 8px 0 0; margin:0;'>New Auction Finds</h2>"
        "<p style='color:#555; padding:0 4px;'>Found on " + datetime.now().strftime("%B %d, %Y at %I:%M %p") + "</p>"
        "<table style='width:100%; border-collapse:collapse; border:1px solid #e5e7eb;'>"
        "<thead><tr style='background:#f9fafb;'>"
        "<th style='padding:10px; text-align:left;'>Listing</th>"
        "<th style='padding:10px; text-align:left;'>Price</th>"
        "</tr></thead>"
        "<tbody>" + rows + "</tbody>"
        "</table>"
        "<p style='color:#aaa; font-size:12px; margin-top:16px;'>Sent by your Auction Scraper.</p>"
        "</body></html>"
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print("  Email sent: " + str(len(new_items)) + " new item(s).")
    except Exception as e:
        print("  Email failed: " + str(e))


def run():
    print("Auction Scraper - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    seen = load_seen()
    new_items = []
    for term in SEARCH_TERMS:
        print("Searching: " + term)
        results = search_shopgoodwill(term) + search_reverb(term)
        term_new = 0
        for item in results:
            if item["id"] not in seen:
                seen[item["id"]] = True
                new_items.append(item)
                term_new += 1
                print("  NEW: " + item["title"] + " - $" + "{:.2f}".format(item["price"]) + " (" + item["site"] + ")")
        if term_new == 0:
            print("  No new listings.")
    print("New listings found: " + str(len(new_items)))
    if new_items:
        send_email(new_items)
    else:
        print("No email sent (nothing new).")
    save_seen(seen)
    print("Done.")


if __name__ == "__main__":
    run()
