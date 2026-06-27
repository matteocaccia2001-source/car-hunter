"""
Subito.it moto scraper — categoria moto-e-scooter, target Honda CRF 450.
Usa Playwright (gratis) o ScraperAPI come fallback.
"""
import os
import re
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price,
    MAX_DISTANCE_KM,
)

# Filtri specifici moto
MAX_PRICE_MOTO = 3500
YEAR_MIN_MOTO = 2005      # dal 2005 compreso in su

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "").strip()
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

SEARCHES = [
    # 1 sola query per non spammare Subito (rischio IP ban)
    {"query": "crf 450", "make": "Honda", "model": "CRF 450", "label": "Honda CRF 450"},
]


def _extract_year(text):
    if not text:
        return 0
    m = re.search(r'\b(19[89]\d|20[0-2]\d)\b', text)
    return int(m.group(1)) if m else 0


def _fetch_with_playwright(target_url):
    """Browser nuovo per ogni richiesta (stessa config dello scraper auto)."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            locale="it-IT",
            timezone_id="Europe/Rome",
            viewport={"width": 1366, "height": 900},
            extra_http_headers={
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                "Sec-Ch-Ua": '"Google Chrome";v="124", "Chromium";v="124"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
            },
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['it-IT', 'it', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        page = context.new_page()
        page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_selector("article img[src*='sbito.it']", timeout=20000)
        except Exception:
            pass
        html = page.content()
        browser.close()
    return html


def _fetch_via_scraperapi(target_url):
    resp = requests.get(
        "http://api.scraperapi.com",
        params={"api_key": SCRAPER_API_KEY, "url": target_url, "country_code": "it", "render": "false"},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.text


def _fetch(target_url):
    if PLAYWRIGHT_AVAILABLE:
        return _fetch_with_playwright(target_url)
    if SCRAPER_API_KEY:
        return _fetch_via_scraperapi(target_url)
    raise RuntimeError("Né Playwright né SCRAPER_API_KEY disponibili")


def _parse(html, search, debug=False):
    results = []
    soup = BeautifulSoup(html, "html.parser")

    items = soup.select("article[class*='card']") or soup.select("article")

    if debug:
        print(f"      [debug] HTML size: {len(html)} bytes, articles: {len(items)}")
        if items:
            first_text = items[0].get_text(" ", strip=True)[:200]
            print(f"      [debug] first article text: {first_text}")
        title = soup.title.string if soup.title else "?"
        print(f"      [debug] page title: {title}")

    for item in items:
        try:
            text = item.get_text(" ", strip=True)
            if "€" not in text and not re.search(r'\d[\.\s]?\d{3}', text):
                continue

            link_el = item.select_one("a[href*='/vi/'], a[href*='/annunci/'], a[href]")
            url = link_el["href"] if link_el and link_el.has_attr("href") else ""
            if url and not url.startswith("http"):
                url = "https://www.subito.it" + url

            title_el = item.select_one("h2, h3, [class*='item-title'], [class*='title']")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                img = item.select_one("img[alt]")
                title = img["alt"] if img else ""
            if not title:
                continue

            # Filtro permissivo: cerca CRF in tutto il testo della card (titolo + descrizione)
            text_lower = text.lower()
            has_crf = "crf" in text_lower
            has_honda_450 = "honda" in text_lower and "450" in text_lower
            if not (has_crf or has_honda_450):
                continue

            # Prezzo
            price = 0
            price_el = item.select_one("[class*='price'], [class*='Price']")
            if price_el:
                price = parse_price(price_el.get_text(strip=True))
            if not price:
                m = re.search(r'(\d{1,2}[\.\s]?\d{3})\s*€', text)
                if m:
                    price = int(m.group(1).replace(".", "").replace(" ", ""))
            if not price or price > MAX_PRICE_MOTO:
                continue

            # Città + distanza
            city_el = item.select_one("[class*='town'], [class*='city'], [class*='location']")
            city = city_el.get_text(strip=True) if city_el else ""
            lat, lon = geocode_city(city)
            dist = distance_from_bergamo(lat, lon)
            if dist is not None and dist > MAX_DISTANCE_KM:
                continue

            year = _extract_year(title) or _extract_year(text)

            # Filtro anno: minimo 2005. Se anno mancante → escludi (troppo rischioso).
            if year < YEAR_MIN_MOTO:
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
                "vehicle_type": "moto",
            })
        except Exception as e:
            print(f"      Moto item error: {e}")

    return results


def scrape_moto():
    if not PLAYWRIGHT_AVAILABLE and not SCRAPER_API_KEY:
        print("  Moto skipped: né Playwright né SCRAPER_API_KEY")
        return []

    results = []
    seen_q = set()
    first = True
    for search in SEARCHES:
        if search["query"] in seen_q:
            continue
        seen_q.add(search["query"])

        q = search["query"].replace(" ", "+")
        target = (
            f"https://www.subito.it/annunci-italia/vendita/moto-e-scooter/"
            f"?q={q}&ps=0&pe={MAX_PRICE_MOTO}"
        )
        print(f"  Subito.it moto → {search['query']}...")
        try:
            html = _fetch(target)
            items = _parse(html, search, debug=first)
            first = False
            print(f"    {len(items)} listings")
            results.extend(items)
        except Exception as e:
            print(f"    Moto error: {e}")
        time.sleep(random.uniform(2, 4))

    return results
