"""
Bakeca.it scraper — sostituisce Subito.it (bloccato su GitHub Actions).
Bakeca.it è il secondo classificato italiano per auto usate e non blocca i data center.
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
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.bakeca.it/",
}

SEARCHES = [
    {"url": "https://www.bakeca.it/annunci/auto/bmw/serie-3/",   "label": "BMW E36",       "make": "BMW",      "model": "E36"},
    {"url": "https://www.bakeca.it/annunci/auto/audi/80/",        "label": "Audi B4/B5",    "make": "Audi",     "model": "80"},
    {"url": "https://www.bakeca.it/annunci/auto/audi/a4/",        "label": "Audi B5",       "make": "Audi",     "model": "A4"},
    {"url": "https://www.bakeca.it/annunci/auto/mercedes/190/",   "label": "Mercedes 190E", "make": "Mercedes", "model": "190E"},
    # Generic search fallback
    {"url": "https://www.bakeca.it/annunci/auto/?q=bmw+e36",      "label": "BMW E36",       "make": "BMW",      "model": "E36"},
    {"url": "https://www.bakeca.it/annunci/auto/?q=mercedes+190e","label": "Mercedes 190E", "make": "Mercedes", "model": "190E"},
]


def _extract_year(text):
    if not text:
        return 0
    m = re.search(r'\b(199[0-9]|200[0-6])\b', text)
    return int(m.group(1)) if m else 0


def _parse_page(soup, search):
    results = []
    items = (
        soup.select("div.annuncio, article.annuncio, div[class*='listing'], div[class*='card']")
        or soup.select("ul.items li, .annunci-list li")
        or soup.select("div[class*='item']")
    )

    for item in items:
        try:
            link_el = item.select_one("a[href]")
            title_el = item.select_one("h2, h3, .title, [class*='title']")
            price_el = item.select_one(".price, [class*='price'], .prezzo")
            city_el = item.select_one(".location, .city, .zone, [class*='location']")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            price = parse_price(price_el.get_text(strip=True) if price_el else "")
            if not price or price > MAX_PRICE:
                continue

            year = _extract_year(title) or _extract_year(item.get_text())
            if year and not (YEAR_MIN <= year <= YEAR_MAX):
                continue

            url = link_el["href"] if link_el else ""
            if url and not url.startswith("http"):
                url = "https://www.bakeca.it" + url

            city = city_el.get_text(strip=True) if city_el else ""
            lat, lon = geocode_city(city)
            dist = distance_from_bergamo(lat, lon)
            if dist is not None and dist > MAX_DISTANCE_KM:
                continue

            results.append({
                "source": "Bakeca.it",
                "title": title,
                "make": search["make"],
                "model": search["model"],
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
                "label": search["label"],
            })
        except Exception as e:
            print(f"      Bakeca item error: {e}")

    return results


def scrape_subito():
    """Entry point — name kept for compatibility with main.py."""
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)
    seen_urls = set()

    for search in SEARCHES:
        base_url = search["url"]
        if base_url in seen_urls:
            continue
        seen_urls.add(base_url)
        print(f"  Bakeca.it → {search['label']} ({base_url.split('/')[-2] or 'search'})...")

        for page in range(1, 5):
            try:
                url = base_url if page == 1 else f"{base_url}?p={page}"
                resp = session.get(url, timeout=20)
                if resp.status_code == 404:
                    print(f"    404 — skipping this URL")
                    break
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                items = _parse_page(soup, search)
                print(f"    page {page}: {len(items)} listings")
                results.extend(items)
                if len(items) < 5:
                    break
                time.sleep(random.uniform(1, 2))
            except Exception as e:
                print(f"    Bakeca error (page {page}): {e}")
                break

        time.sleep(random.uniform(2, 3))

    return results
