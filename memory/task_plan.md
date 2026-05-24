# Task Plan — Car Hunter

## Obiettivo
Sistema automatico di ricerca auto storiche (BMW E36 / Audi B5 / Mercedes 190E)
entro 300km da Bergamo, prezzo ≤ €6.000, anno 1991–1996.

## Fasi

### ✅ Fase B — Blueprint
- [x] North Star definita
- [x] Integrazioni identificate (AutoScout24, Subito.it, Mobile.de)
- [x] Schema dati JSON definito in CLAUDE.md
- [x] Regole comportamentali documentate

### 🔄 Fase A — Architect (in corso)
- [x] utils.py (haversine, geocoding, hashing)
- [x] scraper_autoscout24.py
- [x] scraper_subito.py
- [x] scraper_mobile.py
- [x] sheets_writer.py
- [x] main.py
- [x] GitHub Actions workflow

### ⏳ Fase L — Link (da fare dall'utente)
- [ ] GitHub account creato
- [ ] Google Cloud project creato
- [ ] Sheets API abilitata
- [ ] Service Account creato + JSON key scaricato
- [ ] Google Sheet creato e condiviso
- [ ] GitHub Secrets aggiunti
- [ ] Primo test manuale eseguito

### ⏳ Fase S — Stylize
- [x] Google Sheets layout progettato (sheets_writer.py)
- [ ] Verifica visiva dopo primo run

### ⏳ Fase T — Trigger
- [x] GitHub Actions cron configurato
- [ ] Primo run automatico confermato
