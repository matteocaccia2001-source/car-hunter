import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price, parse_km,
    MAX_DISTANCE_KM, MAX_PRICE, YEAR_MIN, YEAR_MAX,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# Mobile.de make/model IDs
SEARCHES = [
    {"make_id": "3500",  "model_id": "16",  "make": "BMW",           "model": "Serie 3 (E36)", "year_from": YEAR_MIN, "year_to": YEAR_MAX, "label": "BMW E36"},
    {"make_id": "1900",  "model_id": "92",  "make": "Audi",          "model": "80",            "year_from": YEAR_MIN, "year_to": 1996,     "label": "Audi B4/B5"},
    {"make_id": "1900",  "model_id": "77",  "make": "Audi",          "model": "A4",            "year_from": 1994,     "year_to": YEAR_MAX, "label": "Audi B5"},
    {"make_id": "17200", "model_id": "19",  "make": "Mercedes-Benz", "model": "190 (W201)",    "year_from": YEAR_MIN, "year_to": 1993,     "label": "Mercedes 190E"},
]


def _build_url(search, page):
    return (
        "https://suchen.mobile.de/fahrzeuge/search.html?"
        "dam=0&isSearchRequest=true"
        f"&makeModelVariant1.makeId={search['make_id']}"
        f"&makeModelVariant1.modelId={search['model_id']}"
        f"&minFirstRegistrationDate={search['year_from']}-01"
        f"&maxFirstRegistrationDate={search['year_to']}-12"
        f"&maxPrice={MAX_PRICE}"
        "&scopeId=C&cn=I"  # Italy
        f"&pageNumber={page}"
    )


def _parse_listing(item, search):
    try:
        title_el = item.select_one("h2.title, h3.title, .headline-block h2, .headline-block h3")
        price_el = item.select_one(".price-block .price-default, .price-primary, [class*='price']")
        location_el = item.select_one(".seller-info, .seller-address, [class*='seller']")
        link_el = item.select_one("a[href]")

        if not title_el or not link_el:
            return None

        title = title_el.get_text(strip=True)
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = parse_price(price_text)

        if not price or price > MAX_PRICE:
            return None

        href = link_el["href"]
        url = href if href.startswith("http") else "https://suchen.mobile.de" + href

        location_text = location_el.get_text(strip=True) if location_el else ""
        lat, lon = geocode_city(location_text)
        dist = distance_from_bergamo(lat, lon)

        if dist is not None and dist > MAX_DISTANCE_KM:
            return None

        return {
            "source": "Mobile.de",
            "title": title,
            "make": search["make"],
            "model": search["model"],
            "year": search["year_from"],
            "price": price,
            "km": 0,
            "city": location_text,
            "distance_km": dist,
            "condition": "Usato",
            "url": url,
            "seller": "",
            "phone": "",
            "listing_id": make_listing_id(url, title, price),
            "found_at": datetime.now().isoformat(),
            "label": search["label"],
        }
    except Exception as e:
        print(f"  Mobile.de item error: {e}")
        return None


def scrape_mobile():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for search in SEARCHES:
        print(f"  Mobile.de → {search['label']}...")
        for page in range(1, 4):
            try:
                url = _build_url(search, page)
                resp = session.get(url, timeout=20)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                items = soup.select("div.result-item, article[data-ad-id], li.result-item")
                if not items:
                    break

                page_count = 0
                for item in items:
                    parsed = _parse_listing(item, search)
                    if parsed:
                        results.append(parsed)
                        page_count += 1

                print(f"    page {page}: {page_count} listings")
                if len(items) < 10:
                    break

                time.sleep(random.uniform(3, 5))

            except Exception as e:
                print(f"    Mobile.de error (page {page}): {e}")
                break

        time.sleep(random.uniform(4, 7))

    return results
