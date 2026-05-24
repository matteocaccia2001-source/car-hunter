# Decisions — Car Hunter

## GitHub Actions come scheduler
**Scelta**: usare GitHub Actions cron invece di un server dedicato
**Motivazione**: gratuito (2.000 min/mese), zero infrastruttura, affidabile
**Trade-off**: minimo 1 min di latenza all'avvio, non real-time

## Google Sheets come destinazione
**Scelta**: Google Sheets via gspread
**Motivazione**: richiesto dall'utente, gratuito, accessibile da browser/mobile
**Trade-off**: limite 100 req/min API, ok per questo use case

## Nominatim per geocoding
**Scelta**: OpenStreetMap Nominatim invece di Google Maps API
**Motivazione**: gratuito, nessuna API key richiesta
**Trade-off**: rate limit 1 req/sec, cache in-memory per ridurre chiamate

## Deduplicazione via MD5
**Scelta**: hash MD5 di (url + title + price) come listing_id
**Motivazione**: deterministico, veloce, nessun DB esterno richiesto
**Trade-off**: cambio di prezzo = nuovo listing (accettabile)

## Ogni 6 ore
**Scelta**: cron ogni 6 ore (4 volte/giorno)
**Motivazione**: bilanciamento tra freschezza dati e consumo minuti GitHub Actions
**Trade-off**: ~120 min/mese (ben sotto il limite di 2.000)

## Audi: cercare sia 80 che A4
**Scelta**: includere sia Audi 80 B4 (1991–1996) che A4 B5 (1994–1996)
**Motivazione**: l'utente ha detto "Audi B5" ma le auto del range 1991–1993
  sono ancora la generazione 80. Meglio coprire entrambe.
