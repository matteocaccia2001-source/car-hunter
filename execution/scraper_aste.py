"""
Aste giudiziarie e telematiche italiane.
Portali coperti automaticamente:
- AstaTelematica.it (relativamente scrapable)
- Gobid.it (aste judicial private)
- PVP + AsteGiudiziarie.it (best effort — spesso vuoti perché usano JS/POST)

Per ricerca manuale: vedi foglio "🔖 Bookmarks" nel Google Sheet.
"""
import requests
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime

from utils import make_listing_id

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Le aste non hanno filtro di anno né di modello preciso (spesso il lotto non li
# indica), quindi qui si cerca per testo. "BMW serie 3" fa da rete larga su E36/E46/E92.
SEARCHES = [
    {"query": "BMW E36",      "make": "BMW",       "model": "Serie 3 E36", "label": "BMW E36"},
    {"query": "BMW E46",      "make": "BMW",       "model": "Serie 3 E46", "label": "BMW E46"},
    {"query": "BMW E92",      "make": "BMW",       "model": "Serie 3 E92", "label": "BMW E92"},
    {"query": "BMW serie 3",  "make": "BMW",       "model": "Serie 3",     "label": "BMW Serie 3"},
    {"query": "Audi A4",      "make": "Audi",      "model": "A4 B5",       "label": "Audi A4 B5"},
    {"query": "Mercedes 190", "make": "Mercedes",  "model": "190E W201",   "label": "Mercedes 190E"},
]


# ─── AstaTelematica.it ───────────────────────────────────────────────────────

def _scrape_astatelematica_query(search):
    results = []
    try:
        url = f"https://www.astetelematiche.it/ricerca?q={search['query'].replace(' ', '+')}&categoria=autoveicoli"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            # Try alternate URL
            url = f"https://procedure.astetelematiche.it/aste/Lista?ricerca={search['query'].replace(' ', '+')}"
            resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            return results
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = (
            soup.select(".lotto, .asta-item, article[class*='lot'], div[class*='asta']")
            or soup.select("tr[class*='lot'], li[class*='asta']")
        )

        for item in items:
            try:
                title_el = item.select_one("h2, h3, .titolo, [class*='title']")
                price_el = item.select_one(".prezzo, .base, [class*='price'], [class*='prezzo']")
                date_el = item.select_one(".data-asta, [class*='data']")
                court_el = item.select_one(".tribunale, [class*='tribunale']")
                link_el = item.select_one("a[href]")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                price_text = price_el.get_text(strip=True) if price_el else ""
                price = int("".join(c for c in price_text if c.isdigit()) or "0")
                href = link_el["href"] if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.astetelematiche.it" + href

                results.append({
                    "source": "AstaTelematica.it",
                    "make": search["make"], "model": search["model"],
                    "label": search["label"], "title": title,
                    "price_base": price,
                    "auction_date": date_el.get_text(strip=True) if date_el else "",
                    "court": court_el.get_text(strip=True) if court_el else "",
                    "lot": "", "url": href,
                    "listing_id": make_listing_id(href, title, price),
                    "found_at": datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"      AstaTel item error: {e}")

    except Exception as e:
        print(f"    AstaTelematica error: {e}")

    return results


def scrape_astatelematica():
    results = []
    for search in SEARCHES:
        print(f"  AstaTelematica → {search['query']}...")
        found = _scrape_astatelematica_query(search)
        print(f"    {len(found)} lotti")
        results.extend(found)
        time.sleep(random.uniform(2, 3))
    return results


# ─── Gobid.it ────────────────────────────────────────────────────────────────

def _scrape_gobid_query(search):
    results = []
    try:
        url = f"https://www.gobid.it/it/ricerca?q={search['query'].replace(' ', '+')}"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            return results
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = (
            soup.select(".asta-card, .lot-card, article[class*='lot'], div[class*='auction']")
            or soup.select("a[href*='/asta/']")
        )

        for item in items:
            try:
                text = item.get_text(" ", strip=True)
                title_el = item.select_one("h2, h3, [class*='title']")
                price_el = item.select_one("[class*='price'], [class*='base']")
                link_el = item.select_one("a[href]") if item.name != "a" else item

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                price = 0
                if price_el:
                    price = int("".join(c for c in price_el.get_text() if c.isdigit()) or "0")
                if not price:
                    m = re.search(r'€\s?(\d{1,2}[\.\s]?\d{3})', text)
                    if m:
                        price = int(m.group(1).replace(".", "").replace(" ", ""))

                href = link_el["href"] if link_el and link_el.has_attr("href") else ""
                if href and not href.startswith("http"):
                    href = "https://www.gobid.it" + href

                results.append({
                    "source": "Gobid.it",
                    "make": search["make"], "model": search["model"],
                    "label": search["label"], "title": title,
                    "price_base": price,
                    "auction_date": "", "court": "",
                    "lot": "", "url": href,
                    "listing_id": make_listing_id(href, title, price),
                    "found_at": datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"      Gobid item error: {e}")

    except Exception as e:
        print(f"    Gobid error: {e}")

    return results


def scrape_gobid():
    results = []
    for search in SEARCHES:
        print(f"  Gobid → {search['query']}...")
        found = _scrape_gobid_query(search)
        print(f"    {len(found)} lotti")
        results.extend(found)
        time.sleep(random.uniform(2, 3))
    return results


# ─── Entry point ─────────────────────────────────────────────────────────────

def scrape_aste():
    results = []
    print("  → AstaTelematica.it")
    results += scrape_astatelematica()
    return results
