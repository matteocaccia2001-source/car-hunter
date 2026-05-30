# SETUP MAC — Car Hunter in locale

Una volta completati questi step, il sistema gira **ogni 6 ore** sul tuo Mac.
GitHub Actions può rimanere come backup ma non è più necessario.

---

## PASSO 1 — Aggiorna il codice

Apri il Terminale ed esegui:

```bash
cd /Users/matteocaccia/code/car-hunter
git pull
```

## PASSO 2 — Crea il file .env

Crea il file `.env` nella cartella `car-hunter` con dentro:

```
GOOGLE_CREDENTIALS_JSON='INCOLLA_QUI_TUTTO_IL_JSON_DEL_SERVICE_ACCOUNT'
SPREADSHEET_ID=INCOLLA_QUI_L_ID_DEL_SHEET
```

Sono gli stessi valori che hai messo nei Secrets GitHub. Per crearlo:

```bash
nano .env
```

Incolla i due valori, poi premi `Ctrl+O`, `Invio`, `Ctrl+X` per salvare.

## PASSO 3 — Esegui il setup

```bash
bash local/setup.sh
```

Il setup script fa **tutto** in automatico:
- Crea ambiente Python isolato
- Installa le dipendenze (~30 sec)
- Installa Chrome headless per Playwright (~150 MB, 1 minuto)
- Fa un test run
- Installa lo scheduler `launchd` (4 esecuzioni/giorno)

## PASSO 4 — Verifica

Apri il Google Sheet e controlla che ci siano nuovi annunci. Fatto.

---

## Comandi utili

```bash
# Eseguire manualmente adesso
bash local/run.sh

# Vedere i log dell'ultima esecuzione
cat .tmp/run.log

# Vedere i log in tempo reale (mentre gira)
tail -f .tmp/run.log

# Fermare la schedulazione automatica
launchctl unload ~/Library/LaunchAgents/com.carhunter.plist

# Riavviare la schedulazione
launchctl load ~/Library/LaunchAgents/com.carhunter.plist
```

---

## FAQ

**Il Mac consuma di più?**
~10 centesimi/mese. Trascurabile.

**E se chiudo il Mac?**
Lo script non parte. Riparte alla prossima ora schedulata quando il Mac torna attivo.

**Posso disabilitare GitHub Actions?**
Sì, opzionale. Vai su `github.com/.../car-hunter` → Actions → Car Hunter → "..." → Disable workflow.

**Vedo errori "Playwright not installed"?**
Significa che il venv non è stato attivato. Esegui di nuovo `bash local/setup.sh`.
