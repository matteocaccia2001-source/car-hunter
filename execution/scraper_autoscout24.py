import requests
from bs4 import BeautifulSoup
import json
import time
import random
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, safe_int,
    MAX_DISTANCE_KM, TARGETS, passes_target, parse_price, parse_km,
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

def _build_url(target, page):
    return (
        f"https://www.autoscout24.it/lst/{target['as24_slug']}"
        f"?atype=C&cy=I&damaged_listing=exclude"
        f"&fregfrom={target['year_from']}&fregto={target['year_to']}"
        f"&priceto={target['max_price']}&sort=standard&ustate=N%2CU"
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
    """Print FULL structure of first item to understand AutoScout24's schema."""
    print(f"    [debug] item keys: {list(item.keys())[:14]}")
    vehicle = item.get("vehicle", {})
    if isinstance(vehicle, dict):
        print(f"    [debug] vehicle keys: {list(vehicle.keys())}")
    price = item.get("price", {})
    if isinstance(price, dict):
        print(f"    [debug] price keys: {list(price.keys())}")
    for field in ["price", "location"]:
        if field in item:
            val = item[field]
            if isinstance(val, dict):
                print(f"    [debug] {field}: {dict(list(val.items())[:5])}")


def _get_price(item):
    """AS24 stores price as item.price = {priceFormatted: '€ 5.200', ...}"""
    p = item.get("price")
    if isinstance(p, dict):
        # Try raw numeric keys first
        for k in ["priceRaw", "priceValue", "raw", "value", "amount"]:
            v = safe_int(p.get(k))
            if v: return v
        # Fall back to parsing formatted string
        formatted = p.get("priceFormatted") or p.get("formatted") or ""
        return parse_price(formatted)
    return safe_int(p)


def _get_detail(item, icon):
    """vehicleDetails e' una lista di badge:
    [{"data": "05/1999", "iconName": "calendar"}, {"data": "97.900 km", ...}]"""
    for d in item.get("vehicleDetails") or []:
        if isinstance(d, dict) and d.get("iconName") == icon:
            return d.get("data") or ""
    return ""


def _get_year(item):
    """Anno di immatricolazione.

    AutoScout ha spostato il dato fuori da vehicle.*: ora vive in
    tracking.firstRegistration ("05-1999") e nel badge vehicleDetails con
    iconName "calendar" ("05/1999"). Cercarlo solo in vehicle.* restituiva
    0 su ogni annuncio, disattivando di fatto il filtro sugli anni.
    """
    vehicle = item.get("vehicle", {}) or {}
    tracking = item.get("tracking", {}) or {}
    candidates = [
        tracking.get("firstRegistration"),
        _get_detail(item, "calendar"),
        vehicle.get("firstRegistrationDate"),
        vehicle.get("firstRegistration"),
        vehicle.get("firstRegistrationYear"),
        vehicle.get("registrationYear"),
        vehicle.get("year"),
        item.get("firstRegistrationDate"),
        item.get("firstRegistration"),
    ]
    for c in candidates:
        if c is None:
            continue
        if isinstance(c, dict):
            v = safe_int(c.get("year") or c.get("raw") or c.get("value"))
            if 1900 < v < 2100:
                return v
        elif isinstance(c, int):
            if 1900 < c < 2100:
                return c
        elif isinstance(c, str):
            import re
            m = re.search(r'(19[5-9]\d|20\d{2})', c)
            if m:
                return int(m.group(1))
    return 0


def _get_km(item):
    """Chilometri. Il campo attuale e' vehicle.mileageInKm; gli altri sono
    fallback storici piu' il badge vehicleDetails."""
    vehicle = item.get("vehicle", {}) or {}
    v = safe_int(vehicle.get("mileageInKm"))
    if v:
        return v
    ml = vehicle.get("mileage")
    if isinstance(ml, dict):
        for k in ["raw", "value", "km"]:
            v = safe_int(ml.get(k))
            if v: return v
        return parse_km(ml.get("formatted") or ml.get("mileageFormatted") or "")
    v = safe_int(ml or vehicle.get("km") or item.get("mileage") or 0)
    if v:
        return v
    v = safe_int((item.get("tracking") or {}).get("mileage"))
    if v:
        return v
    return parse_km(_get_detail(item, "mileage_odometer"))


def _parse_item_json(item, target, debug=False):
    try:
        if debug:
            _debug_item(item)

        price = _get_price(item)
        year = _get_year(item)
        if not passes_target(year, price, target):
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
            "label": target["label"],
            "target_key": target["key"],
        }
    except Exception as e:
        print(f"      AS24 item error: {e}")
        return None


def _parse_html_fallback(soup, target):
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
            if not price or price > target["max_price"]:
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
                "source": "AutoScout24", "title": title, "make": target["make"],
                "model": "", "year": 0, "price": price, "km": 0, "city": city,
                "distance_km": dist, "condition": "Usato", "url": url,
                "seller": "", "phone": "",
                "listing_id": make_listing_id(url, title, price),
                "found_at": datetime.now().isoformat(),
                "label": target["label"], "target_key": target["key"],
            })
        except Exception:
            pass
    return results


def scrape_autoscout24():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)
    first_run = True

    for target in TARGETS:
        print(f"  AutoScout24 → {target['label']} "
              f"({target['year_from']}-{target['year_to']}, max {target['max_price']}€)...")

        for page in range(1, 6):
            try:
                url = _build_url(target, page)
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
                        parsed = _parse_item_json(item, target, debug=debug)
                        if parsed:
                            page_results.append(parsed)
                        if debug:
                            first_run = False
                else:
                    print(f"    page {page}: no __NEXT_DATA__, trying HTML fallback")
                    page_results = _parse_html_fallback(soup, target)

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
