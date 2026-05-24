import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price, parse_km,
    MAX_DISTANCE_KM, MAX_PRICE, YEAR_MIN, YEAR_MAX,
)

# Mobile.de blocks standard scrapers with 403.
# Using AutoScout24 Germany (autoscout24.de) which is more permissive
# and lists Italian/Swiss/Austrian cars too within EU.

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,it;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.autoscout24.de/",
}

SEARCHES = [
    {"make": "bmw",           "model": "serie-3",  "year_from": YEAR_MIN, "year_to": YEAR_MAX, "label": "BMW E36"},
    {"make": "audi",          "model": "80",        "year_from": YEAR_MIN, "year_to": 1996,     "label": "Audi B4/B5"},
    {"make": "mercedes-benz", "model": "190",       "year_from": YEAR_MIN, "year_to": 1993,     "label": "Mercedes 190E"},
]


def _build_url(search, page):
    # AutoScout24.de — search Italy (cy=I) so listings are near Bergamo
    return (
        f"https://www.autoscout24.de/lst/{search['make']}/{search['model']}"
        f"?atype=C&cy=I&damaged_listing=exclude"
        f"&fregfrom={search['year_from']}&fregto={search['year_to']}"
        f"&priceto={MAX_PRICE}&sort=standard&ustate=N%2CU"
        f"&page={page}"
    )


def scrape_mobile():
    """Scrape AutoScout24.de for additional Italian listings."""
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for search in SEARCHES:
        label = search["label"]
        print(f"  AutoScout24.de → {label}...")

        for page in range(1, 4):
            try:
                url = _build_url(search, page)
                resp = session.get(url, timeout=25)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                import json
                script = soup.find("script", id="__NEXT_DATA__")
                if not script:
                    break

                data = json.loads(script.string)

                def find_list(d, depth=0):
                    if depth > 6 or not isinstance(d, (dict, list)):
                        return []
                    if isinstance(d, list) and d and isinstance(d[0], dict):
                        if any(k in d[0] for k in ["vehicle", "pricing", "price", "url", "guid"]):
                            return d
                    if isinstance(d, dict):
                        for k in ["listings", "ads", "items", "results", "vehicles"]:
                            if k in d:
                                r = find_list(d[k], depth + 1)
                                if r:
                                    return r
                        for v in d.values():
                            r = find_list(v, depth + 1)
                            if r:
                                return r
                    return []

                raw_items = find_list(data)
                page_count = 0

                for item in raw_items:
                    try:
                        vehicle = item.get("vehicle", {}) or {}
                        pricing = item.get("pricing", {}) or {}
                        location = item.get("location", {}) or {}

                        price = int(pricing.get("price", {}).get("raw", 0) or
                                    item.get("price", 0) or 0)
                        if not price or price > MAX_PRICE:
                            continue

                        year = int(vehicle.get("firstRegistrationYear", 0) or 0)
                        if year and not (YEAR_MIN <= year <= YEAR_MAX):
                            continue

                        km = int(vehicle.get("mileage", {}).get("raw", 0) or 0)
                        city = location.get("city", "") or ""
                        lat = location.get("latitude")
                        lon = location.get("longitude")

                        if lat and lon:
                            dist = distance_from_bergamo(float(lat), float(lon))
                        else:
                            lat, lon = geocode_city(city)
                            dist = distance_from_bergamo(lat, lon)

                        if dist is not None and dist > MAX_DISTANCE_KM:
                            continue

                        url_listing = item.get("url", "") or ""
                        if url_listing and not url_listing.startswith("http"):
                            url_listing = "https://www.autoscout24.de" + url_listing

                        make = vehicle.get("make", "") or ""
                        model = vehicle.get("model", "") or ""
                        title = f"{make} {model} {year}".strip()

                        results.append({
                            "source": "AutoScout24.de",
                            "title": title,
                            "make": make,
                            "model": model,
                            "year": year,
                            "price": price,
                            "km": km,
                            "city": city,
                            "distance_km": dist,
                            "condition": "Usato",
                            "url": url_listing,
                            "seller": "",
                            "phone": "",
                            "listing_id": make_listing_id(url_listing, title, price),
                            "found_at": datetime.now().isoformat(),
                            "label": label,
                        })
                        page_count += 1
                    except Exception as e:
                        print(f"      AS24.de item error: {e}")

                print(f"    page {page}: {page_count} valid listings")
                if not raw_items:
                    break

                time.sleep(random.uniform(2, 4))

            except Exception as e:
                print(f"    AS24.de error (page {page}): {e}")
                break

        time.sleep(random.uniform(3, 5))

    return results
