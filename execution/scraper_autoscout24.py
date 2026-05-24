import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id,
    MAX_DISTANCE_KM, MAX_PRICE, YEAR_MIN, YEAR_MAX,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.autoscout24.it/",
}

SEARCHES = [
    {"make": "bmw",          "model": "serie-3", "year_from": YEAR_MIN, "year_to": YEAR_MAX, "label": "BMW E36"},
    {"make": "audi",         "model": "80",       "year_from": YEAR_MIN, "year_to": 1996,     "label": "Audi B4/B5"},
    {"make": "audi",         "model": "a4",       "year_from": 1994,     "year_to": YEAR_MAX, "label": "Audi B5"},
    {"make": "mercedes-benz","model": "190",       "year_from": YEAR_MIN, "year_to": 1993,     "label": "Mercedes 190E"},
]


def _build_url(search, page):
    return (
        f"https://www.autoscout24.it/lst/{search['make']}/{search['model']}"
        f"?atype=C&cy=I&damaged_listing=exclude"
        f"&fregfrom={search['year_from']}&fregto={search['year_to']}"
        f"&price_to={MAX_PRICE}&sort=standard&ustate=N%2CU"
        f"&zipcodeCity=Bergamo&zipcodeRadius={MAX_DISTANCE_KM}"
        f"&page={page}"
    )


def _parse_next_data(data, label):
    results = []
    try:
        listings = (
            data.get("props", {})
                .get("pageProps", {})
                .get("listings", [])
        )
        if not listings:
            # fallback path used in some versions
            listings = (
                data.get("props", {})
                    .get("pageProps", {})
                    .get("initialState", {})
                    .get("list", {})
                    .get("items", [])
            )
        for item in listings:
            try:
                vehicle = item.get("vehicle", {})
                pricing = item.get("pricing", {})
                location = item.get("location", {})

                price = pricing.get("price", {}).get("raw", 0) or 0
                if not price or price > MAX_PRICE:
                    continue

                year = vehicle.get("firstRegistrationYear", 0) or 0
                if year and not (YEAR_MIN <= year <= YEAR_MAX):
                    continue

                km = vehicle.get("mileage", {}).get("raw", 0) or 0
                city = location.get("city", "") or ""
                lat = location.get("latitude")
                lon = location.get("longitude")

                if lat and lon:
                    dist = distance_from_bergamo(lat, lon)
                else:
                    lat, lon = geocode_city(city)
                    dist = distance_from_bergamo(lat, lon)

                if dist is not None and dist > MAX_DISTANCE_KM:
                    continue

                url = item.get("url", "") or ""
                if url and not url.startswith("http"):
                    url = "https://www.autoscout24.it" + url

                make = vehicle.get("make", "")
                model = vehicle.get("model", "")
                title = f"{make} {model} {year}".strip()

                results.append({
                    "source": "AutoScout24",
                    "title": title,
                    "make": make,
                    "model": model,
                    "year": year,
                    "price": int(price),
                    "km": int(km),
                    "city": city,
                    "distance_km": dist,
                    "condition": "Usato",
                    "url": url,
                    "seller": item.get("seller", {}).get("type", ""),
                    "phone": "",
                    "listing_id": make_listing_id(url, title, price),
                    "found_at": datetime.now().isoformat(),
                    "label": label,
                })
            except Exception as e:
                print(f"  AS24 item error: {e}")
    except Exception as e:
        print(f"  AS24 parse error: {e}")
    return results


def scrape_autoscout24():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for search in SEARCHES:
        label = search["label"]
        print(f"  AutoScout24 → {label}...")
        for page in range(1, 6):
            try:
                url = _build_url(search, page)
                resp = session.get(url, timeout=20)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                script = soup.find("script", id="__NEXT_DATA__")
                if not script:
                    print(f"    No __NEXT_DATA__ on page {page}")
                    break

                data = json.loads(script.string)
                page_results = _parse_next_data(data, label)

                if not page_results:
                    break

                results.extend(page_results)
                print(f"    page {page}: {len(page_results)} listings")
                time.sleep(random.uniform(2, 4))

            except Exception as e:
                print(f"    AS24 error (page {page}): {e}")
                break

        time.sleep(random.uniform(3, 6))

    return results
