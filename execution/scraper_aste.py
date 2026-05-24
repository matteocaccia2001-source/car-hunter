import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime

from utils import make_listing_id, MAX_PRICE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

SEARCHES = [
    {"query": "BMW E36",      "make": "BMW",       "model": "E36",   "label": "BMW E36"},
    {"query": "BMW serie 3",  "make": "BMW",       "model": "Serie 3","label": "BMW E36"},
    {"query": "Audi 80",      "make": "Audi",      "model": "80",    "label": "Audi B4/B5"},
    {"query": "Audi A4",      "make": "Audi",      "model": "A4",    "label": "Audi B5"},
    {"query": "Mercedes 190", "make": "Mercedes",  "model": "190E",  "label": "Mercedes 190E"},
]


# ─── PVP — Portale Vendite Pubbliche (Ministero della Giustizia) ─────────────

def _scrape_pvp_query(search):
    results = []
    # PVP usa un form POST per la ricerca beni mobili
    url = "https://pvp.giustizia.it/pvp/it/elenco_lotti.wp"
    params = {"idCategoria": "2", "search": search["query"]}  # cat 2 = veicoli

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = soup.select(".lotto-item, .item-lotto, article.lotto, .annuncio-bene")
        if not items:
            # prova selettori alternativi
            items = soup.select("div[class*='lotto'], li[class*='lotto']")

        for item in items:
            try:
                title_el = item.select_one("h2, h3, .titolo-lotto, .titolo")
                price_el = item.select_one(".prezzo-base, .base-asta, [class*='prezzo']")
                date_el = item.select_one(".data-asta, .data-vendita, [class*='data-asta']")
                court_el = item.select_one(".tribunale, .procedura, [class*='tribunale']")
                lot_el = item.select_one(".numero-lotto, .lotto-num, [class*='lotto-n']")
                link_el = item.select_one("a[href]")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                price_text = price_el.get_text(strip=True) if price_el else ""
                price = int("".join(c for c in price_text if c.isdigit()) or "0")

                href = link_el["href"] if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://pvp.giustizia.it" + href

                results.append({
                    "source": "PVP (Ministero Giustizia)",
                    "make": search["make"],
                    "model": search["model"],
                    "label": search["label"],
                    "title": title,
                    "price_base": price,
                    "auction_date": date_el.get_text(strip=True) if date_el else "",
                    "court": court_el.get_text(strip=True) if court_el else "",
                    "lot": lot_el.get_text(strip=True) if lot_el else "",
                    "url": href,
                    "listing_id": make_listing_id(href, title, price),
                    "found_at": datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"    PVP item error: {e}")

    except Exception as e:
        print(f"  PVP error ('{search['query']}'): {e}")

    return results


def scrape_pvp():
    results = []
    for search in SEARCHES:
        print(f"  PVP → {search['query']}...")
        found = _scrape_pvp_query(search)
        print(f"    {len(found)} lotti")
        results.extend(found)
        time.sleep(random.uniform(2, 4))
    return results


# ─── AsteGiudiziarie.it — aggregatore privato ────────────────────────────────

def _scrape_asteg_query(search):
    results = []
    url = "https://www.astegiudiziarie.it/ricerca-aste"
    params = {"q": search["query"], "categoria": "autoveicoli"}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        items = soup.select(".asta-card, .lotto-card, article.asta, .item-asta")
        if not items:
            items = soup.select("div[class*='asta'], li[class*='asta']")

        for item in items:
            try:
                title_el = item.select_one("h2, h3, .titolo, .title, .asta-titolo")
                price_el = item.select_one(".prezzo, .base-asta, .prezzo-base, [class*='prezzo']")
                date_el = item.select_one(".data-asta, .data, [class*='data']")
                court_el = item.select_one(".tribunale, .procedura, .sede, [class*='tribunale']")
                link_el = item.select_one("a[href]")

                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                price_text = price_el.get_text(strip=True) if price_el else ""
                price = int("".join(c for c in price_text if c.isdigit()) or "0")

                href = link_el["href"] if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.astegiudiziarie.it" + href

                results.append({
                    "source": "AsteGiudiziarie.it",
                    "make": search["make"],
                    "model": search["model"],
                    "label": search["label"],
                    "title": title,
                    "price_base": price,
                    "auction_date": date_el.get_text(strip=True) if date_el else "",
                    "court": court_el.get_text(strip=True) if court_el else "",
                    "lot": "",
                    "url": href,
                    "listing_id": make_listing_id(href, title, price),
                    "found_at": datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"    AsteGiud. item error: {e}")

    except Exception as e:
        print(f"  AsteGiudiziarie.it error ('{search['query']}'): {e}")

    return results


def scrape_astegiudiziarie():
    results = []
    for search in SEARCHES:
        print(f"  AsteGiudiziarie.it → {search['query']}...")
        found = _scrape_asteg_query(search)
        print(f"    {len(found)} lotti")
        results.extend(found)
        time.sleep(random.uniform(2, 4))
    return results


# ─── Entry point ─────────────────────────────────────────────────────────────

def scrape_aste():
    results = []
    results += scrape_pvp()
    results += scrape_astegiudiziarie()
    return results
