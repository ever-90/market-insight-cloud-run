# Market Insight — Cloud Run (Phase 3)

Multi-tenant SaaS port of the Apps Script v205 reference. Same business logic, FastAPI + Firestore + Cloud Run.

## What's here

```
cloud_run/
├── app/
│   ├── main.py                  # FastAPI entry + CORS + middleware
│   ├── config.py                # Env-driven settings
│   ├── auth/firebase_auth.py    # JWT + API key verification
│   ├── services/
│   │   ├── firestore_client.py  # Real + in-memory backend
│   │   ├── bq_client.py         # BigQuery (real + test fakes)
│   │   └── search_engine.py     # Port of _searchByCategory_ / _searchByKeyword_
│   └── routers/                 # 13 endpoints
│       ├── search.py            POST /api/search
│       ├── analytics.py         GET  /api/analytics
│       ├── pricing.py           GET  /api/category-pricing
│       ├── market_size.py       GET  /api/market-size
│       ├── history.py           GET  /api/search-history
│       ├── favorites.py         CRUD /api/favorites
│       ├── brand_compare.py     POST /api/brand-compare
│       ├── export_csv.py        GET  /api/export-csv/*  (4 variants)
│       └── timeseries.py        GET  /api/{timeseries,quarterly,brand-trend,cagr,yoy}
├── tests/                       # 16 pytest cases (all PASS)
├── migrations/v205_to_firestore.py
├── Dockerfile
├── cloudbuild.yaml
├── monitoring.yaml
└── requirements.txt
```

## Local dev

```bash
cd cloud_run
pip install -r requirements.txt
TEST_MODE=true uvicorn app.main:app --reload
# http://localhost:8080/health
```

```bash
TEST_MODE=true python -m pytest tests/ -v
# 16 passed
```

## Multi-tenant model

All user data lives under `users/{user_id}/...` subcollections. Every API route
extracts `user_id` from the Firebase ID token (or API key) and scopes Firestore
reads/writes accordingly. The shared collection `global_category_pricing/{category}`
is read-only across tenants.

## Auth

Two paths:
- **Firebase ID token** — `Authorization: Bearer <token>` (web app via Firebase Auth)
- **API key** — `X-API-Key: <key>` (B2B integrations). Keys stored under `api_keys/{key}`
  collection with `{ user_id, email, active }`.

Test mode accepts tokens of the form `test-<uid>-<email>`.

## Deploy

1. Provision a GCP project + Firestore (native mode) + Firebase Auth.
2. Set `gcloud config set project <PROJECT_ID>` and `gcloud config set run/region asia-northeast3`.
3. Submit a build: `gcloud builds submit --config cloudbuild.yaml`.
4. Wire a Cloud Build trigger to GitHub `main` for auto-deploy on push.

## Observability

See `monitoring.yaml` — alert policies for 5xx rate, P95 latency, Firestore quota,
plus SLO definitions (99.9% availability, 95% P95 < 1.5s) and a Firestore export
backup schedule.

## Migration from v205

```bash
# 1. Export from Apps Script
#    Hit /api/export-csv/brand-mapping etc. on the v205 webapp endpoint
#    OR call exportBrandMappingToCSV() directly in the editor.
# 2. Place CSVs in a folder
# 3. Run:
python migrations/v205_to_firestore.py --user-id <uid> --dir ./v205_csvs
```

## Cost envelope

| Component | Free-tier coverage | Expected monthly cost |
|---|---|---|
| Cloud Run (256 MB, scale-to-zero) | 2M requests | $0–2 |
| Firestore (1 GB + 50k reads/day) | 1 GiB + 50k reads | $0–2 |
| BigQuery (50 GB partitioned scans) | 1 TB/month free | $1–5 |
| Cloud Storage (signed URLs for CSV) | 5 GB | <$1 |
| Cloud Scheduler (3 jobs) | 3 free | $0 |
| Firebase Auth | 50k MAU free | $0 |
| **Total** | | **≈ $5–10/month** |

Multi-tenant public-facing scale (≥100 active users) pushes to $30–60/month.
