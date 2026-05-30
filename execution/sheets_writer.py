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
SHEET_BOOKMARKS = "🔖 Bookmarks Aste"
SHEET_CONTACTS = "👥 Contatti"
SHEET_DASHBOARD = "📊 Dashboard"
SHEET_SEEN = "Visti"

BOOKMARKS = [
    # (Portale, Tipo, URL ricerca)
    ("PVP — Min. Giustizia", "Tutti i veicoli", "https://pvp.giustizia.it/pvp/it/ricerca_avanzata_vendite.wp"),
    ("AsteGiudiziarie.it", "Cerca BMW",       "https://www.astegiudiziarie.it/Aste/ListaAste?cerca=BMW&categoria=autoveicoli"),
    ("AsteGiudiziarie.it", "Cerca Audi",      "https://www.astegiudiziarie.it/Aste/ListaAste?cerca=Audi&categoria=autoveicoli"),
    ("AsteGiudiziarie.it", "Cerca Mercedes",  "https://www.astegiudiziarie.it/Aste/ListaAste?cerca=Mercedes&categoria=autoveicoli"),
    ("AsteTelematica.it",  "Tutti veicoli",   "https://www.astetelematiche.it/auto"),
    ("Gobid.it",           "Tutti veicoli",   "https://www.gobid.it/it/aste/veicoli"),
    ("FallcoAste.it",      "Auto",            "https://www.fallcoaste.it/cerca?categoria=veicoli"),
    ("Astebene.it",        "Auto",            "https://www.astebene.it/aste/veicoli"),
    ("Doauction.it",       "Auto",            "https://www.doauction.it/it/ricerca?categoria=auto"),
    ("Ananke Aste",        "Auto",            "https://www.anankeaste.it/categoria/veicoli"),
]

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
    bookmarks_ws = _get_or_create(spreadsheet, SHEET_BOOKMARKS)
    contacts_ws = _get_or_create(spreadsheet, SHEET_CONTACTS)
    dashboard_ws = _get_or_create(spreadsheet, SHEET_DASHBOARD)
    seen_ws = _get_or_create(spreadsheet, SHEET_SEEN)

    # Bookmarks (popolato una sola volta)
    if not bookmarks_ws.row_values(1):
        rows = [["Portale", "Tipo Ricerca", "Link Diretto (clicca per aprire)"]]
        for portale, tipo, link in BOOKMARKS:
            rows.append([portale, tipo, link])
        bookmarks_ws.update("A1:C{}".format(len(rows)), rows)
        bookmarks_ws.format("A1:C1", {
            "backgroundColor": {"red": 0.5, "green": 0.3, "blue": 0.7},
            "textFormat": {"foregroundColor": COLOR_WHITE, "bold": True, "fontSize": 10},
            "horizontalAlignment": "CENTER",
        })
        bookmarks_ws.freeze(rows=1)

    listings_first_time = not listings_ws.row_values(1)
    if listings_first_time:
        listings_ws.update("A1:P1", [LISTINGS_HEADERS])
        _format_header(listings_ws, len(LISTINGS_HEADERS))
        listings_ws.freeze(rows=1)
        _setup_score_conditional_formatting(spreadsheet, listings_ws)
    elif not _has_conditional_formatting(spreadsheet, listings_ws):
        # Retrofit per fogli già esistenti senza color rules
        _setup_score_conditional_formatting(spreadsheet, listings_ws)

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

    return listings_ws, auctions_ws, bookmarks_ws, contacts_ws, dashboard_ws, seen_ws


def _has_conditional_formatting(spreadsheet, ws):
    """Check if the worksheet already has conditional format rules on the Score column."""
    try:
        meta = spreadsheet.fetch_sheet_metadata(params={"fields": "sheets(properties.sheetId,conditionalFormats)"})
        for s in meta.get("sheets", []):
            if s["properties"]["sheetId"] == ws.id:
                return len(s.get("conditionalFormats", [])) > 0
    except Exception:
        return True  # in dubbio, assumi che esista per non spammare le API
    return False


def _setup_score_conditional_formatting(spreadsheet, ws):
    """Imposta UNA volta le regole di colore per la colonna Score (K)."""
    sheet_id = ws.id
    # Score column = K = index 10 (0-based)
    rng = {
        "sheetId": sheet_id,
        "startRowIndex": 1,
        "endRowIndex": 5000,
        "startColumnIndex": 10,
        "endColumnIndex": 11,
    }
    # Threshold interi (Google Sheets API non accetta decimali nelle conditional rules)
    rules = [
        # >= 8 → verde brillante (bomba)
        ({"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": "8"}]},
         {"red": 0.72, "green": 0.93, "blue": 0.72}),
        # >= 7 → verde chiaro (buon affare)
        ({"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": "7"}]},
         {"red": 0.86, "green": 0.96, "blue": 0.82}),
        # >= 5 → giallo (standard)
        ({"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": "5"}]},
         {"red": 1.00, "green": 0.95, "blue": 0.80}),
        # >= 4 → arancio (sotto media)
        ({"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": "4"}]},
         {"red": 0.99, "green": 0.85, "blue": 0.78}),
        # < 4 → rosso (da evitare)
        ({"type": "NUMBER_LESS", "values": [{"userEnteredValue": "4"}]},
         {"red": 0.96, "green": 0.74, "blue": 0.74}),
    ]
    requests = []
    for idx, (condition, bg) in enumerate(rules):
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [rng],
                    "booleanRule": {
                        "condition": condition,
                        "format": {"backgroundColor": bg, "textFormat": {"bold": True}},
                    },
                },
                "index": idx,
            }
        })
    try:
        spreadsheet.batch_update({"requests": requests})
    except Exception as e:
        print(f"  Conditional formatting setup error: {e}")


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
    _, auctions_ws, _, _, _, seen_ws = _setup_sheets(spreadsheet)

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

    # Pre-popola numero riga prima dell'append → niente update_cell per row
    for i, row in enumerate(rows):
        row[0] = current_row + i

    auctions_ws.append_rows(rows, value_input_option="USER_ENTERED")
    seen_ws.append_rows(new_ids)
    print(f"  ✅ {len(new_auctions)} new auction lots written.")
    return len(new_auctions)


def write_listings(listings, spreadsheet_id):
    client = _get_client()
    spreadsheet = client.open_by_key(spreadsheet_id)
    listings_ws, _, _, _, dashboard_ws, seen_ws = _setup_sheets(spreadsheet)

    seen_ids = _get_seen_ids(seen_ws)
    new_listings = [l for l in listings if l.get("listing_id") not in seen_ids]

    if not new_listings:
        print("  No new listings to add.")
        return 0

    rows = [_listing_to_row(l) for l in new_listings]
    new_ids = [[l["listing_id"]] for l in new_listings]

    current_row = len(listings_ws.col_values(1))

    # Riempi la colonna # nelle rows PRIMA dell'append → niente update_cell per ogni riga
    for i, row in enumerate(rows):
        row[0] = current_row + i

    # UNA sola chiamata di append per tutte le righe
    listings_ws.append_rows(rows, value_input_option="USER_ENTERED")

    # UNA sola chiamata di append per gli ID visti
    seen_ws.append_rows(new_ids)

    # UNA sola chiamata per la dashboard timestamp
    dashboard_ws.update("B3", [[datetime.now().strftime("%d/%m/%Y %H:%M")]])

    print(f"  ✅ {len(new_listings)} new listings written to Google Sheets.")
    return len(new_listings)
