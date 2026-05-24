import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id,
    MAX_DISTANCE_KM, MAX_PRICE, YEAR_MIN, YEAR_MAX, parse_price, parse_km,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.autoscout24.it/",
    "DNT": "1",
}

# Search by make only (no model slug) — more reliable, filter E36/B5/W201 in Python
SEARCHES = [
    {"make": "bmw",           "year_from": YEAR_MIN, "year_to": YEAR_MAX, "label": "BMW E36",       "keywords": ["e36", "serie 3", "316", "318", "320", "323", "325", "328"]},
    {"make": "audi",          "year_from": YEAR_MIN, "year_to": YEAR_MAX, "label": "Audi B4/B5",    "keywords": ["80", "a4", "b4", "b5", "1.8", "1.9", "2.0", "2.6"]},
    {"make": "mercedes-benz", "year_from": YEAR_MIN, "year_to": 1993,     "label": "Mercedes 190E", "keywords": ["190", "w201", "1.8", "2.0", "2.3", "2.5", "2.6"]},
]


def _build_url(search, page):
    # Search all Italy (no location filter — filter by distance in Python)
    return (
        f"https://www.autoscout24.it/lst/{search['make']}"
        f"?atype=C&cy=I&damaged_listing=exclude"
        f"&fregfrom={search['year_from']}&fregto={search['year_to']}"
        f"&priceto={MAX_PRICE}&sort=standard&ustate=N%2CU"
        f"&page={page}"
    )


def _find_listings_recursive(data, depth=0):
    """Recursively search the NEXT_DATA JSON for a listings array."""
    if depth > 6:
        return []
    if isinstance(data, list) and len(data) > 0:
        first = data[0] if data else {}
        if isinstance(first, dict) and any(k in first for k in ["vehicle", "pricing", "price", "make", "url", "guid"]):
            return data
    if isinstance(data, dict):
        for key in ["listings", "ads", "items", "results", "vehicles", "data", "listingItems"]:
            if key in data and isinstance(data[key], (list, dict)):
                found = _find_listings_recursive(data[key], depth + 1)
                if found:
                    return found
        for value in data.values():
            if isinstance(value, (dict, list)):
                found = _find_listings_recursive(value, depth + 1)
                if found:
                    return found
    return []


def _parse_item_json(item, label):
    try:
        vehicle = item.get("vehicle", {}) or {}
        pricing = item.get("pricing", {}) or {}
        location = item.get("location", {}) or {}

        # Try multiple price paths
        price = (
            pricing.get("price", {}).get("raw")
            or pricing.get("rawPrice")
            or item.get("price")
            or 0
        )
        price = int(price) if price else 0
        if not price or price > MAX_PRICE:
            return None

        year = (
            vehicle.get("firstRegistrationYear")
            or vehicle.get("registrationYear")
            or item.get("firstRegistrationYear")
            or 0
        )
        year = int(year) if year else 0
        if year and not (YEAR_MIN <= year <= YEAR_MAX):
            return None

        km = (
            vehicle.get("mileage", {}).get("raw")
            or vehicle.get("km")
            or item.get("mileage")
            or 0
        )
        km = int(km) if km else 0

        city = location.get("city") or location.get("town") or item.get("city") or ""
        lat = location.get("latitude") or location.get("lat")
        lon = location.get("longitude") or location.get("lon")

        if lat and lon:
            dist = distance_from_bergamo(float(lat), float(lon))
        else:
            lat, lon = geocode_city(city)
            dist = distance_from_bergamo(lat, lon)

        if dist is not None and dist > MAX_DISTANCE_KM:
            return None

        url = item.get("url") or item.get("link") or ""
        if url and not url.startswith("http"):
            url = "https://www.autoscout24.it" + url

        make = vehicle.get("make") or item.get("make") or ""
        model = vehicle.get("model") or item.get("model") or ""
        title = f"{make} {model} {year}".strip()

        return {
            "source": "AutoScout24",
            "title": title,
            "make": make,
            "model": model,
            "year": year,
            "price": price,
            "km": km,
            "city": city,
            "distance_km": dist,
            "condition": "Usato",
            "url": url,
            "seller": item.get("seller", {}).get("type", "") if isinstance(item.get("seller"), dict) else "",
            "phone": "",
            "listing_id": make_listing_id(url, title, price),
            "found_at": datetime.now().isoformat(),
            "label": label,
        }
    except Exception as e:
        print(f"      AS24 json item error: {e}")
        return None


def _parse_html_fallback(soup, label):
    """Fallback: parse AS24 article elements directly from HTML."""
    results = []
    articles = soup.select("article[data-guid], div[data-item-name='listing-article']")
    for art in articles:
        try:
            title_el = art.select_one("h2, h3, [class*='Title'], [class*='title']")
            price_el = art.select_one("[class*='Price'], [class*='price']")
            link_el = art.select_one("a[href*='/offerte-auto/']")
            km_el = art.select_one("[class*='Mileage'], [class*='mileage']")
            year_el = art.select_one("[class*='FirstRegistration'], [class*='registration']")
            city_el = art.select_one("[class*='Location'], [class*='location'], [class*='city']")

            if not title_el or not price_el:
                continue

            title = title_el.get_text(strip=True)
            price = parse_price(price_el.get_text(strip=True))
            if not price or price > MAX_PRICE:
                continue

            url = link_el["href"] if link_el else ""
            if url and not url.startswith("http"):
                url = "https://www.autoscout24.it" + url

            year = parse_price(year_el.get_text(strip=True)) if year_el else 0
            if year and not (YEAR_MIN <= year <= YEAR_MAX):
                continue

            km = parse_km(km_el.get_text(strip=True)) if km_el else 0
            city = city_el.get_text(strip=True) if city_el else ""

            lat, lon = geocode_city(city)
            dist = distance_from_bergamo(lat, lon)
            if dist is not None and dist > MAX_DISTANCE_KM:
                continue

            results.append({
                "source": "AutoScout24",
                "title": title,
                "make": label.split()[0],
                "model": "",
                "year": year,
                "price": price,
                "km": km,
                "city": city,
                "distance_km": dist,
                "condition": "Usato",
                "url": url,
                "seller": "",
                "phone": "",
                "listing_id": make_listing_id(url, title, price),
                "found_at": datetime.now().isoformat(),
                "label": label,
            })
        except Exception as e:
            print(f"      AS24 html item error: {e}")
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
                resp = session.get(url, timeout=25)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                script = soup.find("script", id="__NEXT_DATA__")

                page_results = []

                if script:
                    data = json.loads(script.string)
                    # Debug: print structure on first page of first search
                    if page == 1 and search == SEARCHES[0]:
                        try:
                            pp = data.get("props", {}).get("pageProps", {})
                            print(f"    [debug] pageProps keys: {list(pp.keys())[:8]}")
                        except Exception:
                            pass

                    raw_items = _find_listings_recursive(data)
                    print(f"    [debug] JSON items found: {len(raw_items)}")

                    for item in raw_items:
                        parsed = _parse_item_json(item, label)
                        if parsed:
                            page_results.append(parsed)
                else:
                    print(f"    No __NEXT_DATA__ — trying HTML fallback")
                    page_results = _parse_html_fallback(soup, label)

                print(f"    page {page}: {len(page_results)} valid listings")
                results.extend(page_results)

                if not page_results:
                    break

                time.sleep(random.uniform(2, 4))

            except Exception as e:
                print(f"    AS24 error (page {page}): {e}")
                break

        time.sleep(random.uniform(3, 5))

    return results
