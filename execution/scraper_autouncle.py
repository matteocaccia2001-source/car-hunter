"""
AutoUncle.it — aggregatore italiano di auto usate.
Blocca i data center IP → via ScraperAPI (se SCRAPER_API_KEY configurato).
"""
import os
import requests
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price, parse_km,
    MAX_DISTANCE_KM, MAX_PRICE, YEAR_MIN, YEAR_MAX,
)

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "").strip()

SEARCHES = [
    {"path": "bmw-serie_3",            "make": "BMW",       "model": "Serie 3", "label": "BMW E36"},
    {"path": "audi-a4",                 "make": "Audi",      "model": "A4",      "label": "Audi B5"},
    {"path": "mercedes_benz-classe_e", "make": "Mercedes",  "model": "190E",    "label": "Mercedes 190E"},
]


def _extract_year(text):
    if not text:
        return 0
    m = re.search(r'\b(199[0-9]|200[0-6])\b', text)
    return int(m.group(1)) if m else 0


def _fetch_via_scraperapi(target_url):
    params = {"api_key": SCRAPER_API_KEY, "url": target_url, "country_code": "it"}
    resp = requests.get("http://api.scraperapi.com", params=params, timeout=70)
    resp.raise_for_status()
    return resp.text


def scrape_autouncle():
    if not SCRAPER_API_KEY:
        print("  AutoUncle skipped: SCRAPER_API_KEY non configurato")
        return []

    results = []
    for search in SEARCHES:
        print(f"  AutoUncle (ScraperAPI) → {search['label']}...")
        try:
            target = (
                f"https://www.autouncle.it/it/auto_usate/{search['path']}"
                f"?s%5Byear_from%5D={YEAR_MIN}&s%5Byear_to%5D={YEAR_MAX}"
                f"&s%5Bprice_to%5D={MAX_PRICE}"
            )
            html = _fetch_via_scraperapi(target)
            soup = BeautifulSoup(html, "html.parser")

            items = (
                soup.select("div.car-list-item, article.car-item, div[class*='CarCard']")
                or soup.select("a[href*='/auto_usate/']")
            )

            page_count = 0
            for item in items:
                try:
                    text = item.get_text(" ", strip=True)
                    if "€" not in text:
                        continue

                    link_el = item.select_one("a[href]") if item.name != "a" else item
                    url_l = link_el["href"] if link_el and link_el.has_attr("href") else ""
                    if url_l and not url_l.startswith("http"):
                        url_l = "https://www.autouncle.it" + url_l

                    title_el = item.select_one("h2, h3, [class*='title']")
                    title = title_el.get_text(strip=True) if title_el else text[:80]

                    price_el = item.select_one("[class*='price']")
                    price = parse_price(price_el.get_text(strip=True) if price_el else "")
                    if not price:
                        m = re.search(r'(\d{1,2}[\.\s]?\d{3})\s*€', text)
                        if m:
                            price = int(m.group(1).replace(".", "").replace(" ", ""))
                    if not price or price > MAX_PRICE:
                        continue

                    year = _extract_year(title) or _extract_year(text)
                    if year and not (YEAR_MIN <= year <= YEAR_MAX):
                        continue

                    city_el = item.select_one("[class*='location'], [class*='city']")
                    city = city_el.get_text(strip=True) if city_el else ""
                    lat, lon = geocode_city(city)
                    dist = distance_from_bergamo(lat, lon)
                    if dist is not None and dist > MAX_DISTANCE_KM:
                        continue

                    results.append({
                        "source": "AutoUncle",
                        "title": title,
                        "make": search["make"], "model": search["model"],
                        "year": year, "price": price, "km": 0,
                        "city": city, "distance_km": dist,
                        "condition": "Usato", "url": url_l,
                        "seller": "", "phone": "",
                        "listing_id": make_listing_id(url_l, title, price),
                        "found_at": datetime.now().isoformat(),
                        "label": search["label"],
                    })
                    page_count += 1
                except Exception as e:
                    print(f"      AutoUncle item error: {e}")

            print(f"    {page_count} listings")
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"    AutoUncle error: {e}")

    return results
