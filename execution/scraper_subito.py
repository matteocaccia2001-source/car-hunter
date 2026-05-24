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
    """Fetch a URL through ScraperAPI con JS rendering (costa 10 credits/call)."""
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": target_url,
        "country_code": "it",
        "render": "true",  # esegue JS → necessario per Subito.it (skeleton loading)
    }
    resp = requests.get(SCRAPER_API_URL, params=params, timeout=90)
    resp.raise_for_status()
    return resp.text


def _parse_subito(html, search, debug=False):
    results = []
    soup = BeautifulSoup(html, "html.parser")

    # Subito.it 2026: ricerca multipla
    items = (
        soup.select("article[class*='card']")
        or soup.select("article")
    )

    if debug and items:
        # Dump primo article HTML per capire struttura
        first_html = str(items[0])[:1500]
        print(f"      [debug] FIRST ARTICLE HTML (first 1500 chars):\n{first_html}\n")
        print(f"      [debug] FIRST ARTICLE TEXT: {items[0].get_text(' ', strip=True)[:300]}")

    for idx, item in enumerate(items):
        try:
            text = item.get_text(" ", strip=True)
            # Non skippare per €: prova comunque a estrarre dati
            has_price_hint = ("€" in text) or re.search(r'\d[\.\s]?\d{3}', text)
            if not has_price_hint:
                continue

            link_el = item.select_one("a[href*='/vi/'], a[href*='/annunci/'], a[href*='/annuncio/'], a[href]")
            url = link_el["href"] if link_el and link_el.has_attr("href") else ""
            if url and not url.startswith("http"):
                url = "https://www.subito.it" + url

            # Title
            title_el = (
                item.select_one("h2")
                or item.select_one("h3")
                or item.select_one("[class*='item-title']")
                or item.select_one("[class*='title']")
            )
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                # Try alt of image
                img = item.select_one("img[alt]")
                title = img["alt"] if img else ""
            if not title:
                continue

            # Price — element first, regex fallback
            price = 0
            price_el = item.select_one("[class*='price'], [class*='Price']")
            if price_el:
                price = parse_price(price_el.get_text(strip=True))
            if not price:
                m = re.search(r'(\d{1,2}[\.\s]?\d{3})\s*€', text)
                if m:
                    price = int(m.group(1).replace(".", "").replace(" ", ""))
            if not price or price > MAX_PRICE:
                continue

            # Year
            year = _extract_year(title) or _extract_year(text)
            if year and not (YEAR_MIN <= year <= YEAR_MAX):
                continue

            # City
            city_el = item.select_one("[class*='town'], [class*='city'], [class*='location'], [class*='geo']")
            city = city_el.get_text(strip=True) if city_el else ""

            if debug and idx < 2:
                print(f"      [debug item {idx}] title={title[:50]} price={price} year={year} city={city}")

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
        q = search['query'].replace(' ', '+')
        # Filtro prezzo nell'URL → massimizza il signal:noise per ogni call (1 call = 10 credits)
        target = (
            f"https://www.subito.it/annunci-italia/vendita/auto/"
            f"?q={q}&ps={0}&pe={MAX_PRICE}"
        )
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
            items = _parse_subito(html, search, debug=(search == SEARCHES[0]))
            print(f"    {len(items)} listings")
            results.extend(items)
        except Exception as e:
            print(f"    Subito error ('{search['query']}'): {e}")
        time.sleep(random.uniform(1, 2))

    return results
