import requests
from bs4 import BeautifulSoup
import time
import random
import json
from datetime import datetime

from utils import make_listing_id, MAX_PRICE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCHES = [
    {"query": "BMW E36",      "make": "BMW",       "model": "E36",   "label": "BMW E36"},
    {"query": "BMW serie 3",  "make": "BMW",       "model": "Serie 3","label": "BMW E36"},
    {"query": "Audi 80",      "make": "Audi",      "model": "80",    "label": "Audi B4/B5"},
    {"query": "Audi A4",      "make": "Audi",      "model": "A4",    "label": "Audi B5"},
    {"query": "Mercedes 190", "make": "Mercedes",  "model": "190E",  "label": "Mercedes 190E"},
]


# ─── PVP — Portale Vendite Pubbliche (Ministero della Giustizia) ─────────────

PVP_SEARCH_URLS = [
    "https://pvp.giustizia.it/pvp/it/ricerca_beni_mobili.wp",
    "https://pvp.giustizia.it/pvp/it/ricerca_all.wp",
    "https://pvp.giustizia.it/pvp/it/homepage.wp",
]


def _scrape_pvp_query(search):
    results = []

    for base_url in PVP_SEARCH_URLS:
        try:
            params = {"search": search["query"], "idCategoria": "2"}
            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=20)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select(".lotto-item, .item-lotto, article.lotto")
                or soup.select("div[class*='lotto'], li[class*='lotto']")
                or soup.select(".annuncio, .bene-mobile")
            )

            if not items:
                print(f"    PVP ({base_url.split('/')[-1]}): nessun selettore trovato")
                continue

            for item in items:
                try:
                    title_el = item.select_one("h2, h3, .titolo, .title")
                    price_el = item.select_one(".prezzo-base, .base-asta, [class*='prezzo']")
                    date_el = item.select_one(".data-asta, [class*='data-asta']")
                    court_el = item.select_one(".tribunale, [class*='tribunale']")
                    lot_el = item.select_one(".numero-lotto, [class*='lotto-n']")
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
                        "make": search["make"], "model": search["model"],
                        "label": search["label"], "title": title,
                        "price_base": price,
                        "auction_date": date_el.get_text(strip=True) if date_el else "",
                        "court": court_el.get_text(strip=True) if court_el else "",
                        "lot": lot_el.get_text(strip=True) if lot_el else "",
                        "url": href,
                        "listing_id": make_listing_id(href, title, price),
                        "found_at": datetime.now().isoformat(),
                    })
                except Exception as e:
                    print(f"      PVP item error: {e}")

            break  # success, stop trying fallback URLs

        except Exception as e:
            print(f"    PVP error ({base_url.split('/')[-1]}): {e}")
            continue

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


# ─── AsteGiudiziarie.it ───────────────────────────────────────────────────────

ASTEG_SEARCH_URLS = [
    "https://www.astegiudiziarie.it/aste",
    "https://www.astegiudiziarie.it/ricerca",
    "https://www.astegiudiziarie.it/beni-mobili",
]


def _scrape_asteg_query(search):
    results = []

    for base_url in ASTEG_SEARCH_URLS:
        try:
            params = {"q": search["query"], "categoria": "autoveicoli"}
            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=20)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            items = (
                soup.select(".asta-card, .lotto-card, article.asta, .item-asta")
                or soup.select("div[class*='asta'], li[class*='asta']")
                or soup.select(".card, .result-item")
            )

            if not items:
                print(f"    AsteGiud ({base_url.split('/')[-1]}): nessun selettore trovato")
                continue

            for item in items:
                try:
                    title_el = item.select_one("h2, h3, .titolo, .title")
                    price_el = item.select_one(".prezzo, .base-asta, [class*='prezzo']")
                    date_el = item.select_one(".data-asta, [class*='data']")
                    court_el = item.select_one(".tribunale, .sede, [class*='tribunale']")
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
                        "make": search["make"], "model": search["model"],
                        "label": search["label"], "title": title,
                        "price_base": price,
                        "auction_date": date_el.get_text(strip=True) if date_el else "",
                        "court": court_el.get_text(strip=True) if court_el else "",
                        "lot": "",
                        "url": href,
                        "listing_id": make_listing_id(href, title, price),
                        "found_at": datetime.now().isoformat(),
                    })
                except Exception as e:
                    print(f"      AsteGiud item error: {e}")

            break

        except Exception as e:
            print(f"    AsteGiud error ({base_url.split('/')[-1]}): {e}")
            continue

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
