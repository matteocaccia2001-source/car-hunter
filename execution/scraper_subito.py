"""
Subito.it scraper via Playwright.

Subito.it non blocca gli IP dei data center: rifiuta le richieste che non
arrivano da un browser vero (403 anche da IP residenziale con requests).
Con Chromium headless passa da qualunque IP — verificato su GitHub Actions
(runner 52.160.149.130 → 26 annunci, identici a quelli ottenuti in locale).

Quindi niente ScraperAPI e nessun limite di credits: gira ovunque, gratis.
Se Playwright non è installato → lo scraper si auto-disabilita.

3 query (una per modello target), 1 pagina per query.
"""
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price,
    MAX_DISTANCE_KM, TARGETS, passes_target, YEAR_MIN, YEAR_MAX,
)

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# Subito scrive l'immatricolazione come "01/1995": quel formato è il segnale più
# affidabile, perché un anno nudo può essere il chilometraggio ("2000 Km").
_REG_DATE_RE = re.compile(r'\b\d{1,2}/(\d{4})\b')
_BARE_YEAR_RE = re.compile(r'\b(19\d{2}|20\d{2})\b')


def _extract_year(text):
    """Anno di immatricolazione, limitato all'arco coperto dai target."""
    if not text:
        return 0
    for regex in (_REG_DATE_RE, _BARE_YEAR_RE):
        for m in regex.finditer(text):
            year = int(m.group(1))
            if YEAR_MIN <= year <= YEAR_MAX:
                return year
    return 0


def _fetch_with_playwright(target_url):
    """Browser nuovo per ogni richiesta (la versione che funzionava per auto)."""
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


def _fetch(target_url):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright non disponibile")
    return _fetch_with_playwright(target_url)


def _parse_subito(html, target, debug=False):
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
            # Year
            year = _extract_year(title) or _extract_year(text)
            if not passes_target(year, price, target):
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
                "make": target["make"],
                "model": target["model"],
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
                "label": target["label"],
                "target_key": target["key"],
            })
        except Exception as e:
            print(f"      Subito item error: {e}")

    return results


def scrape_subito():
    if not PLAYWRIGHT_AVAILABLE:
        print("  Subito.it skipped: Playwright non disponibile")
        return []

    print("  Subito.it via Playwright")

    results = []
    first = True
    for target in TARGETS:
        q = target['query'].replace(' ', '+')
        # Filtro prezzo nell'URL → massimizza il signal:noise di ogni pagina
        search_url = (
            f"https://www.subito.it/annunci-italia/vendita/auto/"
            f"?q={q}&ps={0}&pe={target['max_price']}"
        )
        print(f"  Subito.it → {target['query']} "
              f"({target['year_from']}-{target['year_to']}, max {target['max_price']}€)...")
        try:
            html = _fetch(search_url)
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
            items = _parse_subito(html, target, debug=(target is TARGETS[0]))
            print(f"    {len(items)} listings")
            results.extend(items)
        except Exception as e:
            print(f"    Subito error ('{target['query']}'): {e}")
        # Pausa lunga tra query Subito → riduce il rischio di rate-limit/IP ban
        time.sleep(random.uniform(15, 25))

    return results
