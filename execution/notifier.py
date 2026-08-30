"""
Notifiche push per gli annunci con score alto.

Due canali, scelti in base a cosa e' configurato:

1. Telegram (consigliato) — gratis e senza quote.
     TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
   Setup: scrivi a @BotFather -> /newbot -> ricevi il token; poi scrivi un
   messaggio al tuo bot e leggi il chat_id da
   https://api.telegram.org/bot<TOKEN>/getUpdates

2. CallMeBot / WhatsApp — fallback storico. ATTENZIONE: il piano gratuito ha
     un tetto di messaggi. Esaurito il credito l'API risponde comunque HTTP 200
     con "Message not sent" nel corpo, quindi il codice DEVE leggere il corpo:
     fidarsi dello status code faceva contare come inviati messaggi mai partiti.
     WHATSAPP_PHONE, WHATSAPP_API_KEY
"""
import os
import re
import html
import time
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
PHONE = os.environ.get("WHATSAPP_PHONE", "").strip()
API_KEY = os.environ.get("WHATSAPP_API_KEY", "").strip()

MIN_SCORE = 7.0


def _telegram_ready():
    return bool(TELEGRAM_TOKEN and TELEGRAM_CHAT)


def _whatsapp_ready():
    return bool(PHONE and API_KEY)


def can_notify():
    return _telegram_ready() or _whatsapp_ready()


def channel_name():
    if _telegram_ready():
        return "Telegram"
    if _whatsapp_ready():
        return "WhatsApp (CallMeBot)"
    return "nessuno"


def _strip_html(text):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()


def _send_telegram(message):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": message,
                  "disable_web_page_preview": False},
            timeout=20,
        )
        data = resp.json()
        if data.get("ok"):
            return True, ""
        return False, str(data.get("description") or resp.text)[:200]
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _send_whatsapp(message):
    """CallMeBot risponde 200 anche in caso di errore: il verdetto e' nel corpo."""
    try:
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": PHONE, "text": message, "apikey": API_KEY},
            timeout=20,
        )
        body = _strip_html(resp.text)
        low = body.lower()
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        if "not sent" in low or "messages left" in low or "invalid" in low:
            return False, body[:200]
        if "queued" in low or "sent" in low:
            return True, ""
        return False, body[:200] or "risposta non riconosciuta"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _send(message):
    """Restituisce (ok, dettaglio_errore)."""
    if _telegram_ready():
        return _send_telegram(message)
    if _whatsapp_ready():
        return _send_whatsapp(message)
    return False, "nessun canale configurato"


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
    label = listing.get("label", "")
    url = listing.get("url", "")
    price_str = f"{price:,}".replace(",", ".")

    return (
        f"🚗 SCORE {score} - {label} ({source})\n"
        f"{title}\n"
        f"💶 {price_str} € | 📅 {year} | 🛣 {km_str} km\n"
        f"📍 {city} ({dist_str})\n"
        f"🔗 {url}"
    )


def notify_high_score_listings(listings, min_score=MIN_SCORE):
    """Manda una notifica per ogni listing con score >= min_score.
    Restituisce il numero di messaggi REALMENTE recapitati."""
    if not can_notify():
        return 0

    pause = 1.0 if _telegram_ready() else 7.0
    sent = 0
    failed = 0
    first_error = ""

    for listing in listings:
        if (listing.get("score") or 0) < min_score:
            continue
        ok, err = _send(_format_listing(listing))
        if ok:
            sent += 1
        else:
            failed += 1
            if not first_error:
                first_error = err
                print(f"  ❌ Invio fallito ({channel_name()}): {err}")
            if failed >= 3 and sent == 0:
                print(f"  ⏹  Interrotto dopo {failed} fallimenti consecutivi: "
                      f"canale non funzionante, gli annunci restano sul foglio.")
                break
        time.sleep(pause)

    if failed:
        print(f"  ⚠️  {failed} notifiche NON recapitate")
    return sent
