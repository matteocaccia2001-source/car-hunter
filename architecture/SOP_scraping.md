# SOP — Scraping (Come Funziona)

## Obiettivo
Raccogliere annunci di BMW E36 / Audi B4-B5 / Mercedes 190E entro 150km da Bergamo, prezzo ≤ €6.000, anno 1991–1996.

## Flusso

```
main.py
  ├── scraper_autoscout24.py  → lista di listing dict
  ├── scraper_subito.py       → lista di listing dict
  ├── scraper_mobile.py       → lista di listing dict
  ↓
filter_listings()   → scarta fuori prezzo / fuori anno
deduplicate()       → scarta per listing_id (MD5)
sort by price
  ↓
sheets_writer.py    → scrive solo i listing NON ancora visti
```

## Regole di Deduplicazione

- `listing_id = MD5(url + title + price)[:12]`
- Gli ID già scritti vivono nel foglio "Visti" (colonna A)
- Prima di scrivere, leggi tutti gli ID visti → scrivi solo i nuovi

## Regole di Distanza

- Centro: Bergamo (45.6983°N, 9.6773°E)
- Formula: Haversine
- Se le coordinate non sono disponibili nell'annuncio → geocodifica la città con Nominatim
- Se la distanza non è calcolabile → includi il listing (non scartare per dati mancanti)

## Rate Limiting

| Piattaforma  | Delay tra pagine | Delay tra modelli |
|--------------|-----------------|-------------------|
| AutoScout24  | 2–4s (random)   | 3–6s              |
| Subito.it    | 1–2s            | 2–3s              |
| Mobile.de    | 3–5s            | 4–7s              |
| Nominatim    | 1.1s (fisso)    | —                 |

## Caso Limite: __NEXT_DATA__ non trovato (AutoScout24)

Sintomo: `No __NEXT_DATA__ on page N`
Causa: AutoScout24 ha cambiato struttura HTML
Azione:
1. Aggiungere un parser HTML di fallback
2. Controllare il sorgente pagina manualmente
3. Aggiornare `_parse_next_data()` con il nuovo path JSON

## Caso Limite: API Subito.it ritorna errore 403

Causa: rate limiting o cambio endpoint
Azione:
1. Aspettare 10 minuti e riprovare
2. Se persiste: aggiungere scraper HTML come fallback
   (URL: `https://www.subito.it/annunci-italia/vendita/auto/?q={query}&raggio=150`)
