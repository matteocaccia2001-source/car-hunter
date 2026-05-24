"""
ClassicCarMarketplace + AutoSupermarket: portali specializzati auto storiche italiani.
Volume basso, curato, alta qualità di annunci.
"""
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Classic Trader IT — portale dedicato auto storiche
CLASSIC_TRADER_SEARCHES = [
    {"slug": "bmw-3-serie",     "make": "BMW",       "model": "Serie 3", "label": "BMW E36"},
    {"slug": "audi-80",          "make": "Audi",      "model": "80",      "label": "Audi B4"},
    {"slug": "audi-a4",          "make": "Audi",      "model": "A4",      "label": "Audi B5"},
    {"slug": "mercedes-benz-190","make": "Mercedes",  "model": "190E",    "label": "Mercedes 190E"},
]


def _extract_year(text):
    if not text:
        return 0
    m = re.search(r'\b(19[5-9]\d|200[0-6])\b', text)
    return int(m.group(1)) if m else 0


def scrape_classic_trader():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for search in CLASSIC_TRADER_SEARCHES:
        print(f"  ClassicTrader → {search['label']}...")
        try:
            url = (
                f"https://it.classic-trader.com/it/auto/lista/{search['slug']}"
                f"?yearOfManufactureFrom={YEAR_MIN}&yearOfManufactureUntil={YEAR_MAX}"
                f"&priceUntil={MAX_PRICE}&country=it"
            )
            resp = session.get(url, timeout=20)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select("article[class*='offer'], div[class*='offer'], div[class*='listing']")
                or soup.select("a[href*='/auto/'][href*='/dettagli/']")
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
                        url_l = "https://it.classic-trader.com" + url_l

                    title_el = item.select_one("h2, h3, [class*='title']")
                    title = title_el.get_text(strip=True) if title_el else text[:80]

                    price_el = item.select_one("[class*='price']")
                    price = parse_price(price_el.get_text(strip=True) if price_el else "")
                    if not price:
                        m = re.search(r'€\s?(\d{1,2}[\.\s]?\d{3})', text)
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
                        "source": "ClassicTrader",
                        "title": title,
                        "make": search["make"], "model": search["model"],
                        "year": year, "price": price, "km": 0,
                        "city": city, "distance_km": dist,
                        "condition": "Storica", "url": url_l,
                        "seller": "", "phone": "",
                        "listing_id": make_listing_id(url_l, title, price),
                        "found_at": datetime.now().isoformat(),
                        "label": search["label"],
                    })
                    page_count += 1
                except Exception as e:
                    print(f"      ClassicTrader item error: {e}")

            print(f"    {page_count} listings")
            time.sleep(random.uniform(2, 3))

        except Exception as e:
            print(f"    ClassicTrader error: {e}")

    return results


def scrape_motostoriche():
    """Entry point — chiama tutti i portali specializzati."""
    return scrape_classic_trader()
