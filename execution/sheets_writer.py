import gspread
from google.oauth2.service_account import Credentials
import os
import json
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_LISTINGS = "🔍 Annunci"
SHEET_AUCTIONS = "🔨 Aste Giudiziarie"
SHEET_CONTACTS = "👥 Contatti"
SHEET_DASHBOARD = "📊 Dashboard"
SHEET_SEEN = "Visti"

AUCTIONS_HEADERS = [
    "#", "Data Trovato", "Piattaforma", "Marca", "Modello",
    "Titolo Lotto", "Prezzo Base (€)", "Data Asta", "Tribunale / Sede",
    "N. Lotto", "Link", "ID",
]

LISTINGS_HEADERS = [
    "#", "Data", "Piattaforma", "Marca", "Modello", "Anno",
    "Prezzo (€)", "Km", "Città", "Dist. Bergamo (km)",
    "Score", "Titolo", "Condizioni", "Link", "Venditore", "ID",
]

CONTACTS_HEADERS = [
    "#", "Data", "Fonte", "Nome / Profilo", "Link Profilo",
    "Veicolo", "Anno Stimato", "Contatto", "Bozza Messaggio", "Note",
]

COLOR_BLUE = {"red": 0.18, "green": 0.35, "blue": 0.6}
COLOR_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
COLOR_GREEN = {"red": 0.13, "green": 0.55, "blue": 0.13}
COLOR_GRAY = {"red": 0.95, "green": 0.95, "blue": 0.95}


def _get_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create(spreadsheet, name):
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=name, rows=2000, cols=20)


def _format_header(ws, col_count):
    col_letter = chr(ord("A") + col_count - 1)
    ws.format(f"A1:{col_letter}1", {
        "backgroundColor": COLOR_BLUE,
        "textFormat": {
            "foregroundColor": COLOR_WHITE,
            "bold": True,
            "fontSize": 10,
        },
        "horizontalAlignment": "CENTER",
    })


def _setup_sheets(spreadsheet):
    listings_ws = _get_or_create(spreadsheet, SHEET_LISTINGS)
    auctions_ws = _get_or_create(spreadsheet, SHEET_AUCTIONS)
    contacts_ws = _get_or_create(spreadsheet, SHEET_CONTACTS)
    dashboard_ws = _get_or_create(spreadsheet, SHEET_DASHBOARD)
    seen_ws = _get_or_create(spreadsheet, SHEET_SEEN)

    if not listings_ws.row_values(1):
        listings_ws.update("A1:P1", [LISTINGS_HEADERS])
        _format_header(listings_ws, len(LISTINGS_HEADERS))
        listings_ws.freeze(rows=1)

    if not auctions_ws.row_values(1):
        auctions_ws.update("A1:L1", [AUCTIONS_HEADERS])
        # Intestazione arancione per distinguerle dagli annunci normali
        auctions_ws.format("A1:L1", {
            "backgroundColor": {"red": 0.9, "green": 0.45, "blue": 0.0},
            "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True, "fontSize": 10},
            "horizontalAlignment": "CENTER",
        })
        auctions_ws.freeze(rows=1)

    if not contacts_ws.row_values(1):
        contacts_ws.update("A1:J1", [CONTACTS_HEADERS])
        _format_header(contacts_ws, len(CONTACTS_HEADERS))
        contacts_ws.freeze(rows=1)

    if not dashboard_ws.row_values(1):
        _setup_dashboard(dashboard_ws)

    if not seen_ws.row_values(1):
        seen_ws.update("A1", [["listing_id"]])

    return listings_ws, auctions_ws, contacts_ws, dashboard_ws, seen_ws


def _setup_dashboard(ws):
    ws.update("A1:B1", [["🚗 CAR HUNTER — Dashboard", ""]])
    ws.format("A1", {"textFormat": {"bold": True, "fontSize": 16}})
    ws.update("A3:B7", [
        ["Ultima scansione:", "—"],
        ["Annunci totali:", f"=COUNTA('{SHEET_LISTINGS}'!A:A)-1"],
        ["BMW E36:", f"=COUNTIF('{SHEET_LISTINGS}'!D:D,\"BMW\")"],
        ["Audi:", f"=COUNTIF('{SHEET_LISTINGS}'!D:D,\"Audi\")"],
        ["Mercedes:", f"=COUNTIF('{SHEET_LISTINGS}'!D:D,\"Mercedes-Benz\")"],
    ])
    ws.update("A9:B12", [
        ["Per piattaforma", ""],
        ["AutoScout24:", f"=COUNTIF('{SHEET_LISTINGS}'!C:C,\"AutoScout24\")"],
        ["Subito.it:", f"=COUNTIF('{SHEET_LISTINGS}'!C:C,\"Subito.it\")"],
        ["Mobile.de:", f"=COUNTIF('{SHEET_LISTINGS}'!C:C,\"Mobile.de\")"],
    ])
    ws.format("A3:A12", {"textFormat": {"bold": True}})


