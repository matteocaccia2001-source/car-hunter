"""
Subito.it scraper via ScraperAPI.
Subito.it blocca i data center IPs (Azure/GitHub Actions),
quindi instradiamo le richieste via ScraperAPI (free tier: 1.000 chiamate/mese).

Se SCRAPER_API_KEY non è settato → lo scraper si auto-disabilita.

Per minimizzare i credits:
- Solo 3 query (una per modello target)
- 1 pagina per query → 3 chiamate/run → ~360/mese (4 run/giorno × 30)
"""
import os
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

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "").strip()
SCRAPER_API_URL = "http://api.scraperapi.com"

SEARCHES = [
    {"query": "bmw e36",       "label": "BMW E36",       "make": "BMW",      "model": "E36"},
    {"query": "audi 80 a4",    "label": "Audi B4/B5",    "make": "Audi",     "model": "80/A4"},
    {"query": "mercedes 190e", "label": "Mercedes 190E", "make": "Mercedes", "model": "190E"},
]


def _extract_year(text):
    if not text:
        return 0
    m = re.search(r'\b(199[0-9]|200[0-6])\b', text)
    return int(m.group(1)) if m else 0


def _fetch_via_scraperapi(target_url):
    """Fetch a URL through ScraperAPI's residential proxies (Italian IPs)."""
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": target_url,
        "country_code": "it",  # IT residential proxy
    }
    resp = requests.get(SCRAPER_API_URL, params=params, timeout=70)
    resp.raise_for_status()
    return resp.text


def _parse_subito(html, search):
    results = []
    soup = BeautifulSoup(html, "html.parser")

    # Multiple selectors — Subito.it changes class names periodically
    items = (
        soup.select("div[class*='item-card']")
        or soup.select("article[class*='item']")
        or soup.select("div.items--wrap > div > div")
    )

    if not items:
        # Fallback: any link to an /annuncio/
        anchors = soup.select("a[href*='/annunci/'], a[href*='/vi/']")
        items = list({a.find_parent("article") or a.find_parent("div") for a in anchors})
        items = [x for x in items if x is not None]

    for item in items:
        try:
            link_el = item.select_one("a[href*='/annunci/'], a[href*='/vi/'], a[href]")
            title_el = item.select_one("h2, h3, [class*='item-title'], [class*='title']")
            price_el = item.select_one("[class*='price'], [class*='prezzo']")
            city_el = item.select_one("[class*='town'], [class*='city'], [class*='location']")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            price = parse_price(price_el.get_text(strip=True) if price_el else "")
            if not price or price > MAX_PRICE:
                continue

            year = _extract_year(title) or _extract_year(item.get_text())
            if year and not (YEAR_MIN <= year <= YEAR_MAX):
                continue

            url = link_el["href"] if link_el and link_el.has_attr("href") else ""
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
            print(f"      Subito item error: {e}")

    return results


def scrape_subito():
    if not SCRAPER_API_KEY:
        print("  Subito.it skipped: SCRAPER_API_KEY non configurato")
        return []

    results = []
    first = True
    for search in SEARCHES:
        target = f"https://www.subito.it/annunci-italia/vendita/auto/?q={search['query'].replace(' ', '+')}"
        print(f"  Subito.it (via ScraperAPI) → {search['query']}...")
        try:
            html = _fetch_via_scraperapi(target)
            if first:
                # Debug: scan available selectors to understand current Subito.it HTML
                soup = BeautifulSoup(html, "html.parser")
                print(f"    [debug] HTML size: {len(html)} bytes")
                print(f"    [debug] page title: {soup.title.string if soup.title else 'N/A'}")
                # Try to find ANY listing-like container
                for sel in ["div[class*='item-card']", "article", "div[class*='ad']",
                            "div[class*='listing']", "div[class*='SmallCard']",
                            "a[href*='/annunci/']", "a[href*='/vi/']"]:
                    found = soup.select(sel)
                    if found:
                        print(f"    [debug] selector '{sel}' → {len(found)} matches")
                        # Print first match's classes
                        if found[0].get("class"):
                            print(f"    [debug]   first match classes: {found[0]['class']}")
                first = False
            items = _parse_subito(html, search)
            print(f"    {len(items)} listings")
            results.extend(items)
        except Exception as e:
            print(f"    Subito error ('{search['query']}'): {e}")
        time.sleep(random.uniform(1, 2))

    return results
