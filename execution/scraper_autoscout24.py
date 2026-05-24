import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, safe_int,
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

SEARCHES = [
    {"make": "bmw",           "year_from": YEAR_MIN, "year_to": YEAR_MAX, "label": "BMW E36"},
    {"make": "audi",          "year_from": YEAR_MIN, "year_to": YEAR_MAX, "label": "Audi B4/B5"},
    {"make": "mercedes-benz", "year_from": YEAR_MIN, "year_to": 1993,     "label": "Mercedes 190E"},
]


def _build_url(search, page):
    return (
        f"https://www.autoscout24.it/lst/{search['make']}"
        f"?atype=C&cy=I&damaged_listing=exclude"
        f"&fregfrom={search['year_from']}&fregto={search['year_to']}"
        f"&priceto={MAX_PRICE}&sort=standard&ustate=N%2CU"
        f"&page={page}"
    )


def _find_listings_recursive(data, depth=0):
    if depth > 6:
        return []
    if isinstance(data, list) and len(data) > 0:
        first = data[0] if data else {}
        if isinstance(first, dict) and any(k in first for k in ["vehicle", "pricing", "prices", "price", "make", "url", "guid", "id"]):
            return data
    if isinstance(data, dict):
        for key in ["listings", "ads", "items", "results", "vehicles", "data", "listingItems", "searchResults"]:
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


def _debug_item(item):
    """Print the structure of the first item to understand AutoScout24's schema."""
    print(f"    [debug] item keys: {list(item.keys())[:12]}")
    for field in ["vehicle", "pricing", "prices", "price", "location", "seller"]:
        if field in item:
            val = item[field]
            if isinstance(val, dict):
                print(f"    [debug] {field}: {dict(list(val.items())[:4])}")
            else:
                print(f"    [debug] {field}: {val}")


def _get_price(item):
    """Extract price trying all known AutoScout24 JSON structures."""
    # pricing.price.raw  (old structure)
    p = item.get("pricing", {})
    v = safe_int(p.get("price", {}).get("raw") if isinstance(p.get("price"), dict) else p.get("price"))
    if v: return v
    v = safe_int(p.get("rawPrice") or p.get("priceRaw"))
    if v: return v

    # prices.public.priceRaw  (new structure)
    pr = item.get("prices", {})
    if isinstance(pr, dict):
        pub = pr.get("public", {}) or pr.get("retail", {}) or {}
        v = safe_int(pub.get("priceRaw") or pub.get("price") or pub.get("raw"))
        if v: return v
        v = safe_int(pr.get("priceRaw") or pr.get("price") or pr.get("raw"))
        if v: return v

    # top-level price
    return safe_int(item.get("price") or item.get("priceRaw") or 0)


def _get_year(item):
    vehicle = item.get("vehicle", {}) or {}
    # vehicle.firstRegistration.year
    fr = vehicle.get("firstRegistration", {})
    if isinstance(fr, dict):
        v = safe_int(fr.get("year"))
        if v: return v
    v = safe_int(vehicle.get("firstRegistrationYear") or vehicle.get("registrationYear"))
    if v: return v
    return safe_int(item.get("firstRegistrationYear") or 0)


def _get_km(item):
    vehicle = item.get("vehicle", {}) or {}
    ml = vehicle.get("mileage", {})
    if isinstance(ml, dict):
        v = safe_int(ml.get("value") or ml.get("raw"))
        if v: return v
    return safe_int(vehicle.get("km") or item.get("mileage") or 0)


def _parse_item_json(item, label, debug=False):
    try:
        if debug:
            _debug_item(item)

        price = _get_price(item)
        if not price or price > MAX_PRICE:
            return None

        year = _get_year(item)
        if year and not (YEAR_MIN <= year <= YEAR_MAX):
            return None

        km = _get_km(item)

        location = item.get("location", {}) or {}
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

        url = item.get("url") or item.get("link") or item.get("detailUrl") or ""
        if url and not url.startswith("http"):
            url = "https://www.autoscout24.it" + url

        vehicle = item.get("vehicle", {}) or {}
        make = vehicle.get("make") or item.get("make") or ""
        model = vehicle.get("model") or item.get("model") or ""
        title = f"{make} {model} {year}".strip()

        seller = item.get("seller", {})
        seller_type = seller.get("type", "") if isinstance(seller, dict) else ""

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
            "seller": seller_type,
            "phone": "",
            "listing_id": make_listing_id(url, title, price),
            "found_at": datetime.now().isoformat(),
            "label": label,
        }
    except Exception as e:
        print(f"      AS24 item error: {e}")
        return None


def _parse_html_fallback(soup, label):
    results = []
    articles = soup.select("article[data-guid], div[data-item-name='listing-article']")
    for art in articles:
        try:
            title_el = art.select_one("h2, h3, [class*='Title'], [class*='title']")
            price_el = art.select_one("[class*='Price'], [class*='price']")
            link_el = art.select_one("a[href*='/offerte-auto/']")
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
            city = city_el.get_text(strip=True) if city_el else ""
            lat, lon = geocode_city(city)
            dist = distance_from_bergamo(lat, lon)
            if dist is not None and dist > MAX_DISTANCE_KM:
                continue
            results.append({
                "source": "AutoScout24", "title": title, "make": label.split()[0],
                "model": "", "year": 0, "price": price, "km": 0, "city": city,
                "distance_km": dist, "condition": "Usato", "url": url,
                "seller": "", "phone": "",
                "listing_id": make_listing_id(url, title, price),
                "found_at": datetime.now().isoformat(), "label": label,
            })
        except Exception:
            pass
    return results


def scrape_autoscout24():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)
    first_run = True

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
                    raw_items = _find_listings_recursive(data)
                    print(f"    page {page}: {len(raw_items)} items in JSON")

                    for i, item in enumerate(raw_items):
                        # Debug the first item of the whole run to understand structure
                        debug = (first_run and i == 0)
                        parsed = _parse_item_json(item, label, debug=debug)
                        if parsed:
                            page_results.append(parsed)
                        if debug:
                            first_run = False
                else:
                    print(f"    page {page}: no __NEXT_DATA__, trying HTML fallback")
                    page_results = _parse_html_fallback(soup, label)

                print(f"    page {page}: {len(page_results)} valid listings")
                results.extend(page_results)

                if not raw_items if script else not page_results:
                    break

                time.sleep(random.uniform(2, 4))

            except Exception as e:
                print(f"    AS24 error (page {page}): {e}")
                break

        time.sleep(random.uniform(3, 5))

    return results
