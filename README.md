<div align="center">
  <img src="docs/user-manual/img/crops/logo-emblem.png" alt="aiPHeed Logo" width="260" />

  <h1>aiPHeed</h1>

  <p>A food-insecurity risk forecasting system for the five CALABARZON provinces,<br/>backed by an E196 LightGBM model with SHAP explanations and an interactive map dashboard.</p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white" />
    <img src="https://img.shields.io/badge/FastAPI-0.136.0-009688?style=flat-square&logo=fastapi&logoColor=white" />
    <img src="https://img.shields.io/badge/LightGBM-4.6.0-9ACD32?style=flat-square" />
    <img src="https://img.shields.io/badge/React-18.3-61DAFB?style=flat-square&logo=react&logoColor=black" />
    <img src="https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript&logoColor=white" />
    <img src="https://img.shields.io/badge/Vite-5.4-646CFF?style=flat-square&logo=vite&logoColor=white" />
  </p>

  <p>
    <a href="https://drive.google.com/file/d/1jTWFy2kj809mipEthBBRTCXNMAjYIO49/view?usp=drive_link">
      <img src="https://img.shields.io/badge/User_Guide-PDF-EA4335?style=flat-square&logo=googledrive&logoColor=white" alt="User Guide" />
    </a>
  </p>
</div>

---

## User Guide

