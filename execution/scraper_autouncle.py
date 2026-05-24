"""
AutoUncle.it — aggregatore auto usate italiano.
Pesca da più fonti (anche Subito.it indirettamente).
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCHES = [
    {"path": "bmw-serie_3",   "make": "BMW",       "model": "Serie 3", "label": "BMW E36"},
    {"path": "audi-80",        "make": "Audi",      "model": "80",      "label": "Audi B4"},
    {"path": "audi-a4",        "make": "Audi",      "model": "A4",      "label": "Audi B5"},
    {"path": "mercedes_benz-classe_e", "make": "Mercedes", "model": "Classe E", "label": "Mercedes 190E"},
    {"path": "mercedes_benz",  "make": "Mercedes",  "model": "190",     "label": "Mercedes 190E"},
]


def _extract_year(text):
    if not text:
        return 0
    m = re.search(r'\b(199[0-9]|200[0-6])\b', text)
    return int(m.group(1)) if m else 0


def scrape_autouncle():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for search in SEARCHES:
        print(f"  AutoUncle → {search['label']} ({search['path']})...")
        for page in range(1, 4):
            try:
                url = (
                    f"https://www.autouncle.it/it/auto_usate/{search['path']}"
                    f"?s%5Byear_from%5D={YEAR_MIN}&s%5Byear_to%5D={YEAR_MAX}"
                    f"&s%5Bprice_to%5D={MAX_PRICE}"
                    f"&page={page}"
                )
                resp = session.get(url, timeout=20)
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                items = (
                    soup.select("div.car-list-item, article.car-item, div[class*='CarCard']")
                    or soup.select("a[href*='/auto_usate/']")
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
                            url_l = "https://www.autouncle.it" + url_l

                        title_el = item.select_one("h2, h3, [class*='title']")
                        title = title_el.get_text(strip=True) if title_el else text[:80]

                        price_el = item.select_one("[class*='price'], [class*='Price']")
                        price = parse_price(price_el.get_text(strip=True) if price_el else "")
                        if not price:
                            m = re.search(r'(\d{1,2}[\.\s]?\d{3})\s*€', text)
                            if m:
                                price = int(m.group(1).replace(".", "").replace(" ", ""))
                        if not price or price > MAX_PRICE:
                            continue

                        year = _extract_year(title) or _extract_year(text)
                        if year and not (YEAR_MIN <= year <= YEAR_MAX):
                            continue

                        km_el = item.select_one("[class*='km'], [class*='mileage']")
                        km = parse_km(km_el.get_text(strip=True) if km_el else "")

                        city_el = item.select_one("[class*='location'], [class*='city']")
                        city = city_el.get_text(strip=True) if city_el else ""

                        lat, lon = geocode_city(city)
                        dist = distance_from_bergamo(lat, lon)
                        if dist is not None and dist > MAX_DISTANCE_KM:
                            continue

                        results.append({
                            "source": "AutoUncle",
                            "title": title,
                            "make": search["make"], "model": search["model"],
                            "year": year, "price": price, "km": km,
                            "city": city, "distance_km": dist,
                            "condition": "Usato", "url": url_l,
                            "seller": "", "phone": "",
                            "listing_id": make_listing_id(url_l, title, price),
                            "found_at": datetime.now().isoformat(),
                            "label": search["label"],
                        })
                        page_count += 1
                    except Exception as e:
                        print(f"      AutoUncle item error: {e}")

                print(f"    page {page}: {page_count} listings")
                if page_count < 3:
                    break
                time.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"    AutoUncle error (page {page}): {e}")
                break

        time.sleep(random.uniform(2, 3))

    return results
