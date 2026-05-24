# SETUP — Car Hunter
### Guida completa senza esperienza richiesta

---

## COSA TI SERVE
- Un browser (Chrome o Safari)
- Account Google (Gmail) — se non ce l'hai: gmail.com → Crea account
- 20 minuti

---

## PASSO 1 — Crea un account GitHub

1. Vai su **github.com**
2. Clicca **Sign up**
3. Inserisci email, password, username
4. Conferma la email
5. Scegli il piano **Free**

---

## PASSO 2 — Crea il repository su GitHub

1. Una volta loggato su GitHub, clicca il **+** in alto a destra → **New repository**
2. Nome: `car-hunter`
3. Visibilità: **Public** ← importante (gratis con Public)
4. Non spuntare nient'altro
5. Clicca **Create repository**
6. Tieni aperta questa pagina — ti servirà tra poco

---

## PASSO 3 — Crea il progetto Google Cloud

1. Vai su **console.cloud.google.com**
   (se ti chiede di accettare le condizioni, accetta)
2. In alto clicca su **Select a project** → **New Project**
3. Nome progetto: `car-hunter`
4. Clicca **Create**
5. Assicurati che il progetto `car-hunter` sia selezionato in alto

---

## PASSO 4 — Abilita Google Sheets API

1. Nel menu a sinistra cerca **APIs & Services** → **Library**
2. Nella barra di ricerca scrivi `Google Sheets API`
3. Clicca sul risultato → **Enable**
4. Ripeti per **Google Drive API** (stessa procedura)

---

## PASSO 5 — Crea il Service Account (le "chiavi" del sistema)

1. Vai su **APIs & Services** → **Credentials**
2. Clicca **+ Create Credentials** → **Service Account**
3. Nome: `car-hunter-bot`
4. Clicca **Create and Continue** → **Done** (salta i passaggi opzionali)
5. Clicca sulla email del service account appena creato (es. `car-hunter-bot@car-hunter-xxxxx.iam.gserviceaccount.com`)
6. Vai alla tab **Keys**
7. Clicca **Add Key** → **Create new key** → **JSON** → **Create**
8. Si scaricherà un file JSON sul tuo computer — **non perderlo e non condividerlo**

---

## PASSO 6 — Crea il Google Sheet

1. Vai su **sheets.google.com**
2. Clicca **+** per creare un nuovo foglio
3. Rinominalo `Car Hunter` (clicca su "Foglio senza titolo" in alto)
4. Copia l'**ID** dal URL: è la stringa lunga tra `/d/` e `/edit`
   Esempio: `https://docs.google.com/spreadsheets/d/`**`1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms`**`/edit`
5. Salva questo ID — ti serve al Passo 8

6. Condividi il foglio con il service account:
   - Clicca **Condividi** (tasto verde in alto a destra)
   - Incolla l'email del service account (es. `car-hunter-bot@car-hunter-xxxxx.iam.gserviceaccount.com`)
   - Ruolo: **Editor**
   - Clicca **Invia**

---

## PASSO 7 — Carica il codice su GitHub

Apri il **Terminale** (su Mac: Spotlight → "Terminale") e lancia questi comandi uno alla volta:

```bash
cd /Users/matteocaccia/code/car-hunter
git init
git add .
git commit -m "Car Hunter - setup iniziale"
git branch -M main
git remote add origin https://github.com/IL_TUO_USERNAME/car-hunter.git
git push -u origin main
```

> Sostituisci `IL_TUO_USERNAME` con il tuo username GitHub.
> GitHub potrebbe chiederti username e password (o un Personal Access Token).

---

## PASSO 8 — Aggiungi i Secrets a GitHub

I secrets sono variabili private che GitHub usa per eseguire il codice senza esporre le credenziali.

1. Vai sul tuo repository GitHub (`github.com/IL_TUO_USERNAME/car-hunter`)
2. Clicca **Settings** (tab in alto)
3. Nel menu a sinistra: **Secrets and variables** → **Actions**
4. Clicca **New repository secret**

**Secret 1 — GOOGLE_CREDENTIALS_JSON**
- Name: `GOOGLE_CREDENTIALS_JSON`
- Value: apri il file JSON scaricato al Passo 5, seleziona tutto il testo e incollalo qui

**Secret 2 — SPREADSHEET_ID**
- Name: `SPREADSHEET_ID`
- Value: l'ID del Google Sheet copiato al Passo 6

---

## PASSO 9 — Primo test manuale

1. Vai su **github.com/IL_TUO_USERNAME/car-hunter**
2. Clicca la tab **Actions**
3. Nel menu a sinistra clicca **Car Hunter**
4. Clicca **Run workflow** → **Run workflow** (conferma)
5. Aspetta 2–5 minuti
6. Se il pallino diventa ✅ verde: funziona!
7. Apri il tuo Google Sheet — dovresti vedere i primi annunci

---

## COSA SUCCEDE DOPO

Il sistema girerà automaticamente **4 volte al giorno** (alle 06:00, 12:00, 18:00, 00:00 UTC).
Ogni volta che trova annunci nuovi, li aggiunge al foglio.
Gli annunci già visti non vengono duplicati.

---

## SE QUALCOSA VA MALE

1. Vai su **Actions** nel repo GitHub
2. Clicca sul run rosso ❌
3. Clicca sul job `hunt` per vedere i log
4. Mostrami il testo dell'errore — risolvo in pochi minuti

---

## LAYOUT GOOGLE SHEETS

| Foglio | Contenuto |
|--------|-----------|
| 🔍 Annunci | Tutti gli annunci trovati, ordinati per prezzo |
| 👥 Contatti | Proprietari diretti da contattare |
| 📊 Dashboard | Contatori per marca e piattaforma |
| Visti | (nascosto) ID già visti — per deduplicazione |
