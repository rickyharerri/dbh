# Schema inventory: `calgary_agent_hackathon.alberta_water_well_data`

**STATUS: NOT YET RUN.** No Databricks access was available when this project was generated, so no table or column
names have been inspected — and none are assumed anywhere in the code.

To produce the real inventory (needs `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and credentials in `.env`):

```bash
source .venv/bin/activate
python scripts/discover_schema.py        # overwrites this file with the real tables, columns, and suggested mapping
```

Equivalent SQL (run in a SQL editor) is in [`schema_inventory.sql`](schema_inventory.sql).
Then copy the confirmed names into `.env` (see `.env.example`).
