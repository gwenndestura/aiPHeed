# aiPHeed

**Food-insecurity risk forecasting for CALABARZON.** aiPHeed forecasts, for each of
the five CALABARZON provinces (Batangas, Cavite, Laguna, Quezon and Rizal), the
chance that household food insecurity will be HIGH one to three quarters ahead,
explains what drives each forecast, and shows it on an interactive map
dashboard with province and municipal detail, charts, news evidence and PDF
reports.

It was developed as a thesis for the Bachelor of Science in Computer Science
with Intelligent Systems Track at De La Salle University - Dasmariñas, by
Princess Gwenn A. Destura, Christina M. Esico and Angel Vhea P. Melindo. The
Department of Agriculture did not develop aiPHeed and has not endorsed it.

---

## Contents

1. [What the system does](#1-what-the-system-does)
2. [Technology](#2-technology)
3. [Requirements](#3-requirements)
4. [Setup](#4-setup)
5. [Check that it works](#5-check-that-it-works)
6. [Running the tests](#6-running-the-tests)
7. [Administrator accounts](#7-administrator-accounts)
8. [Repository layout](#8-repository-layout)
9. [Known limitations](#9-known-limitations)
10. [Further documentation](#10-further-documentation)

---

## 1. What the system does

### The model

The served model is **E168 LightGBM** (`e168-lgbm-1.0`). It forecasts the
provincial share of households that are moderately or severely food insecure
under the HFIAS scale (Household Food Insecurity Access Scale, as measured by
FNRI's Expanded National Nutrition Survey). A province is **HIGH** when that
share is 50 % or more.

The model has three parts:

1. **Survey baseline:** the latest measured provincial HFIAS figure.
2. **Constrained LightGBM:** predicts the change from that baseline using five
   groups of inputs: weather and farm supply, food prices, jobs, remittances
   from overseas Filipino workers, and fish catch, with news evidence inside
   the groups.
3. **Calibration layer:** turns the forecast into a probability of HIGH.

The number shown on the map and in the ranking is that **probability of HIGH**
(0 to 1). The forecast share of food-insecure households is shown alongside it.

### Accuracy

Measured on 72 chronological, as-of forecasts against the ENNS 2018, 2019 and
2021 survey rounds:

| Quarters ahead | 1 | 2 | 3 |
|---|---|---|---|
| E168 accuracy | 75.0 % | 77.8 % | 75.0 % |
| Reusing the latest survey (baseline) | 62.5 % | 62.5 % | 62.5 % |

Leads 1 to 3 meet the project's acceptance rule (at least 75 % accurate and
significantly better than reusing the latest survey), so the dashboard serves
forecasts up to three quarters ahead. Full evidence:
`docs/final/FINAL_SYSTEM_REPORT_E168.md`.

### What the dashboard shows

- **Map:** each province coloured by risk, with municipal detail on zoom.
- **Drivers:** each input group's share of the forecast (SHAP values), with a
  plain-language explanation using the latest figures.
- **Province ranking**, **forecast history**, **news reports used**, and
  **data freshness** for every input source.
- **Data** page: a sortable, filterable table with CSV export.
- **Visualization** page: trend charts and driver charts, exportable as PNG and
  PDF.
- **Administrator area:** review and approval of forecasts, accounts, audit log
  and user feedback.

---

## 2. Technology

| Part | Technology |
|---|---|
| Backend API | Python 3.13, FastAPI, Uvicorn |
| Model | LightGBM, scikit-learn, SHAP |
| Database | SQLite through SQLAlchemy (async) with Alembic migrations. It holds accounts, reviews, audit and feedback only; the forecasts are read from the model files in `backend/data/` |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Leaflet, Recharts |
| Tests | pytest (backend), Vitest and Testing Library (frontend) |

The trained model and every data file the API reads are included in the
repository, so the system runs without downloading any data.

---

## 3. Requirements

- **Python 3.13** (developed on 3.13.2)
- **Node.js 22** (developed on 22.14) with npm
- **Git**
- About 6 GB of free disk space: the repository is about 400 MB, and the
  Python packages include PyTorch and the transformer libraries used for news
  scoring
- Windows, macOS or Linux. The commands below are for Windows PowerShell; the
  macOS and Linux equivalents are noted where they differ.

---

## 4. Setup

You will run two programs side by side: the **backend** (the API, on port 8000)
and the **frontend** (the website, on port 8080). Use two terminal windows.

### 4.1 Get the code

```powershell
git clone https://github.com/gwenndestura/aipheed-system.git
cd aipheed-system
```

### 4.2 Backend

```powershell
cd backend

# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate            # macOS / Linux: source venv/bin/activate

# 2. Install the packages (this takes several minutes)
pip install -r requirements.txt
pip install -r requirements-dev.txt   # only needed to run the tests

# 3. Create the settings file from the template
copy .env.example .env             # macOS / Linux: cp .env.example .env
```

Open `backend/.env` in a text editor and replace `SECRET_KEY=changeme` with a
long random value. You can generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Leave the other settings as they are. In particular, keep these two lines,
which select the E168 model and make the API refuse to start rather than fall
back to an older model:

```
AIPHEED_LEAD2_MODEL=thesis
AIPHEED_STRICT_MODEL=1
```

With `SMTP_HOST` left empty, emails (sign-up verification and password reset)
are printed in the backend terminal instead of being sent.

```powershell
# 4. Create the database (a new, empty SQLite file: backend/aipheed.db)
python -m alembic upgrade head

# 5. Start the API
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start-up takes up to a minute. It is ready when the terminal shows:

```
Serving e168-lgbm-1.0 (E168 LightGBM food-insecurity risk) on the dashboard (strict)
```

Leave this window open.

### 4.3 Frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:8080** in a browser. The frontend calls the API at
`http://localhost:8000` by default. To use another address, copy
`frontend/.env.example` to `frontend/.env` and change `VITE_API_BASE_URL`.

A short guided tour appears on the first visit to each page. It can be skipped.

### 4.4 Map background (optional)

The province and municipal shapes, colours and labels are drawn from files in
the repository. The street-map background underneath them is a separate
OpenStreetMap tile file, `frontend/public/basemap.pmtiles`, which is not
included because of its size. Without it the map still works, but shows a plain
background and the browser console logs tile errors. To add it, extract the
CALABARZON area from a Protomaps build (https://docs.protomaps.com) with the
`pmtiles` command-line tool and save it as `frontend/public/basemap.pmtiles`,
or set `VITE_BASEMAP_PMTILES_URL` to a hosted copy.

---

## 5. Check that it works

With the backend running:

| Address | Expected |
|---|---|
| http://127.0.0.1:8000/api/v1/health | `{"status": "ok", ...}` |
| http://127.0.0.1:8000/api/v1/final/food-insecurity/outlook | `"status": "approved"`, `"model": "e168-lgbm-1.0"` |
| http://127.0.0.1:8000/api/v1/provinces?quarter=2027-Q1 | five provinces, each with a `riskScore` |

On the dashboard, the overall CALABARZON score for 2027-Q1 is **0.03** (low
risk), with Quezon the highest-risk province.

To browse every API route, set `ENABLE_API_DOCS=true` in `backend/.env`,
restart the backend, and open http://127.0.0.1:8000/docs. Keep it `false` in a
deployment.

---

## 6. Running the tests

### Frontend

```powershell
cd frontend
npm test                 # 97 tests
npx tsc --noEmit -p tsconfig.app.json
npm run build
```

### Backend

```powershell
cd backend
python -m pytest -q --continue-on-collection-errors
```

The tests use an in-memory database and never touch `backend/aipheed.db`.
Some research tests need large raw data files that are not in the repository
(for example the IBTrACS typhoon archive); those report a missing-file error
and can be ignored. See [section 9](#9-known-limitations) for the current
result.

---

## 7. Administrator accounts

The public dashboard needs no account. The administrator area (forecast review,
accounts, audit log, feedback) does. A new database has no administrator, so
create the first one from the `backend` folder:

```powershell
python scripts/create_admin.py --email juan.delacruz@calabarzon.da.gov.ph --name "Juan Dela Cruz"
```

It asks for a password (at least 12 characters, not a common password). Only
`@calabarzon.da.gov.ph` addresses are accepted. Other people sign up on the
website and an administrator approves them under **☰ menu → Accounts**.

`SETUP_GUIDE.md` explains every setting, account approval, the read-only demo
account for presentations, password resets and the checklist before going
live.

---

## 8. Repository layout

```
backend/
  app/
    main.py            API start-up, including the strict model check
    api/v1/            HTTP endpoints (dashboard, forecast, explainability,
                       final outlook, report, auth, admin)
    e168/              the served E168 model: serving, gate, monthly refresh
    ml/inference/      e168_system.py connects E168 to every dashboard endpoint
    services/          dashboard assembly, reports, review, accounts, security
    db/                SQLAlchemy models and Alembic migrations
    e1xx/, fi*/        earlier experiments that E168 builds on (kept for
                       reproducibility; several are imported by E168)
  data/
    e168/              E168 forecasts, inputs and evaluation outputs
    registry/          model registry and the acceptance gate results
  scripts/             admin and maintenance scripts
  tests/               unit, integration and end-to-end tests
frontend/
  src/
    pages/             Landing, dashboard, Data, Visualization, Admin, sign-in
    components/        map, panels, charts, modals
    lib/               API client, data adapters, PDF and CSV export
    test/              Vitest tests
aipheed-backend-aligned/
  experiments/         the research experiments behind the model selection,
                       with their protocols, sealed results and hashes
docs/
  final/               final model, audit and evaluation reports
  user-manual/         user manual (PDF and Word)
```

### Keeping the forecast current

`backend/scripts/live_refresh_monthly.ps1` refreshes the forecast once a month
with the newest public data and news, using the frozen E168 model. It is a
maintenance task for the deployed system and is not needed to evaluate it. It
needs the `AIPHEED_PYTHON` environment variable to point at the Python
environment that runs the news scorer.

---

## 9. Known limitations

These are stated in the thesis and in `docs/final/FINAL_SYSTEM_REPORT_E168.md`:

- **The evidence is retrospective.** Accuracy comes from 72 past forecasts over
  three survey rounds. The 75 % figure at one quarter ahead has a plausible
  range of about 65 to 85 %, and it was 73.6 % with one of three alternative
  random seeds. Forecasts for the 2022 survey round are sealed so they can be
  checked when FNRI publishes provincial results.
- **The three forecast quarters are almost identical.** 2027-Q1, Q2 and Q3 are
  all issued from the same date with the same data, and the latest survey is
  released with a long lag, so the model's answer barely changes with the
  horizon. All five provinces are currently LOW.
- **Some inputs are national.** Employment and remittance figures are national
  series, the same for all five provinces. The dashboard labels them
  "(national figures)".
- **Fish catch stands in for fish kills.** No province-level fish-kill event
  data exists, so the fisheries input is the change in fish catch, and the
  dashboard says so.
- **The provincial inputs show no proven province-specific value** beyond
  timing in the research tests.
- **Backend test suite.** On this release (Windows, Python 3.13.2), 1,646
  tests pass, 33 are skipped, 26 fail and one file cannot load. The same 26
  failures and the load error also occur on the source branch before this
  repository was prepared. They are research checks, not checks of the served
  dashboard:
  - **Missing raw files.** Some experiments need large third-party raw files,
    such as the IBTrACS typhoon archive, that are not in the repository. This
    causes the load error and several failures.
  - **Locked hashes.** Some experiments lock the exact bytes of their inputs and
    outputs, and a later experiment changed one of those files, so they report
    a lock mismatch.
  - **One outdated expectation.** `test_e168_regenerate.py` still expects the
    original 2026-10-01 issue date. The monthly refresh has since moved it to
    2026-11-01.

  The frontend suite passes in full (97 tests), with no TypeScript errors.

---

## 10. Further documentation

| Document | Contents |
|---|---|
| `SETUP_GUIDE.md` | Plain-language guide for the person who maintains the system |
| `docs/final/FINAL_SYSTEM_REPORT_E168.md` | The served model, its accuracy and limits |
| `docs/final/INDEPENDENT_COMPLIANCE_AUDIT_E168.md` | Independent audit of the E168 system |
| `docs/final/LEAKAGE_AUDIT_E168.md` | Check that no future information leaks into the forecasts |
| `docs/e158_frontend_verification/FINAL_FRONTEND_MODEL_VERIFICATION.md` | End-to-end check that the model's output reaches the screen unchanged |
| `docs/final/iso25010/` | ISO/IEC 25010 software quality evaluation material |
| `docs/user-manual/aiPHeed_User_Manual.pdf` | User manual |
