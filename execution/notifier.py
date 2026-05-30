"""
WhatsApp notifier via CallMeBot (gratis, illimitato per uso personale).
Invia un messaggio sul TUO WhatsApp per ogni annuncio con score >= MIN_SCORE.

Setup:
1. Aggiungi in rubrica il numero: +34 644 51 95 23
2. Apri WhatsApp → manda al numero esattamente: "I allow callmebot to send me messages"
3. Aspetta la risposta con la tua API key
4. Aggiungi al file .env:
     WHATSAPP_PHONE=+393xxxxxxxxx
     WHATSAPP_API_KEY=la_chiave_ricevuta
"""
import os
import time
import requests

PHONE = os.environ.get("WHATSAPP_PHONE", "").strip()
API_KEY = os.environ.get("WHATSAPP_API_KEY", "").strip()
MIN_SCORE = 7.0


def can_notify():
    return bool(PHONE and API_KEY)


def _send(message):
    """Invia un messaggio via CallMeBot. Restituisce True se OK."""
    try:
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": PHONE, "text": message, "apikey": API_KEY},
            timeout=20,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"  WhatsApp send error: {e}")
        return False


def _format_listing(listing):
    score = listing.get("score", 0)
    title = (listing.get("title") or "")[:70]
    price = listing.get("price", 0)
    year = listing.get("year") or "?"
    km = listing.get("km", 0)
    km_str = f"{km:,}".replace(",", ".") if km else "n/d"
    city = listing.get("city", "")
    dist = listing.get("distance_km")
    dist_str = f"{dist:.0f} km da Bg" if dist is not None else ""
    source = listing.get("source", "")
    url = listing.get("url", "")

    return (
        f"🚗 SCORE {score} - {source}\n"
        f"{title}\n"
        f"💶 {price:,} € | 📅 {year} | 🛣 {km_str} km\n".replace(",", ".")
        + f"📍 {city} ({dist_str})\n"
        f"🔗 {url}"
    )


def notify_high_score_listings(listings, min_score=MIN_SCORE):
    """Manda una notifica WhatsApp per ogni listing con score >= min_score."""
    if not can_notify():
        return 0
    sent = 0
    for listing in listings:
        if (listing.get("score") or 0) >= min_score:
            msg = _format_listing(listing)
            if _send(msg):
                sent += 1
                # CallMeBot rate limit: max 1 msg/sec
                time.sleep(7)
    return sent