def _get_seen_ids(seen_ws):
    ids = seen_ws.col_values(1)
    return set(ids[1:]) if len(ids) > 1 else set()


def _listing_to_row(listing):
    dist = listing.get("distance_km")
    dist_str = f"{dist:.0f}" if dist is not None else "N/D"
    km = listing.get("km", 0)
    km_str = f"{km:,}".replace(",", ".") if km else "N/D"
    found = listing.get("found_at", "")[:19].replace("T", " ")

    return [
        "",                              # # (filled after append)
        found,
        listing.get("source", ""),
        listing.get("make", ""),
        listing.get("model", ""),
        listing.get("year", ""),
        listing.get("price", ""),
        km_str,
        listing.get("city", ""),
        dist_str,
        listing.get("score", ""),
        listing.get("title", ""),
        listing.get("condition", ""),
        listing.get("url", ""),
        listing.get("seller", ""),
        listing.get("listing_id", ""),
    ]


def write_auctions(auctions, spreadsheet_id):
    client = _get_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    _, auctions_ws, _, _, seen_ws = _setup_sheets(spreadsheet)

    seen_ids = _get_seen_ids(seen_ws)
    new_auctions = [a for a in auctions if a.get("listing_id") not in seen_ids]

    if not new_auctions:
        print("  No new auction lots to add.")
        return 0

    rows = []
    new_ids = []
    current_row = len(auctions_ws.col_values(1))

    for a in new_auctions:
        found = a.get("found_at", "")[:19].replace("T", " ")
        rows.append([
            "",
            found,
            a.get("source", ""),
            a.get("make", ""),
            a.get("model", ""),
            a.get("title", ""),
            a.get("price_base", ""),
            a.get("auction_date", ""),
            a.get("court", ""),
            a.get("lot", ""),
            a.get("url", ""),
            a.get("listing_id", ""),
        ])
        new_ids.append([a["listing_id"]])

    auctions_ws.append_rows(rows, value_input_option="USER_ENTERED")
    for i in range(len(rows)):
        auctions_ws.update_cell(current_row + i + 1, 1, current_row + i)

    seen_ws.append_rows(new_ids)
    print(f"  ✅ {len(new_auctions)} new auction lots written.")
    return len(new_auctions)


def write_listings(listings, spreadsheet_id):
    client = _get_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    listings_ws, _, _, dashboard_ws, seen_ws = _setup_sheets(spreadsheet)

    seen_ids = _get_seen_ids(seen_ws)
    new_listings = [l for l in listings if l.get("listing_id") not in seen_ids]

    if not new_listings:
        print("  No new listings to add.")
        return 0

    rows = [_listing_to_row(l) for l in new_listings]
    new_ids = [[l["listing_id"]] for l in new_listings]

    current_row = len(listings_ws.col_values(1))
    listings_ws.append_rows(rows, value_input_option="USER_ENTERED")

    for i in range(len(rows)):
        listings_ws.update_cell(current_row + i + 1, 1, current_row + i)

    # Colora la colonna Score (K) in base al valore
    try:
        from scorer import score_color
        format_requests = []
        for i, listing in enumerate(new_listings):
            score = listing.get("score", 0) or 0
            if not score:
                continue
            row_idx = current_row + i + 1
            format_requests.append({
                "range": f"K{row_idx}",
                "format": {
                    "backgroundColor": score_color(score),
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER",
                },
            })
        # Batch format in chunks
        for req in format_requests:
            listings_ws.format(req["range"], req["format"])
    except Exception as e:
        print(f"  Score color formatting skipped: {e}")

    seen_ws.append_rows(new_ids)
    dashboard_ws.update("B3", [[datetime.now().strftime("%d/%m/%Y %H:%M")]])

    print(f"  ✅ {len(new_listings)} new listings written to Google Sheets.")
    return len(new_listings)
