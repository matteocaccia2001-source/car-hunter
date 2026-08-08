# CAR HUNTER — Costituzione del Progetto

## North Star
Trovare automaticamente annunci di BMW E36, BMW E46, BMW E92, Audi A4 B5 e
Mercedes 190E entro 300 km da Bergamo, ciascuno nella propria finestra di
produzione e nel proprio budget.

## Schema Dati

### Input (per ogni scraper)
```json
{
  "make": "BMW",
  "model": "E36",
  "year_from": 1991,
  "year_to": 1996,
  "max_price": 6000,
  "radius_km": 300,
  "center": { "lat": 45.6983, "lon": 9.6773 }
}
```

### Output (ogni listing)
```json
{
  "source": "AutoScout24",
  "title": "BMW 316i 1993",
  "make": "BMW",
  "model": "Serie 3 E36",
  "year": 1993,
  "price": 4500,
  "km": 150000,
  "city": "Milano",
  "distance_km": 45.2,
  "condition": "Usato",
  "url": "https://...",
  "seller": "Privato",
  "phone": "",
  "listing_id": "abc123def456",
  "found_at": "2026-05-24T10:00:00"
}
```

## Regole Comportamentali

- **Anno e prezzo**: per target, non globali (vedi tabella sotto). Un filtro
  unico non può funzionare: E36 ed E92 non si sovrappongono né come anni né
  come budget. Annunci senza prezzo = scartati.
- **Distanza**: massimo 300 km da Bergamo (45.6983°N, 9.6773°E)

### Target

| Key  | Modello       | Anni      | Tetto   | Slug AutoScout      | Query testuale |
|------|---------------|-----------|---------|---------------------|----------------|
| E36  | BMW E36       | 1990–2000 | €6.000  | `bmw/serie-3`       | `bmw e36`      |
| E46  | BMW E46       | 1998–2006 | €8.000  | `bmw/serie-3`       | `bmw e46`      |
| E92  | BMW E92       | 2006–2013 | €12.000 | `bmw/serie-3`       | `bmw e92`      |
| B5   | Audi A4 B5    | 1994–2001 | €6.000  | `audi/a4`           | `audi a4 b5`   |
| 190E | Mercedes 190E | 1991–1993 | €6.000  | `mercedes-benz/190` | `mercedes 190e`|

Definiti una volta sola in `utils.py` (`TARGETS`) e usati da tutti gli scraper.
Per aggiungere un modello basta una voce lì.

Su AutoScout E36, E46 ed E92 condividono lo slug `serie-3`: a distinguerli è
solo la finestra anni, e le sovrapposizioni producono doppioni che la
deduplica per `listing_id` assorbe.

Lo score sul prezzo è **relativo al tetto del target**: una E92 a €7.000 su un
tetto di €12.000 vale come una E36 a €3.500 su un tetto di €6.000.
- **Duplicati**: un listing_id per annuncio — mai scrivere lo stesso due volte
- **Frequenza**: ogni 2 ore via GitHub Actions (gratuito, nessun servizio a pagamento)

## Piattaforme Coperte

| Piattaforma              | Tipo      | Priorità | Foglio Sheet          |
|--------------------------|-----------|----------|-----------------------|
| AutoScout24              | HTML/JSON | Alta     | 🔍 Annunci            |
| Subito.it                | API JSON  | Alta     | 🔍 Annunci            |
| Mobile.de                | HTML      | Media    | 🔍 Annunci            |
| PVP (Min. Giustizia)     | HTML      | Alta     | 🔨 Aste Giudiziarie   |
| AsteGiudiziarie.it       | HTML      | Media    | 🔨 Aste Giudiziarie   |

### Note Aste Giudiziarie
- Nessun filtro di distanza (le auto possono essere ovunque in Italia)
- Nessun filtro di anno (spesso non indicato nel lotto)
- Il prezzo è il **prezzo base d'asta** — il prezzo finale può essere superiore
- Richiede deposito cauzionale (~10%) per partecipare

## Invarianti Architetturali

1. Le credenziali vivono SOLO in variabili d'ambiente (mai nel codice)
2. Ogni scraper è indipendente — un fallimento non blocca gli altri
3. La deduplicazione usa `listing_id` (MD5 di url+title+price)
4. Il geocoding usa Nominatim (OpenStreetMap) — gratuito, 1 req/sec
5. I dati temporanei vivono in `/.tmp/`

## Struttura File

```
car-hunter/
├── CLAUDE.md               ← questo file
├── SETUP.md                ← guida setup per l'utente
├── requirements.txt
├── .env.example
├── .github/workflows/
│   └── car-hunter.yml      ← cron GitHub Actions (ogni 6h)
├── memory/
│   ├── task_plan.md
│   ├── findings.md
│   ├── progress.md
│   └── decisions.md
├── architecture/
│   └── SOP_scraping.md
├── execution/
│   ├── main.py             ← orchestratore
│   ├── scraper_autoscout24.py
│   ├── scraper_subito.py
│   ├── scraper_mobile.py
│   ├── sheets_writer.py
│   └── utils.py
└── .tmp/                   ← effimero
```

## Trigger di Esecuzione

- **Automatico**: cron `0 */2 * * *` (ogni 2 ore)
- **Manuale**: GitHub Actions → "Run workflow"

## Scraping di Subito.it

Subito **non** blocca gli IP dei data center: rifiuta le richieste che non
arrivano da un browser reale (403 anche da IP residenziale con `requests`).
Serve quindi Playwright + Chromium, che funziona su GitHub Actions esattamente
come in locale. Nessun servizio di proxy/scraping a pagamento è necessario.

## Fase B.L.A.S.T. — Stato

- [x] B — Blueprint approvato
- [ ] L — Link (credenziali da configurare dall'utente)
- [ ] A — Architect (codice in costruzione)
- [ ] S — Stylize (Google Sheets layout)
- [ ] T — Trigger (GitHub Actions)
