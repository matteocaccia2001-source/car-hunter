"""
Score 1-10 per ogni annuncio.
Base 5.0 + bonus/malus su prezzo, km, distanza, venditore, keyword.

Il punteggio sul prezzo è relativo al tetto del target, non assoluto: una E92
a 7.000€ (tetto 12.000) è un affare, una E36 a 7.000€ (tetto 6.000) è fuori
budget. Con tetto 6.000 le soglie coincidono con quelle originali
(1500/2500/3500/4500/5500).
"""
from utils import TARGETS_BY_KEY

DEFAULT_MAX_PRICE = 6000

# Soglie espresse come frazione del tetto, derivate dalle bande originali su 6.000€.
_PRICE_BANDS = [
    (1500 / DEFAULT_MAX_PRICE, 2.5),
    (2500 / DEFAULT_MAX_PRICE, 1.8),
    (3500 / DEFAULT_MAX_PRICE, 1.2),
    (4500 / DEFAULT_MAX_PRICE, 0.6),
    (5500 / DEFAULT_MAX_PRICE, 0.0),
]

POSITIVE_KEYWORDS = {
    "asi": 1.5,                       # certificata ASI (auto storica)
    "storica": 1.0,
    "iscritta asi": 1.5,
    "tagliand": 0.8,                  # tagliando / tagliandi / tagliandata
    "originale": 0.8,
    "conservat": 1.0,                 # conservata
    "non fumatore": 0.5,
    "garage": 0.5,
    "primo proprietario": 1.2,
    "unico proprietario": 1.2,
    "unica mano": 1.0,
    "perfett": 0.5,                   # perfette/perfetta condizioni
    "ottim": 0.4,                     # ottime condizioni
    "restaurat": 0.8,                 # restaurata / restauro
    "matching numbers": 1.5,
    "tetto apribile": 0.3,
    "manuale": 0.3,                   # cambio manuale (più ricercato)
    "neopatent": 0.3,                 # neopatentati (uscita certa)
    "permuto": 0.3,
}

NEGATIVE_KEYWORDS = {
    "da restaurare": -1.5,
    "incidentata": -2.0,
    "incidente": -1.5,
    "fermo deposito": -1.5,
    "danno": -1.2,
    "sinistro": -1.2,
    "rottame": -2.5,
    "rottamare": -2.5,
    "per ricambi": -2.0,
    "ricambi": -1.5,
    "ferma da anni": -1.5,
    "non marciante": -2.0,
    "non funzionante": -2.0,
    "motore rotto": -2.5,
    "ruggine": -1.0,
    "demolita": -2.5,
    "demolizione": -2.5,
}


def score_listing(listing):
    """Restituisce un float 1.0–10.0."""
    score = 5.0

    # ─── Prezzo (relativo al tetto del target) ─────────
    price = listing.get("price", 0) or 0
    target = TARGETS_BY_KEY.get(listing.get("target_key"))
    cap = target["max_price"] if target else DEFAULT_MAX_PRICE
    if price > 0:
        ratio = price / cap
        for threshold, bonus in _PRICE_BANDS:
            if ratio <= threshold:
                score += bonus
                break
        else:
            score -= 0.5

    # ─── Chilometri ────────────────────────────────────
    km = listing.get("km", 0) or 0
    if km > 0:
        if km < 60000:
            score += 2.0
        elif km < 100000:
            score += 1.0
        elif km < 150000:
            score += 0.3
        elif km < 200000:
            score -= 0.2
        elif km < 280000:
            score -= 0.8
        else:
            score -= 1.5

    # ─── Distanza ──────────────────────────────────────
    dist = listing.get("distance_km")
    if dist is not None:
        if dist < 30:
            score += 1.0
        elif dist < 80:
            score += 0.6
        elif dist < 150:
            score += 0.2
        elif dist > 250:
            score -= 0.4

    # ─── Venditore ─────────────────────────────────────
    seller = (listing.get("seller") or "").lower()
    if any(k in seller for k in ["private", "privato"]):
        score += 0.8

    # ─── Keywords ─────────────────────────────────────
    text = " ".join([
        listing.get("title", ""),
        listing.get("condition", ""),
    ]).lower()

    for kw, weight in POSITIVE_KEYWORDS.items():
        if kw in text:
            score += weight
    for kw, weight in NEGATIVE_KEYWORDS.items():
        if kw in text:
            score += weight  # weight già negativo

    # ─── Clamp 1–10 ────────────────────────────────────
    score = max(1.0, min(10.0, score))
    return round(score, 1)


def score_color(score):
    """Restituisce un dict colore per Google Sheets in base allo score."""
    if score >= 8.0:
        return {"red": 0.72, "green": 0.93, "blue": 0.72}    # verde brillante
    if score >= 6.5:
        return {"red": 0.86, "green": 0.96, "blue": 0.82}    # verde chiaro
    if score >= 5.0:
        return {"red": 1.00, "green": 0.95, "blue": 0.80}    # giallo chiaro
    if score >= 3.5:
        return {"red": 0.99, "green": 0.85, "blue": 0.78}    # arancio chiaro
    return {"red": 0.96, "green": 0.74, "blue": 0.74}        # rosso chiaro
