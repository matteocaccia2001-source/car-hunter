# CAR HUNTER — Costituzione del Progetto

## North Star
Trovare automaticamente annunci di BMW E36, Audi B5 e Mercedes 190E
immatricolate tra il 1991 e il 1996, entro 300 km da Bergamo, a meno di €6.000.

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

- **Anno**: solo 1991–1996 inclusi (30–35 anni fa dal 2026)
- **Prezzo**: massimo €6.000 (annunci senza prezzo = scartati)
- **Distanza**: massimo 300 km da Bergamo (45.6983°N, 9.6773°E)
- **Modelli target**: BMW E36 (Serie 3), Audi B5 (80/A4), Mercedes 190E (W201)
- **Duplicati**: un listing_id per annuncio — mai scrivere lo stesso due volte
- **Frequenza**: ogni 6 ore via GitHub Actions (gratuito)

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

- **Automatico**: cron `0 6,12,18,0 * * *` (06:00, 12:00, 18:00, 00:00 UTC)
- **Manuale**: GitHub Actions → "Run workflow"

## Fase B.L.A.S.T. — Stato

- [x] B — Blueprint approvato
- [ ] L — Link (credenziali da configurare dall'utente)
- [ ] A — Architect (codice in costruzione)
- [ ] S — Stylize (Google Sheets layout)
- [ ] T — Trigger (GitHub Actions)
