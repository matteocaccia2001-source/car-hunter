# Findings — Car Hunter

## Piattaforme

### AutoScout24.it
- App Next.js — i dati listing sono in `<script id="__NEXT_DATA__">` (JSON)
- Supporta filtri via URL: make, model, year range, price_to, zipcodeCity, zipcodeRadius
- Paginazione via parametro `&page=N`
- Rate limit: nessuno documentato, usare delay 2–4s tra richieste

### Subito.it
- API pubblica: `https://api.subito.it/sbt/v1/search/items/`
- Parametri: `c=2` (auto), `t=s` (vendi), `geo_radius`, `lat`, `lon`
- Restituisce JSON con campo `ads[]`
- Il campo prezzi è in `prices[0].value` (stringa con €)

### Mobile.de
- Sito tedesco, copertura prevalentemente Germania/Austria
- HTML scraping — struttura può cambiare
- Utile come fonte secondaria, non primaria per l'Italia

### Nominatim (OpenStreetMap)
- Geocoding gratuito: `https://nominatim.openstreetmap.org/search`
- Rate limit: 1 richiesta/secondo (obbligatorio per ToS)
- User-Agent obbligatorio nell'header

## Modelli e Date

| Target         | Codice  | Anni produzione | Anni nel range 1991–1996 |
|----------------|---------|-----------------|--------------------------|
| BMW E36        | Serie 3 | 1990–2000       | 1991–1996 ✓              |
| Audi B4 (80)   | 80      | 1991–1996       | 1991–1996 ✓              |
| Audi B5 (A4)   | A4      | 1994–2001       | 1994–1996 ✓              |
| Mercedes 190E  | W201    | 1982–1993       | 1991–1993 ✓              |

## Stack Gratuito

- **Runtime**: GitHub Actions (2.000 min/mese gratis su repo pubblici)
- **Storage**: Google Sheets (gratuito)
- **Geocoding**: Nominatim (gratuito)
- **Costo totale**: €0/mese
