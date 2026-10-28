# Genie space: AquaWise Alberta Groundwater Intelligence

Setup for the Genie space the app talks to. The backend only ever calls the space whose ID is in `GENIE_SPACE_ID`.
**Nothing below has been created or verified against a workspace yet** (no Databricks access when this was written).

## 1. Create the space
- **Name:** `AquaWise Alberta Groundwater Intelligence`
- **SQL warehouse:** the same (or a compatible) warehouse the app uses.
- **Tables / views** (add only objects you verified in `schema_inventory.md`):
  | Object | Purpose |
  |---|---|
  | `…alberta_water_well_data.v_well_measurements` (or the confirmed source well table) | one row per well: location, depth, yield, dates |
  | `…alberta_water_well_data.v_water_quality` (if a quality table exists) | long-format lab observations |
- **Joins:** `v_water_quality.well_id = v_well_measurements.well_id` (many-to-one). Tell Genie to `COUNT(DISTINCT well_id)`.
- Add column comments (units!) in Unity Catalog so Genie reads them: depth unit, yield unit, “NULL = not recorded”.

## 2. General instructions (paste into the space)
```
You answer questions about historical Alberta water-well records.
- Use ONLY the tables in this space. If a measurement or table is not available, say so plainly. Never invent values.
- Always state units (for example metres for depth, and the recorded yield unit). Use the units from the column comments.
- Missing values are NULL, not zero. Exclude NULLs from statistics and say how many wells the figure is based on.
- Prefer the MEDIAN for "typical" values. Use COUNT(DISTINCT well_id) when counting wells, especially after joins.
- These are HISTORICAL records, often decades old. Do not describe them as current conditions.
- Never state or imply that water is safe or unsafe to drink, and never predict how a specific well will perform.
  Suggest laboratory testing of the person's own water when quality comes up.
- If a question needs coverage context (few wells, many missing values), mention the limitation.
- Explain technical terms in plain language. "Static water level" = depth to water below ground when measured.
- For "near <place>" questions use latitude/longitude and great-circle distance in kilometres:
  2 * 6371.0088 * asin(sqrt(pow(sin(radians((latitude - :lat)/2)),2) + cos(radians(:lat))*cos(radians(latitude))*pow(sin(radians((longitude - :lon)/2)),2)))
  If the question does not include coordinates or a radius, ask the user to provide them or use a clearly stated assumption.
```
If the user supplies location context, the app appends it to the question as text, e.g.
`[Location context supplied by the user … latitude 51.19000, longitude -114.47000, search radius 5 km …]`.
Genie **does not** otherwise know which point is selected on the map.

## 3. Example questions / sample SQL (add after verifying column names)
| Question | Notes |
|---|---|
| How many wells are within 5 km of latitude 51.19, longitude -114.47? | great-circle filter above |
| What is the median well depth within 10 km of … ? | `percentile(depth, 0.5)`, report depth sample count |
| Which nearby wells have recorded yield below `<threshold>`? | threshold must match `LOW_YIELD_THRESHOLD` |
| What water-quality parameters have been recorded near … ? | `GROUP BY parameter`, distinct wells |
| How many wells have no recorded depth? | `COUNT(*) FILTER (WHERE depth IS NULL)` |

The app's suggested questions mention Cochrane and Okotoks. Genie can only answer place-name questions if place names exist
in the data (or you teach it coordinates for them as instructions); otherwise it should ask for coordinates.

## 4. Permissions the app's identity needs
The app calls Genie **as the Databricks App service principal** (`DATABRICKS_CLIENT_ID` / `SECRET` are injected automatically).
Grant that principal:
- **CAN RUN** on the Genie space;
- **CAN USE** on the SQL warehouse;
- `USE CATALOG` on `calgary_agent_hackathon`, `USE SCHEMA` on `alberta_water_well_data`, and `SELECT` on every table/view in the space.
For local development the same permissions are needed for whatever identity your `DATABRICKS_TOKEN` belongs to.

## 5. Wire it up
Copy the space ID (from the space URL) into `GENIE_SPACE_ID`. Verify with a grounded question in the **Ask AquaWise** tab and
confirm the “View the query” section shows SQL against the expected tables.
