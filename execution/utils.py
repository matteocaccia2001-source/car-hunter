import math
import hashlib
import time
import requests

BERGAMO_LAT = 45.6983
BERGAMO_LON = 9.6773
MAX_DISTANCE_KM = 300

# ─── TARGET ────────────────────────────────────────────────────────────────
# Unica fonte di verità per i modelli cercati. Ogni target porta la propria
# finestra di produzione e il proprio tetto di prezzo: un filtro globale non
# può funzionare, perché E36 (1990-2000) ed E92 (2006-2013) non si sovrappongono.
#
#   as24_slug → percorso AutoScout24 (.it e .de usano gli stessi slug)
#   query     → testo per i siti che cercano per stringa (Subito, aste)
#
# Nota: su AutoScout E36, E46 ed E92 condividono lo slug "serie-3" — a
# distinguerli è solo la finestra anni. Gli anni che si sovrappongono
# producono doppioni, che la deduplica per listing_id assorbe.
TARGETS = [
    {
        "key": "E36", "label": "BMW E36", "make": "BMW", "model": "Serie 3 E36",
        "as24_slug": "bmw/serie-3", "query": "bmw e36",
        "year_from": 1990, "year_to": 2000, "max_price": 6000,
    },
    {
        "key": "E46", "label": "BMW E46", "make": "BMW", "model": "Serie 3 E46",
        "as24_slug": "bmw/serie-3", "query": "bmw e46",
        "year_from": 1998, "year_to": 2006, "max_price": 8000,
    },
    {
        "key": "E92", "label": "BMW E92", "make": "BMW", "model": "Serie 3 E92",
        "as24_slug": "bmw/serie-3", "query": "bmw e92",
        "year_from": 2006, "year_to": 2013, "max_price": 12000,
    },
    {
        "key": "B5", "label": "Audi A4 B5", "make": "Audi", "model": "A4 B5",
        "as24_slug": "audi/a4", "query": "audi a4 b5",
        "year_from": 1994, "year_to": 2001, "max_price": 6000,
    },
    {
        "key": "190E", "label": "Mercedes 190E", "make": "Mercedes", "model": "190E W201",
        "as24_slug": "mercedes-benz/190", "query": "mercedes 190e",
        "year_from": 1991, "year_to": 1993, "max_price": 6000,
    },
]

TARGETS_BY_KEY = {t["key"]: t for t in TARGETS}

# Estremi complessivi: servono dove un solo valore deve coprire tutti i target
# (filtro grezzo nell'URL, regex sugli anni). Il controllo fine è per target.
MAX_PRICE = max(t["max_price"] for t in TARGETS)
YEAR_MIN = min(t["year_from"] for t in TARGETS)
YEAR_MAX = max(t["year_to"] for t in TARGETS)


def passes_target(year, price, target):
    """Vero se anno e prezzo rientrano nella finestra del target."""
    if not price or price <= 0 or price > target["max_price"]:
        return False
    if year and not (target["year_from"] <= year <= target["year_to"]):
        return False
    return True

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


def safe_int(val, dict_keys=("raw", "value", "priceRaw", "amount", "price", "year")):
    """Convert int/float/str/dict to int safely — handles AutoScout24's nested dicts."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        digits = "".join(c for c in val if c.isdigit())
        return int(digits) if digits else 0
    if isinstance(val, dict):
        for k in dict_keys:
            if k in val:
                return safe_int(val[k], dict_keys)
    return 0
