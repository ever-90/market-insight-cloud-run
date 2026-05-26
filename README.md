# Market Insight — Tier-based Market Analysis SaaS

![tests](https://img.shields.io/badge/tests-16%2F16%20passing-brightgreen) ![phase](https://img.shields.io/badge/phase-3%20skeleton-blue) ![license](https://img.shields.io/badge/license-MIT-yellow)

Multi-tenant B2B food / health-supplement market-analysis SaaS, built on public production data. FastAPI + Firestore + Firebase Auth + Cloud Run, with a React + Vite frontend.

> **Honest limitation.** Absolute revenue cannot be derived from public production data. This system surfaces **relative ranking** and **market influence** signals — not point revenue numbers. See the Tier System section for the confidence model.

---

## Overview

| Stack layer | Choice |
|---|---|
| API | **FastAPI** (Python 3.11) on **Cloud Run** |
| Datastore (per-tenant) | **Firestore** (native mode) |
| Datastore (read-only public) | **BigQuery** (public production data) |
| Auth | **Firebase Auth** (Google OAuth) + optional API keys for B2B |
| Frontend | **React 18 + Vite + Tailwind + Chart.js** |
| CI / Deploy | **Cloud Build** triggered by GitHub `main` |
| Observability | Cloud Logging + Cloud Monitoring (5xx, P95 latency, Firestore quota) |

---

## Architecture

```
                +----------------+
   Browser ---> | Firebase Auth  | (Google OAuth) -- issues --> ID token
                +-------+--------+
                        | Bearer <token>
                        v
                +----------------+
   API key --> |  Cloud Run     |  FastAPI (this repo)
                |  market-insight-api
                +-+--------------+
                  |
       +----------+----------+
       v                     v
 +-----------+         +--------------+
 | Firestore |         |  BigQuery    |
 | users/{uid}/...     |  (read-only) |
 +-----------+         +--------------+
```

Tenant isolation is enforced at the data-access layer: every router resolves
`user_id` from the verified token and scopes Firestore reads/writes accordingly.
The isolation is verified by `tests/test_endpoints.py::test_tenant_isolation`.

---

## Tier System

| Tier | When | Confidence | Description |
|---|---|---|---|
| **Tier 1** | keyword matches a configured `category_mapping` (substring, bidirectional) | ~ 80%+ | Brand-level grouping via `brand_mapping`. Returns mapped brands + remainder + `mapping_coverage %`. |
| **Tier 0** | no category match | ~ 60% | Plain keyword search on `product_name`. Result keyword is auto-enqueued in `discovery_queue` for review. |

The `mapping_coverage %` (mapped_kg / total_kg) is the system's own honesty dial — when it's low, treat brand share figures with caution. Confidence per brand (H / M / L) reflects how many independent data sources agree on that mapping.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe (unauth) |
| POST | `/api/search` | Tier-based market search |
| GET | `/api/analytics` | 30-day usage analytics |
| GET | `/api/cagr` | Compound annual growth rate (needs 3+ months of snapshots) |
| GET | `/api/yoy` | Year-over-year growth (needs 13+ months) |
| GET | `/api/category-pricing` | Avg price per kg (shared `global_category_pricing`) |
| GET | `/api/market-size` | Estimated market size = total_kg x avg_price |
| GET | `/api/search-history` | User search history (default last 7 days) |
| GET / POST / DELETE | `/api/favorites` | Favorites CRUD |
| POST | `/api/brand-compare` | Multi-brand monthly series (up to 5 brands) |
| GET | `/api/timeseries` | Monthly production time series for a category |
| GET | `/api/quarterly` | Quarterly comparison |
| GET | `/api/brand-trend` | Brand-specific monthly series |
| GET | `/api/export-csv/search` | CSV of a search result |
| GET | `/api/export-csv/brand-mapping` | Tenant's `brand_mapping` as CSV |
| GET | `/api/export-csv/category-mapping` | Tenant's `category_mapping` as CSV |
| GET | `/api/export-csv/monthly-snapshots` | Snapshot history as CSV |

All routes except `/health` require either a Firebase ID token in `Authorization: Bearer <token>` or an API key in `X-API-Key`.

---

## Multi-tenant model

Every per-tenant write lands under `users/{user_id}/...`. The middleware verifies the token, sets `request.state.user`, and routers pass `user.user_id` to the data layer.

```
users/{user_id}                            # profile + plan
  brand_mappings/{auto_id}
  category_mappings/{auto_id}
  search_history/{auto_id}
  favorites/{auto_id}
  monthly_snapshots/{auto_id}
  error_logs/{auto_id}
api_keys/{key}                             # B2B integrations
global_category_pricing/{category}         # shared, read-only
```

---

## Test coverage

```
$ TEST_MODE=true pytest cloud_run/tests/ -v
16 passed in 0.19s
```

Cases cover the health probe, JWT enforcement, Tier 1 / Tier 0 search paths, favorites CRUD, history retrieval, time-series and CAGR / YoY insufficient-data branches, analytics roll-up, brand comparison, CSV export, and explicit cross-tenant isolation.

---

## Quick start (5 min)

```bash
git clone https://github.com/ever-90/market-insight-cloud-run.git
cd market-insight-cloud-run/cloud_run
pip install -r requirements.txt
TEST_MODE=true pytest                           # 16/16 expected
TEST_MODE=true uvicorn app.main:app --reload    # http://localhost:8080/health
```

---

## Deploy to Cloud Run

```bash
cp .env.example .env       # fill GCP_PROJECT, FIREBASE_PROJECT, ...
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region asia-northeast3

gcloud services enable run.googleapis.com firestore.googleapis.com \
    cloudbuild.googleapis.com firebase.googleapis.com bigquery.googleapis.com

gcloud builds submit --config cloud_run/cloudbuild.yaml cloud_run/
```

After the first build, wire a Cloud Build trigger pointed at this repo's `main` branch for push-to-deploy.

---

## Frontend (React + Vite)

```bash
cd frontend
cp ../.env.example .env.local   # set VITE_FIREBASE_* and VITE_API_BASE
npm install
npm run dev                     # http://localhost:5173
npm run build                   # -> dist/
```

---

## Observability

`cloud_run/monitoring.yaml` defines alert policies, SLOs (99.9% availability, 95% of requests under 1.5s P95), and a daily Firestore export. Apply via `gcloud monitoring` or import into Terraform.

---

## Roadmap

- [x] Phase 3.1 Cloud Run skeleton
- [x] Phase 3.2 Firestore schema + migration script
- [x] Phase 3.3 13 endpoints
- [x] Phase 3.4 Auth (Firebase + API key) + multi-tenant isolation
- [x] Phase 3.5 React frontend skeleton
- [x] Phase 3.6 Monitoring + SLO + Stripe spec
- [ ] Phase 3.7 Production deploy + Cloud Build trigger
- [ ] Phase 3.8 Real Firestore (replace in-memory test backend)
- [ ] Phase 3.9 Stripe subscriptions (see `cloud_run/STRIPE_SPEC.md`)
- [ ] Phase 4 OpenAPI docs + B2B SDK

---

## Cost envelope

| Component | Free tier covers | Expected monthly cost |
|---|---|---|
| Cloud Run (256 MB, scale-to-zero) | 2M requests | $0-2 |
| Firestore | 1 GiB + 50k reads/day | $0-2 |
| BigQuery | 1 TB/month free scan | $1-5 |
| Cloud Storage (CSV / backups) | 5 GB | < $1 |
| Cloud Scheduler | 3 jobs free | $0 |
| Firebase Auth | 50k MAU free | $0 |
| **Total** | | **~ $5-10 / month** |

Multi-tenant production scale (>= 100 active users): roughly $30-60 / month.

---

## Contributing

Bug reports and pull requests welcome. Please keep changes scoped, add a test under `cloud_run/tests/`, and confirm `TEST_MODE=true pytest` is green before opening a PR.

---

## License

MIT — see `LICENSE`.
