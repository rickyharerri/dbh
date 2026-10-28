# AquaWise Alberta — MVP Build Agent Instructions

## Mission
Build a working, simple, accessible React web app for Alberta residents to explore historical water-well records, compare two locations, and ask grounded questions using Databricks Genie. Prioritize a demoable end-to-end experience over decorative UI or speculative analytics.

## Working rules
- Implement code, not just a plan. Inspect the repository and available Databricks schema first.
- Never invent source table names, column names, quality measurements, well statistics, or Genie results.
- If credentials or Databricks resources are unavailable, create a clearly labelled demo mode with fixture data, but never present fixtures as real findings.
- Keep UI plain: white background, teal/blue accents, readable cards, simple tabs, no authentication for MVP.
- Keep secrets server-side. Do not put Databricks tokens, warehouse IDs, or privileged credentials into browser bundles.
- Commit changes in small logical units if git is configured; do not overwrite unrelated user work.
- Document setup, environment variables, deployment steps, and known gaps in README.md.

## Stack and structure
- Frontend: React, TypeScript, Vite, Tailwind CSS, React Leaflet, Recharts.
- Backend: Python FastAPI with Pydantic request validation.
- Data: Databricks SQL Warehouse and Unity Catalog Delta tables/views.
- AI: Databricks Genie Conversation API via backend only.
- Deployment: single Databricks App, with FastAPI serving compiled React assets and `/api/*` routes.

Suggested layout:
```
aquawise-alberta/
  frontend/src/{components,pages,services,types}/
  backend/{routes,services,tests}/
  databricks/{schema_inventory.sql,views.sql,genie_instructions.md}/
  app.yaml
  README.md
  .env.example
```

## First actions — required
1. Inspect existing files and follow established conventions where reasonable.
2. Discover Databricks connectivity, credentials, SQL warehouse, Genie Space, and Unity Catalog permissions from runtime environment; never print secrets.
3. Inspect tables under `calgary_agent_hackathon.alberta_water_well_data` (if available), using `SHOW TABLES` and `information_schema.columns`.
4. Identify actual location fields, unique well IDs, drilling depth, yield, units, dates, water-quality records, and joins. Write the mapping to `databricks/schema_inventory.md`.
5. If a required field is absent, disable the dependent UI or show “Not available”; do not synthesize it.

## MVP functionality and acceptance criteria
### 1. Explore Property (P0)
- Map focused on Alberta. User can click a point or enter valid latitude/longitude; optional place-name search only if geocoding is configured.
- Radius options: 1, 2, 5, 10, 20 km; default 5 km.
- “Analyze Groundwater” retrieves nearby well points from backend; show map markers and a selectable well-details panel.
- Cards: total nearby wells, median depth, median yield, count of wells with quality observations. Display sample sizes and units. Missing values are not zeros.
- Charts: depth and yield distributions, only when measurements exist.

### 2. Compare Properties (P0)
- Independently select two locations and shared radius.
- Compare counts, median depth/yield, quality-data coverage, and sample sizes.
- Provide a deterministic plain-language summary based only on computed values. Do not assert which property has safe water or guaranteed supply.

### 3. Ask AquaWise (P0)
- Simple chat UI with suggested questions, follow-ups, loading, errors, and clear conversation.
- Backend starts/continues Genie conversations using configured Space ID; handle asynchronous completion with bounded polling and timeouts.
- Return Genie text and structured tabular results where supported. If unavailable, show a clear “AI assistant not configured” state rather than fake answers.
- Do not imply that Genie knows the selected map location unless coordinates/radius are explicitly included in its supported context or curated query workflow.

### 4. Water Quality (P1, data-dependent)
- Display actual historical measurements only if present in source data.
- Show parameter, value, unit, sample date, well ID, and guideline only if a trustworthy, versioned reference has been configured.
- Distinguish “No data,” “Not evaluated,” “Within guideline,” and “Above guideline.” No unsupported contamination scoring.
- Always display: “Historical nearby records do not establish whether water at this property is safe to drink. Test your own water.”

## API contract
- `GET /api/health` — backend readiness (optionally include non-secret service status).
- `GET /api/wells/nearby?latitude=&longitude=&radius_km=&limit=` — filtered well points, total count, returned count, pagination/limit metadata.
- `GET /api/groundwater/summary?latitude=&longitude=&radius_km=` — metrics plus sample counts and units.
- `GET /api/wells/{well_id}` — source-backed well details.
- `GET /api/water-quality?latitude=&longitude=&radius_km=` — observed measurements, or empty data with explanation.
- `POST /api/properties/compare` — two coordinates and radius; same metric definitions for both.
- `POST /api/genie/chat` — message, optional conversation_id, optional explicit location context; response with conversation/message IDs, status, answer and optional table.

Validate latitude [-90,90], longitude [-180,180], allowed radius values, reasonable limits, and maximum question length. Use parameter binding and allowlisted table/view identifiers; never interpolate untrusted input into SQL. Limit result size and implement timeouts.

## Databricks implementation
- Use Databricks SQL Connector or supported Databricks SDK in FastAPI.
- Build curated SQL views from verified schema; avoid assuming table names beyond the catalog/schema path.
- Use available Databricks spatial SQL functions if supported, otherwise a documented, validated great-circle distance expression. Ensure kilometres and proper coordinate order.
- Count distinct well IDs when joins can duplicate records. Median calculations must ignore nulls; show measurement sample counts.
- Maintain a documented Genie Space setup file listing curated tables, joins, semantic instructions, example questions, and required permissions.
- Configure Databricks App service principal permissions and environment resources according to the actual workspace; do not hardcode personal access tokens.

## UI expectations
- Header: “AquaWise Alberta” and tagline “Understand the water beneath your property.”
- Four tabs: Explore Property, Water Quality, Compare Properties, Ask AquaWise.
- Visible empty, loading, and failure states. No dead buttons.
- Mobile-friendly layout, accessible labels, keyboard navigation, and plain-language tooltips.
- Display “Historical records — not a water safety certification” on relevant analysis views.

## Testing and definition of done
- Unit tests: coordinate/radius validation, distance filtering, distinct counts, median/null handling, comparisons, API errors.
- Backend integration tests with mocked Databricks/Genie clients; avoid live credentials in CI.
- Frontend smoke test: map selection, radius change, summary, comparison, chat loading/error.
- Build succeeds (`npm run build`); Python tests pass; backend serves React and `/api` routes.
- With real Databricks access: verify at least one location end-to-end, inspect raw query results, and confirm Genie responds to a grounded question.
- Without access: mark live integration **NOT VERIFIED** and list exact required configuration in README.

## Execution order
1. Schema inventory and mapping.
2. FastAPI connection layer and nearby-well/summary endpoints.
3. React shell, map, metrics, well details.
4. Property comparison.
5. Genie chat integration.
6. Water-quality module if supported.
7. Tests, responsive polish, Databricks App deployment, README.

## Final handoff format
Report: implemented features, files created, commands to run locally, Databricks configuration still required, tests run and outcomes, deployment status, and any features blocked by missing fields or permissions. Do not claim untested integration works.
