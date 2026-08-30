"""
AutoScout24.de — copertura supplementare per auto Italiane registrate sul portale tedesco.
Stessa struttura JSON di AutoScout24.it.
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
from datetime import datetime

from utils import (
    geocode_city, distance_from_bergamo, make_listing_id, parse_price, parse_km, safe_int,
    MAX_DISTANCE_KM, TARGETS, passes_target,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,it;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.autoscout24.de/",
}

def _build_url(target, page):
    return (
        f"https://www.autoscout24.de/lst/{target['as24_slug']}"
        f"?atype=C&cy=I&damaged_listing=exclude"
        f"&fregfrom={target['year_from']}&fregto={target['year_to']}"
        f"&priceto={target['max_price']}&sort=standard&ustate=N%2CU"
        f"&page={page}"
    )


def _find_listings(data, depth=0):
    if depth > 6 or not isinstance(data, (dict, list)):
        return []
    if isinstance(data, list) and data and isinstance(data[0], dict):
        if any(k in data[0] for k in ["vehicle", "price", "url", "guid", "id"]):
            return data
    if isinstance(data, dict):
        for k in ["listings", "ads", "items", "results", "vehicles"]:
            if k in data:
                r = _find_listings(data[k], depth + 1)
                if r:
                    return r
        for v in data.values():
            r = _find_listings(v, depth + 1)
            if r:
                return r
    return []


def _get_price(item):
    p = item.get("price")
    if isinstance(p, dict):
        for k in ["priceRaw", "priceValue", "raw", "value"]:
            v = safe_int(p.get(k))
            if v: return v
        return parse_price(p.get("priceFormatted") or "")
    return safe_int(p)


def _get_detail(item, icon):
    for d in item.get("vehicleDetails") or []:
        if isinstance(d, dict) and d.get("iconName") == icon:
            return d.get("data") or ""
    return ""


def _get_year(item):
    """Come su AutoScout24.it: l'anno sta in tracking.firstRegistration e nel
    badge vehicleDetails, non piu' dentro vehicle.*"""
    vehicle = item.get("vehicle", {}) or {}
    tracking = item.get("tracking", {}) or {}
    for c in [tracking.get("firstRegistration"), _get_detail(item, "calendar"),
              vehicle.get("firstRegistrationDate"), vehicle.get("firstRegistration"),
              vehicle.get("firstRegistrationYear"), vehicle.get("year")]:
        if c is None:
            continue
        if isinstance(c, dict):
            v = safe_int(c.get("year") or c.get("raw") or c.get("value"))
            if 1900 < v < 2100:
                return v
        elif isinstance(c, int) and 1900 < c < 2100:
            return c
        elif isinstance(c, str):
            m = re.search(r'(19[5-9]\d|20\d{2})', c)
            if m:
                return int(m.group(1))
    return 0


def _get_km(item):
    vehicle = item.get("vehicle", {}) or {}
    return safe_int(vehicle.get("mileageInKm") or vehicle.get("mileage") or 0)


def scrape_mobile():
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for target in TARGETS:
        print(f"  AutoScout24.de → {target['label']} "
              f"({target['year_from']}-{target['year_to']}, max {target['max_price']}€)...")

        for page in range(1, 4):
            try:
                url = _build_url(target, page)
                resp = session.get(url, timeout=25)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                script = soup.find("script", id="__NEXT_DATA__")

                if not script:
                    break

                data = json.loads(script.string)
                raw_items = _find_listings(data)
                page_count = 0

                for item in raw_items:
                    try:
                        price = _get_price(item)
                        year = _get_year(item)
                        if not passes_target(year, price, target):
                            continue

                        km = _get_km(item)
                        location = item.get("location", {}) or {}
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

                        url_l = item.get("url", "") or ""
                        if url_l and not url_l.startswith("http"):
                            url_l = "https://www.autoscout24.de" + url_l

                        vehicle = item.get("vehicle", {}) or {}
                        make = vehicle.get("make", "")
                        model = vehicle.get("model", "")
                        title = f"{make} {model} {year}".strip()

                        results.append({
                            "source": "AutoScout24.de",
                            "title": title, "make": make, "model": model,
                            "year": year, "price": price, "km": km,
                            "city": city, "distance_km": dist,
                            "condition": "Usato", "url": url_l,
                            "seller": "", "phone": "",
                            "listing_id": make_listing_id(url_l, title, price),
                            "found_at": datetime.now().isoformat(),
                            "label": target["label"],
                            "target_key": target["key"],
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
