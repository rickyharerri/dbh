-- Step 1 of the build: inspect the real schema before mapping anything.
-- Run in a Databricks SQL editor (or let scripts/discover_schema.py do it and write schema_inventory.md).

SHOW TABLES IN calgary_agent_hackathon.alberta_water_well_data;

SELECT table_name, column_name, data_type, ordinal_position
FROM calgary_agent_hackathon.information_schema.columns
WHERE table_schema = 'alberta_water_well_data'
ORDER BY table_name, ordinal_position;

-- Once you know the well table, eyeball a few rows and the coordinate/units columns:
-- SELECT * FROM calgary_agent_hackathon.alberta_water_well_data.<WELL_TABLE> LIMIT 20;
-- SELECT COUNT(*) AS rows, COUNT(DISTINCT <ID_COL>) AS distinct_wells FROM calgary_agent_hackathon.alberta_water_well_data.<WELL_TABLE>;
-- SELECT MIN(<LAT_COL>), MAX(<LAT_COL>), MIN(<LON_COL>), MAX(<LON_COL>) FROM calgary_agent_hackathon.alberta_water_well_data.<WELL_TABLE>;
