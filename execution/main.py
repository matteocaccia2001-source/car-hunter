import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from scraper_autoscout24 import scrape_autoscout24
from scraper_subito import scrape_subito
from scraper_mobile import scrape_mobile
from scraper_autouncle import scrape_autouncle
from scraper_catawiki import scrape_catawiki
from scraper_motostoriche import scrape_motostoriche
from scraper_aste import scrape_aste
from sheets_writer import write_listings, write_auctions
from scorer import score_listing
from utils import MAX_PRICE, YEAR_MIN, YEAR_MAX


def deduplicate(listings):
    seen = {}
    for l in listings:
        lid = l.get("listing_id", "")
        if lid and lid not in seen:
            seen[lid] = l
    return list(seen.values())


def filter_listings(listings):
    out = []
    for l in listings:
        price = l.get("price", 0)
        year = l.get("year", 0)
        if price <= 0 or price > MAX_PRICE:
            continue
        if year and not (YEAR_MIN <= year <= YEAR_MAX):
            continue
        out.append(l)
    return out


def run_scraper(name, fn):
    print(f"\n📡 {name}...")
    try:
        results = fn()
        print(f"  → {len(results)} raw listings")
        return results
    except Exception as e:
        print(f"  ❌ {name} failed: {e}")
        return []


def main():
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "")
    if not spreadsheet_id:
        print("❌ SPREADSHEET_ID not set. Check your environment variables.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"🚗 CAR HUNTER — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}")

    all_listings = []
    all_listings += run_scraper("AutoScout24", scrape_autoscout24)
    all_listings += run_scraper("Subito.it", scrape_subito)
    all_listings += run_scraper("AutoScout24.de", scrape_mobile)
    all_listings += run_scraper("AutoUncle", scrape_autouncle)
    all_listings += run_scraper("Catawiki", scrape_catawiki)
    all_listings += run_scraper("ClassicTrader", scrape_motostoriche)

    filtered = filter_listings(all_listings)
    unique = deduplicate(filtered)

    # Apply value score (1-10) to each listing
    for listing in unique:
        listing["score"] = score_listing(listing)

    # Sort by score descending (best first), then by price ascending
    unique.sort(key=lambda x: (-x.get("score", 0), x.get("price", 999999)))

    print(f"\n📊 Annunci:")
    print(f"  Scraped:          {len(all_listings)}")
    print(f"  After filters:    {len(filtered)}")
    print(f"  After dedup:      {len(unique)}")

    print(f"\n📝 Writing annunci to Google Sheets...")
    written = write_listings(unique, spreadsheet_id)

    # Aste giudiziarie — canale separato, nessun filtro di distanza/anno
    print(f"\n🔨 Aste Giudiziarie...")
    all_auctions = run_scraper("Aste Giudiziarie", scrape_aste)
    unique_auctions = deduplicate(all_auctions)
    print(f"  After dedup:      {len(unique_auctions)}")

    print(f"\n📝 Writing aste to Google Sheets...")
    written_auctions = write_auctions(unique_auctions, spreadsheet_id)

    print(f"\n{'='*60}")
    print(f"✅ Done. {written} annunci + {written_auctions} lotti d'asta aggiunti.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
