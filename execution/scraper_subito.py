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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.subito.it/",
}

SEARCHES = [
    {"query": "bmw e36",       "label": "BMW E36",       "make": "BMW",      "model": "E36"},
    {"query": "bmw 316 318",   "label": "BMW E36",       "make": "BMW",      "model": "E36"},
    {"query": "audi 80",       "label": "Audi B4/B5",    "make": "Audi",     "model": "80"},
    {"query": "audi a4 1994",  "label": "Audi B5",       "make": "Audi",     "model": "A4"},
    {"query": "mercedes 190e", "label": "Mercedes 190E", "make": "Mercedes", "model": "190E"},
    {"query": "mercedes w201", "label": "Mercedes 190E", "make": "Mercedes", "model": "190E"},
]


def _extract_year(text):
    """Extract 4-digit year from text."""
    if not text:
        return 0
    m = re.search(r'\b(199[0-9]|200[0-6])\b', text)
    return int(m.group(1)) if m else 0


def _scrape_page(query, page=1):
    url = "https://www.subito.it/annunci-italia/vendita/auto/"
    params = {"q": query, "o": page}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _parse_items(soup, label):
    results = []

    # Subito.it wraps each listing in a div/article with class containing "item-card"
    items = (
        soup.select("div[class*='item-card']")
        or soup.select("article[class*='item']")
        or soup.select(".items--wrap > div > div")
    )

    if not items:
        # Last resort: find all links to /annuncio/
        items = [a.parent.parent for a in soup.select("a[href*='/annuncio/']")]

    for item in items:
        try:
            link_el = item.select_one("a[href*='/annuncio/']") or item.select_one("a[href]")
            title_el = item.select_one("h2, h3, [class*='title']")
            price_el = item.select_one("[class*='price']")
            city_el = item.select_one("[class*='town'], [class*='city'], [class*='location']")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            price = parse_price(price_el.get_text(strip=True) if price_el else "")
            if not price or price > MAX_PRICE:
                continue

            # Try to get year from title or description
            year = _extract_year(title) or _extract_year(item.get_text())
            if year and not (YEAR_MIN <= year <= YEAR_MAX):
                continue

            url = link_el["href"] if link_el else ""
            if url and not url.startswith("http"):
                url = "https://www.subito.it" + url

            city = city_el.get_text(strip=True) if city_el else ""
            lat, lon = geocode_city(city)
            dist = distance_from_bergamo(lat, lon)
            if dist is not None and dist > MAX_DISTANCE_KM:
                continue

            results.append({
                "source": "Subito.it",
                "title": title,
                "make": label.split()[0],
                "model": label.split()[-1] if len(label.split()) > 1 else "",
                "year": year,
                "price": price,
                "km": 0,
                "city": city,
                "distance_km": dist,
                "condition": "Usato",
                "url": url,
                "seller": "",
                "phone": "",
                "listing_id": make_listing_id(url, title, price),
                "found_at": datetime.now().isoformat(),
                "label": label,
            })
        except Exception as e:
            print(f"      Subito item error: {e}")

    return results


def _scrape_query(query, label):
    results = []
    for page in range(1, 6):
        try:
            soup = _scrape_page(query, page)
            items = _parse_items(soup, label)
            print(f"    page {page}: {len(items)} listings")
            results.extend(items)
            if len(items) < 5:
                break
            time.sleep(random.uniform(2, 3))
        except Exception as e:
            print(f"    Subito error ('{query}', page {page}): {e}")
            break
    return results


def scrape_subito():
    results = []
    seen_queries = set()
    for search in SEARCHES:
        if search["query"] in seen_queries:
            continue
        seen_queries.add(search["query"])
        print(f"  Subito.it → {search['query']}...")
        found = _scrape_query(search["query"], search["label"])
        results.extend(found)
        time.sleep(random.uniform(2, 4))
    return results