The **[aiPHeed User Guide (PDF)](https://drive.google.com/file/d/1jTWFy2kj809mipEthBBRTCXNMAjYIO49/view?usp=drive_link)**
walks through every page of the system for its users: the map dashboard, the
Data and Visualization pages, reports, and the administrator area. A copy is
also in the repository at `docs/user-manual/aiPHeed_User_Manual.pdf`.

---

## Overview

**aiPHeed** forecasts, for each of the five CALABARZON provinces (Batangas,
Cavite, Laguna, Quezon and Rizal), the chance that household food insecurity
will be **HIGH** one to four quarters ahead. It explains what drives each
forecast and shows it on an interactive map dashboard with province and
municipal detail, charts, news evidence and PDF reports.

The served model, **E196 LightGBM** (`e196-lgbm-avg5-laf-1.0`), forecasts the provincial
share of households that are moderately or severely food insecure on the HFIAS
scale (Household Food Insecurity Access Scale, as measured by FNRI's Expanded
National Nutrition Survey). A province is **HIGH** when that share is 50 % or
more. The number shown on the map and in the ranking is the **probability of
HIGH** (0 to 1), with the forecast share of food-insecure households alongside
it.

Tested on 72 chronological, as-of forecasts per lead against the ENNS 2018, 2019
and 2021 survey rounds, E196 is **81.9 %, 80.6 %, 79.2 % and 76.4 % accurate**
at one, two, three and four quarters ahead, against 62.5 % for reusing the
latest survey. The same 72 forecasts were used to compare many model variants,
so these figures may be slightly optimistic. After adjusting for that, the
estimate is about 80 % over leads 1 to 3 (`docs/e196/RELIABILITY.md`).
Independent confirmation against the sealed ENNS 2022 results is still pending.

---

## Features

- **Food-insecurity forecasting.** E196 builds on the E168 method: the latest
  measured provincial HFIAS figure, a constrained LightGBM model of its change,
  and a calibration layer that turns the forecast into a probability of HIGH.
  It adds synthetic training rows (training only, never used for testing),
  averages the five best model configurations over 20 synthetic draws, and for
  one quarter ahead also averages in the previous quarter's two-quarters-ahead
  forecast.
- **Five trigger groups.** Weather and farm supply, food prices, jobs,
  remittances from overseas Filipino workers, and fish catch, with news
  evidence inside the groups.
- **Explainable drivers.** SHAP values give each group's share of the forecast,
  with a plain-language explanation using the latest figures.
- **Interactive map dashboard.** Provinces coloured by risk, municipal detail on
  zoom, a quarter timeline, a province ranking, forecast history, news reports
  used, and data freshness for every input source.
- **Data and Visualization pages.** A sortable, filterable table with CSV
  export, plus trend and driver charts exportable as PNG and PDF.
- **Monthly live refresh.** The forecast is refreshed with the newest public
  data and news while the trained model stays frozen.
- **Administrator area.** Forecast review and approval, account approval, audit
  log and user feedback, with a read-only demo account for presentations.
- **Secure accounts.** Email verification, administrator approval, password
  rules, refresh-token sessions and sign-out on every device.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | [FastAPI](https://fastapi.tiangolo.com/) 0.136.0 · Uvicorn 0.45.0 |
| Forecasting Model | [LightGBM](https://lightgbm.readthedocs.io/) 4.6.0 · scikit-learn 1.8.0 |
| Explainability | [SHAP](https://shap.readthedocs.io/) 0.51.0 |
| News Scoring | Sentence Transformers · Transformers · PyTorch |
| Database | SQLite through SQLAlchemy 2.0 (async) · Alembic 1.18 migrations |
| Frontend | [React](https://react.dev/) 18.3 · TypeScript 5.8 · Vite 5.4 · Tailwind CSS 3.4 |
| Maps and Charts | Leaflet 1.9 · Recharts 2.15 |
| Reports | jsPDF (frontend) · WeasyPrint (backend) |
| Testing | pytest (backend) · Vitest and Testing Library (frontend) |
| Language | Python 3.13 · TypeScript |

The database holds accounts, reviews, audit and feedback only. The trained model
and every data file the forecasts are read from are included in the repository,
so the system runs without downloading any data.

---

## Getting Started

### Prerequisites

Ensure you have the following installed before proceeding:

- **Python** `3.13` (developed on 3.13.2)
- **Node.js** `22` (developed on 22.14) with npm
- **Git**
- About **6 GB** of free disk space: the repository is about 450 MB, and the
  Python packages include PyTorch and the transformer libraries used for news
  scoring

You will run two programs side by side: the **backend** (the API, on port 8000)
and the **frontend** (the website, on port 8080). Use two terminal windows.

---

### Backend Setup

**1. Clone the repository**

```bash
git clone https://github.com/gwenndestura/aipheed-system.git
```

**2. Navigate into the backend folder**

```bash
cd aipheed-system/backend
```

**3. Create and activate a virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Unix / macOS
source venv/bin/activate
```

**4. Install dependencies** (this takes several minutes)

```bash
pip install -r requirements.txt

# Only needed to run the tests
pip install -r requirements-dev.txt
```

**5. Configure environment variables**

Copy the template to create `backend/.env`:

```bash
# Windows
copy .env.example .env

# Unix / macOS
cp .env.example .env
```

Open `backend/.env` and replace `SECRET_KEY=changeme` with a long random value.
You can generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Leave the other settings as they are. In particular, keep these two lines. They
make the API serve the approved production model (E196, recorded in
`backend/data/registry/registry.json`) and refuse to start rather than fall
back to an older model:

```env
AIPHEED_LEAD2_MODEL=thesis
AIPHEED_STRICT_MODEL=1
```

With `SMTP_HOST` left empty, emails (sign-up verification and password reset)
are printed in the backend terminal instead of being sent.

**6. Create the database**

```bash
python -m alembic upgrade head
```

This creates a new, empty SQLite file, `backend/aipheed.db`.

**7. Start the backend server**

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start-up takes up to a minute. The server is ready at `http://localhost:8000`
when the terminal shows:

```
Serving e196-lgbm-avg5-laf-1.0 (E196 LightGBM (E184 averaged over 5 configurations, Lead-1 lagged averaging) food-insecurity risk) on the dashboard (strict)
```

Leave this window open.

---

### Frontend Setup

**1. Open a second terminal and navigate into the frontend folder**

```bash
cd aipheed-system/frontend
```

**2. Install dependencies**

```bash
npm install
```

**3. Start the development server**

```bash
npm run dev
```

Open **http://localhost:8080** in a browser. A short guided tour appears on the
first visit to each page; it can be skipped.

The frontend calls the API at `http://localhost:8000` by default. To use another
address, copy `frontend/.env.example` to `frontend/.env` and change
`VITE_API_BASE_URL`.

---

### Check That It Works

With the backend running:

| Address | Expected |
|---|---|
| `http://127.0.0.1:8000/api/v1/health` | `{"status": "ok", ...}` |
| `http://127.0.0.1:8000/api/v1/final/food-insecurity/outlook` | `"status": "approved"`, `"model": "e196-lgbm-avg5-laf-1.0"` |
| `http://127.0.0.1:8000/api/v1/provinces?quarter=2027-Q1` | five provinces, each with a `riskScore` |

On the dashboard, the overall CALABARZON score for 2027-Q1 is **0.02** (low
risk), with Quezon the highest-risk province. The timeline shows four forecast
quarters, 2027-Q1 to 2027-Q4. The dashboard always opens on the quarter after
the current one, so the quarters move forward as the calendar does.

To browse every API route, set `ENABLE_API_DOCS=true` in `backend/.env`, restart
the backend, and open `http://127.0.0.1:8000/docs`. Keep it `false` in a
deployment.

---

### Administrator Accounts

The public dashboard needs no account. The administrator area does, and a new
database has no administrator. Create the first one from the `backend` folder:

```bash
python scripts/create_admin.py --email juan.delacruz@calabarzon.da.gov.ph --name "Juan Dela Cruz"
```

It asks for a password (at least 12 characters, not a common password). Only
`@calabarzon.da.gov.ph` addresses are accepted. Other people sign up on the
website, and an administrator approves them under **☰ menu → Accounts**.

`SETUP_GUIDE.md` explains every setting, account approval, the read-only demo
account for presentations, password resets and the checklist before going live.

---

### Map Background (optional)

The province and municipal shapes, colours and labels are drawn from files in
the repository. The street-map background underneath them is a separate
OpenStreetMap tile file, `frontend/public/basemap.pmtiles`, which is not
included because of its size. Without it the map still works on a plain
background. To add it, extract the CALABARZON area from a Protomaps build
(https://docs.protomaps.com) with the `pmtiles` command-line tool and save it as
`frontend/public/basemap.pmtiles`, or set `VITE_BASEMAP_PMTILES_URL` to a hosted
copy.

---

### Running the Tests

**Frontend**

```bash
cd frontend
npm test
npx tsc --noEmit -p tsconfig.app.json
npm run build
```

**Backend**

```bash
cd backend
python -m pytest -q --continue-on-collection-errors
```

The tests use an in-memory database and never touch `backend/aipheed.db`. Some
research-experiment tests need large third-party raw files that are not in the
repository (for example the IBTrACS typhoon archive) or check locked experiment
outputs; they report errors that do not affect the served dashboard.

---

### Keeping the Forecast Current

`backend/scripts/live_refresh_monthly.ps1` collects the newest public data and
news once a month and prepares a refreshed E168 forecast for review. Because
E196 is the production model, the refresh does not replace the E196 forecast
being served. A new E196 forecast is prepared from the `backend` folder with
`python -m app.e196.serve stage`, and the owner makes it the production
forecast with `python -m app.e196.serve promote --approver "<name>"`; restart
the backend afterwards. These are maintenance tasks for the deployed system and
are not needed to run or evaluate it. The monthly script needs the
`AIPHEED_PYTHON` environment variable to point at the Python environment that
runs the news scorer.

---

## Project Structure

```
aipheed-system/
├── backend/
│   ├── app/
│   │   ├── main.py                   # API start-up, including the strict model check
│   │   ├── api/v1/                   # HTTP endpoints (dashboard, forecast, explainability,
│   │   │                             #   final outlook, report, auth, admin)
│   │   ├── e196/                     # Served E196 model: staging, promotion, reliability and
│   │   │                             #   face-validity checks
│   │   ├── e168/                     # E168 base method: features, release gate, monthly data refresh
│   │   ├── ml/inference/
│   │   │   └── e168_system.py        # Connects the production model (E196) to every dashboard endpoint
│   │   ├── services/                 # Dashboard assembly, reports, review, accounts, security
│   │   ├── db/                       # SQLAlchemy models and Alembic migrations
│   │   └── e1xx/, fi*/               # Earlier experiments E196 builds on (E168, E178, E184 and others)
│   ├── data/
│   │   ├── e196/                     # E196 forecasts and evaluation outputs
│   │   ├── e168/                     # E168 inputs, live data and forecasts
│   │   └── registry/                 # Model registry and release-gate results
│   ├── scripts/
│   │   ├── create_admin.py           # Create and manage administrator accounts
│   │   └── live_refresh_monthly.ps1  # Monthly forecast refresh
│   ├── tests/                        # Unit, integration and end-to-end tests
│   ├── requirements.txt              # Python dependencies
│   ├── requirements-dev.txt          # Test and development tools
│   ├── .env.example                  # Settings template (copy to .env, not committed)
│   └── Dockerfile                    # Container build for deployment
│
├── frontend/
│   ├── src/
│   │   ├── pages/                    # Landing, dashboard, Data, Visualization, Admin, sign-in
│   │   ├── components/               # Map, panels, charts, modals
│   │   ├── lib/                      # API client, data adapters, PDF and CSV export
│   │   └── test/                     # Vitest tests
│   ├── public/                       # Static files, including the map background when added
│   └── package.json                  # Node dependencies and scripts
│
├── aipheed-backend-aligned/
│   └── experiments/                  # Research experiments behind the model selection,
│                                     #   with protocols, sealed results and hashes
├── docs/
│   ├── e196/                         # E196 results, reliability, face validity and objectives
│   ├── final/                        # E168 model, audit and evaluation reports
│   └── user-manual/                  # User manual (PDF and Word)
│
├── SETUP_GUIDE.md                    # Plain-language guide for the system maintainer
└── render.yaml                       # Deployment configuration
```

---

## API Reference

All endpoints are under `/api/v1`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Server health check |
| GET | `/config` | None | Dashboard settings and thresholds |
| GET | `/quarters` | None | Quarters available on the timeline |
| GET | `/provinces` | None | Risk score and level for every province in a quarter |
| GET | `/provinces/{province_id}/municipalities` | None | Municipal detail for one province |
| GET | `/ranking` | None | Provinces ranked by risk |
| GET | `/forecast` | None | Forecast for a province or the region |
| GET | `/forecast/timeseries` | None | Forecast history over a range of quarters |
| GET | `/explainability` | None | Driver shares (SHAP) and explanations |
| GET | `/news` | None | News reports used by the forecast |
| GET | `/search` | None | Search provinces and municipalities |
| GET | `/final/food-insecurity/outlook` | None | Approved E196 forecast for the coming quarters |
| GET | `/final/model-registry` | None | Registered models and the production model |
| GET | `/report` | None | Assessment report as PDF |
| POST | `/feedback` | None | Submit user feedback |
| POST | `/auth/signup` | None | Request an administrator account |
| POST | `/auth/login` | None | Sign in |
| POST | `/auth/refresh` | Refresh cookie | Renew the session |
| POST | `/auth/logout` | Signed in | Sign out |
| GET | `/admin/review` | Administrator | Forecasts waiting for review |
| POST | `/admin/review/{item_id}/approve` | Administrator | Approve a forecast |
| POST | `/admin/review/{item_id}/reject` | Administrator | Reject a forecast |
| GET | `/admin/accounts` | Administrator | Accounts and pending requests |
| GET | `/admin/audit` | Administrator | Audit log |
| GET | `/admin/feedback` | Administrator | User feedback |

**Sample request:**

```
GET /api/v1/provinces?quarter=2027-Q1
```

**Sample response** (one province shown, fields shortened):

```json
{
  "quarter": "2027-Q1",
  "data": [
    {
      "id": "quezon",
      "name": "Quezon",
      "currentQuarter": "2027-Q1",
      "riskScore": 0.052,
      "riskLevel": "low",
      "qoqChange": -0.007
    }
  ]
}
```

---

## Documentation

| Document | Contents |
|---|---|
| [aiPHeed User Guide (PDF)](https://drive.google.com/file/d/1jTWFy2kj809mipEthBBRTCXNMAjYIO49/view?usp=drive_link) | Guide for the system's users |
| `SETUP_GUIDE.md` | Plain-language guide for the person who maintains the system |
| `docs/e196/REPORT.md` | How E196 was chosen and its accuracy at each lead |
| `docs/e196/RELIABILITY.md` | Reliability checks, including the adjusted accuracy estimate |
| `docs/e196/FACE_VALIDITY.md` | E196 forecasts compared with DOST-FNRI CALABARZON figures |
| `docs/e196/OBJECTIVES.md` | The study's specific objectives checked against the E196 system |
| `docs/final/FINAL_SYSTEM_REPORT_E168.md` | The E168 base model that E196 builds on |
| `docs/final/LEAKAGE_AUDIT_E168.md` | Check that no future information leaks into the E168 forecasts |
| `docs/e158_frontend_verification/FINAL_FRONTEND_MODEL_VERIFICATION.md` | End-to-end check that the model's output reaches the screen unchanged |
| `docs/final/iso25010/` | ISO/IEC 25010 software quality evaluation material |

---

## Development Team

| Name |
|---|
| Princess Gwenn A. Destura |
| Christina M. Esico |
| Angel Vhea P. Melindo |

---

<div align="center">
  <sub>Developed as a thesis for the Bachelor of Science in Computer Science with Intelligent Systems Track<br/>at De La Salle University - Dasmariñas. The Department of Agriculture did not develop aiPHeed and has not endorsed it.</sub>
</div>
