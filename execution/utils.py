import math
import hashlib
import time
import requests

BERGAMO_LAT = 45.6983
BERGAMO_LON = 9.6773
MAX_DISTANCE_KM = 150
MAX_PRICE = 6000
YEAR_MIN = 1991
YEAR_MAX = 1996

_city_cache = {}


def haversine(lat1, lon1, lat2=BERGAMO_LAT, lon2=BERGAMO_LON):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def geocode_city(city_name):
    if not city_name:
        return None, None
    key = city_name.strip().lower()
    if key in _city_cache:
        return _city_cache[key]
    try:
        time.sleep(1.1)
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city_name + ", Italy", "format": "json", "limit": 1},
            headers={"User-Agent": "CarHunter/1.0"},
            timeout=10,
        )
        data = resp.json()
        if data:
            result = (float(data[0]["lat"]), float(data[0]["lon"]))
            _city_cache[key] = result
            return result
    except Exception as e:
        print(f"  Geocoding error '{city_name}': {e}")
    _city_cache[key] = (None, None)
    return None, None


def distance_from_bergamo(lat, lon):
    if lat is None or lon is None:
        return None
    return round(haversine(float(lat), float(lon)), 1)


def make_listing_id(url, title, price):
    raw = f"{url}|{title}|{price}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def parse_price(text):
    if not text:
        return 0
    digits = "".join(c for c in str(text) if c.isdigit())
    return int(digits) if digits else 0


def parse_km(text):
    if not text:
        return 0
    digits = "".join(c for c in str(text) if c.isdigit())
    return int(digits) if digits else 0
