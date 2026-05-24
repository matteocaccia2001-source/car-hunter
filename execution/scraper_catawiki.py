"""
Catawiki — aste online certificate.
Sezione auto classiche con aste settimanali.
"""
import requests
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price,
    MAX_DISTANCE_KM, MAX_PRICE, YEAR_MIN, YEAR_MAX,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCHES = [
    {"query": "bmw e36",       "label": "BMW E36",       "make": "BMW",      "model": "E36"},
    {"query": "audi 80",       "label": "Audi B4",       "make": "Audi",     "model": "80"},
    {"query": "audi a4",       "label": "Audi B5",       "make": "Audi",     "model": "A4"},
    {"query": "mercedes 190",  "label": "Mercedes 190E", "make": "Mercedes", "model": "190E"},
]


def _extract_year(text):
    if not text:
        return 0
    m = re.search(r'\b(19[5-9]\d|200[0-6])\b', text)
    return int(m.group(1)) if m else 0


def scrape_catawiki():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for search in SEARCHES:
        print(f"  Catawiki → {search['query']}...")
        try:
            url = f"https://www.catawiki.com/it/s?q={search['query'].replace(' ', '+')}&category=auto-classiche"
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("article[class*='lot'], div[class*='LotCard'], div[class*='lot-card']")
                or soup.select("a[href*='/l/']")
            )

            page_count = 0
            for item in items:
                try:
                    text = item.get_text(" ", strip=True)
                    link_el = item.select_one("a[href]") if item.name != "a" else item
                    url_l = link_el["href"] if link_el and link_el.has_attr("href") else ""
                    if url_l and not url_l.startswith("http"):
                        url_l = "https://www.catawiki.com" + url_l

                    title_el = item.select_one("h2, h3, [class*='title']")
                    title = title_el.get_text(strip=True) if title_el else text[:80]

                    price_el = item.select_one("[class*='price'], [class*='bid'], [class*='Bid']")
                    price = parse_price(price_el.get_text(strip=True) if price_el else "")
                    if not price:
                        m = re.search(r'€\s?(\d{1,2}[\.\s]?\d{3})', text)
                        if m:
                            price = int(m.group(1).replace(".", "").replace(" ", ""))
                    # Catawiki shows starting bid — può essere molto basso, ma non scartiamo se 0
                    if price > MAX_PRICE:
                        continue

                    year = _extract_year(title) or _extract_year(text)
                    if year and not (YEAR_MIN <= year <= YEAR_MAX):
                        continue

                    results.append({
                        "source": "Catawiki",
                        "title": title,
                        "make": search["make"], "model": search["model"],
                        "year": year, "price": price or 0, "km": 0,
                        "city": "Asta online", "distance_km": None,
                        "condition": "Asta", "url": url_l,
                        "seller": "Asta", "phone": "",
                        "listing_id": make_listing_id(url_l, title, price),
                        "found_at": datetime.now().isoformat(),
                        "label": search["label"],
                    })
                    page_count += 1
                except Exception as e:
                    print(f"      Catawiki item error: {e}")

            print(f"    {page_count} lots")
            time.sleep(random.uniform(2, 3))

        except Exception as e:
            print(f"    Catawiki error: {e}")

    return results
