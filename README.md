# AquaWise Alberta

Understand the water beneath your property. A React + FastAPI app that reads Alberta water-well records from
Databricks, lets residents explore wells around a point, compare two properties, and ask questions through Databricks Genie.

> **Status:** built and tested against mocks and a synthetic demo fixture. **Live Databricks integration is NOT VERIFIED**
> (no workspace access when this was built). See [Known gaps](#known-gaps--not-verified).

## Quick start (demo mode, no Databricks needed)

Demo mode serves **synthetic, randomly generated wells** under a permanent banner. It exists only to run the UI.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
./scripts/build.sh                                  # builds React into backend/static
AQUAWISE_DEMO_MODE=true uvicorn backend.main:app --port 8000
# open http://localhost:8000
```
Frontend dev server with hot reload: `cd frontend && npm install && npm run dev` (proxies `/api` to :8000; set `CORS_ORIGINS` only if you bypass the proxy).

## Connect to Databricks

1. **Credentials** — copy `.env.example` to `.env` and set `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and auth
   (`DATABRICKS_TOKEN`, OAuth client id/secret, or a CLI profile). Secrets stay on the backend; nothing is bundled into the browser.
2. **Inspect the real schema** (the code assumes no table or column names):
   ```bash
   python scripts/discover_schema.py      # writes databricks/schema_inventory.md
   ```
3. **Map it** — fill the `WELLS_*` / `QUALITY_*` variables in `.env` with names you confirmed, plus the **units**
   (`WELLS_DEPTH_UNIT`, `WELLS_YIELD_UNIT`). Optional columns that are blank simply show "Not available".
   Optionally create curated views from `databricks/views.sql` (a template with placeholders) and map to those.
4. **Check** — `curl localhost:8000/api/health?deep=true` reports mode, enabled features, and any missing/unknown columns.
5. **Genie** — follow `databricks/genie_instructions.md`, then set `GENIE_SPACE_ID`.

| Variable | Purpose |
|---|---|
| `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` (+auth) | connection |
| `GENIE_SPACE_ID` | enables Ask AquaWise |
| `WELLS_TABLE`, `WELLS_COL_ID/LATITUDE/LONGITUDE` | **required** mapping |
| `WELLS_COL_DEPTH/YIELD/STATIC_WATER_LEVEL/DRILL_DATE/STATUS`, `*_UNIT` | optional mapping + units |
| `LOW_YIELD_THRESHOLD` | low-yield count (in yield units); blank = hidden |
| `QUALITY_TABLE`, `QUALITY_COL_*`, `QUALITY_GUIDELINES_FILE` | water quality (long format) and optional guideline reference |
| `GEOCODER_URL` | optional place search (Nominatim-compatible) |
| `AQUAWISE_DEMO_MODE` | explicit opt-in to synthetic data |
| `CACHE_TTL_SECONDS`, `DB_POOL_SIZE`, `QUERY_TIMEOUT_SECONDS`, `GENIE_TIMEOUT_SECONDS`, `HIST_*`, `MIN_SAMPLE_SIZE` | tuning |

## Deploy as a Databricks App

1. `./scripts/build.sh` (the compiled app must be in `backend/static`; it is not git-ignored so it gets uploaded).
2. Create the app; add resources with keys `sql-warehouse` (Can use) and `genie-space` (Can run); fill the mapping in `app.yaml`.
3. Grant the app's **service principal** `USE CATALOG`, `USE SCHEMA`, `SELECT` on the data, and access to the Genie space.
4. `databricks sync . /Workspace/Users/<you>/aquawise-alberta` then `databricks apps deploy <app-name> --source-code-path /Workspace/Users/<you>/aquawise-alberta`.

Map tiles load from openstreetmap.org; if your workspace blocks it, set another tile URL in `frontend/src/components/WellMap.tsx`.

## API

All under `/api`: `GET health`, `GET wells/nearby`, `GET wells/{id}`, `GET groundwater/summary`, `GET water-quality`,
`POST properties/compare`, `POST genie/chat`, `GET geocode` (optional). Latitude −90..90, longitude −180..180, radius ∈ {1,2,5,10,20} km,
limit 1..1000, question ≤ 1000 chars. Errors are JSON `{"error": {"code", "message"}}` and never contain secrets or SQL.

## How numbers are calculated (assumptions)

- Distance: great-circle (haversine), kilometres, after a bounding-box prefilter. Invalid, missing and (0,0) coordinates are excluded.
- One row per well: duplicates are collapsed by well ID (most recent drilling date kept). Counts are distinct wells.
- "Typical" = median, nulls ignored; sample sizes always shown. Depth ≤ 0 is treated as missing; yield 0 is kept as a real value.
- Counts and medians cover **all** wells in the radius; the map/table show the nearest `limit` (default 500).
- Comparison text is a fixed template over the computed values ("similar" = medians within 10 %); it never says water is safe.
- Guidelines: none shipped. Without `QUALITY_GUIDELINES_FILE`, every measurement is "Not evaluated". Unit mismatches are also "Not evaluated".

## Performance

Pooled warehouse sessions, parallel statements per request, TTL cache (backend) and request cache (browser), SQL-side histograms,
background warm-up at start (a stopped warehouse still needs its own start-up time), lazy-loaded pages/map/charts
(first screen ≈ 65 kB gzipped), canvas map markers, tabs kept mounted so switching is instant.

## Tests

```bash
python -m pytest -q                   # 86 backend tests (mocked Databricks/Genie; SQL parsed with sqlglot)
cd frontend && npm test && npm run build
```

## Known gaps / NOT VERIFIED

- **Live Databricks: NOT VERIFIED.** The generated SQL is syntax-checked but has not run on a warehouse (`QUALIFY`, `percentile`, `TRY_CAST`,
  named parameters, `STATEMENT_TIMEOUT` session setting). Verify one location end-to-end: compare `/api/groundwater/summary`
  with a hand-written SQL count/median for the same point.
- **Genie: NOT VERIFIED.** Written against the `databricks-sdk` Genie API (checked by introspection), exercised only with mocks.
- **Deployment: NOT VERIFIED.** `app.yaml` resource keys and commands follow the docs but were never deployed.
- Unreachable workspace: the request fails with a friendly 502 after ≈ 30 s (bounded retries).
- Geological information and well-level status beyond the mapped columns are not shown. Wide-format quality tables must be unpivoted first.
- Map markers are not keyboard-focusable; the wells table provides the keyboard path. No formal accessibility audit was run.
- No PDF export, favourites, or authentication (out of MVP scope).
