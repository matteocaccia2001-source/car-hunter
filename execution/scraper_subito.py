import requests
import time
import random
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price, parse_km,
    MAX_DISTANCE_KM, MAX_PRICE, YEAR_MIN, YEAR_MAX, BERGAMO_LAT, BERGAMO_LON,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "it-IT,it;q=0.9",
}

SEARCHES = [
    {"query": "bmw e36",       "label": "BMW E36",       "make": "BMW",       "model": "E36"},
    {"query": "bmw serie 3",   "label": "BMW E36",       "make": "BMW",       "model": "Serie 3"},
    {"query": "audi 80",       "label": "Audi B4/B5",    "make": "Audi",      "model": "80"},
    {"query": "audi a4 1994",  "label": "Audi B5",       "make": "Audi",      "model": "A4"},
    {"query": "mercedes 190e", "label": "Mercedes 190E", "make": "Mercedes",  "model": "190E"},
    {"query": "mercedes w201", "label": "Mercedes 190E", "make": "Mercedes",  "model": "190E"},
]


def _fetch_page(query, start=0):
    params = {
        "c": "2",
        "t": "s",
        "q": query,
        "lim": "100",
        "start": str(start),
        "geo_radius": str(MAX_DISTANCE_KM),
        "lat": str(BERGAMO_LAT),
        "lon": str(BERGAMO_LON),
    }
    resp = requests.get(
        "https://api.subito.it/sbt/v1/search/items/",
        params=params,
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_item(item, label):
    try:
        prices = item.get("prices", [])
        price_raw = prices[0].get("value", "0") if prices else "0"
        price = parse_price(price_raw)
        if not price or price > MAX_PRICE:
            return None

        features = {}
        for f in item.get("features", []):
            vals = f.get("values", [])
            if vals:
                features[f.get("uri", "")] = vals[0].get("key", "")

        year = int(features.get("/anno", 0) or 0)
        if year and not (YEAR_MIN <= year <= YEAR_MAX):
            return None

        km = parse_km(features.get("/chilometraggio", "0") or "0")

        geo = item.get("geo", {})
        lat = geo.get("lat")
        lon = geo.get("lon")
        locations = item.get("locations", [])
        city = locations[0].get("value", "") if locations else ""

        if lat and lon:
            dist = distance_from_bergamo(float(lat), float(lon))
        else:
            lat, lon = geocode_city(city)
            dist = distance_from_bergamo(lat, lon)

        if dist is not None and dist > MAX_DISTANCE_KM:
            return None

        urls = item.get("urls", {})
        url = urls.get("default", "") or urls.get("desktop", "")
        title = item.get("subject", "")
        advertiser = item.get("advertiser", {})

        return {
            "source": "Subito.it",
            "title": title,
            "make": label.split()[0],
            "model": label.split()[-1] if len(label.split()) > 1 else "",
            "year": year,
            "price": price,
            "km": km,
            "city": city,
            "distance_km": dist,
            "condition": features.get("/condizioni", "Usato"),
            "url": url,
            "seller": advertiser.get("name", ""),
            "phone": advertiser.get("phone", ""),
            "listing_id": make_listing_id(url, title, price),
            "found_at": datetime.now().isoformat(),
            "label": label,
        }
    except Exception as e:
        print(f"  Subito item parse error: {e}")
        return None


def _scrape_query(query, label):
    results = []
    start = 0
    while True:
        try:
            data = _fetch_page(query, start)
            items = data.get("ads", [])
            if not items:
                break
            for item in items:
                parsed = _parse_item(item, label)
                if parsed:
                    results.append(parsed)
            if len(items) < 100:
                break
            start += 100
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            print(f"  Subito.it error ('{query}'): {e}")
            break
    return results


def scrape_subito():
    results = []
    seen_labels = set()
    for search in SEARCHES:
        label = search["label"]
        print(f"  Subito.it → {search['query']}...")
        found = _scrape_query(search["query"], label)
        results.extend(found)
        print(f"    {len(found)} listings")
        time.sleep(random.uniform(2, 3))
    return results
