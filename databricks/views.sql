-- ============================================================================================
-- TEMPLATE — NOT RUNNABLE AS-IS.
-- Replace every <PLACEHOLDER> with a name you verified in schema_inventory.md. Nothing here is a
-- confirmed table or column. These views are optional: the app can map directly to source tables via
-- .env, but curated views give BOTH the app and Genie clean, documented column names.
--
-- If you create them, point the app at the views (WELLS_TABLE=v_well_measurements,
-- WELLS_COL_ID=well_id, WELLS_COL_LATITUDE=latitude, ...) and add them to the Genie space.
-- ============================================================================================

-- 1) Well locations + measurements: ONE ROW PER WELL (de-duplicate here if the source has several rows per well)
CREATE OR REPLACE VIEW calgary_agent_hackathon.alberta_water_well_data.v_well_measurements
COMMENT 'Historical Alberta water wells: one row per well with location, depth, yield and dates. Historical records, not current conditions.'
AS
SELECT
  CAST(<WELL_ID_COL> AS STRING)                    AS well_id,
  TRY_CAST(<LAT_COL> AS DOUBLE)                    AS latitude,    -- decimal degrees north
  TRY_CAST(<LON_COL> AS DOUBLE)                    AS longitude,   -- decimal degrees east (negative = west)
  TRY_CAST(<DEPTH_COL> AS DOUBLE)                  AS depth,       -- UNIT: <confirm: metres or feet>
  TRY_CAST(<YIELD_COL> AS DOUBLE)                  AS well_yield,  -- UNIT: <confirm: e.g. gpm or L/min>
  TRY_CAST(<STATIC_WATER_LEVEL_COL> AS DOUBLE)     AS static_water_level,
  TRY_CAST(<DRILL_DATE_COL> AS DATE)               AS drilling_date,
  CAST(<STATUS_COL> AS STRING)                     AS status
FROM calgary_agent_hackathon.alberta_water_well_data.<WELL_TABLE>
WHERE <WELL_ID_COL> IS NOT NULL
  AND TRY_CAST(<LAT_COL> AS DOUBLE) BETWEEN -90 AND 90
  AND TRY_CAST(<LON_COL> AS DOUBLE) BETWEEN -180 AND 180
QUALIFY ROW_NUMBER() OVER (PARTITION BY <WELL_ID_COL> ORDER BY <DRILL_DATE_COL> DESC NULLS LAST) = 1;

-- Column comments help Genie (and people) understand units and meaning:
-- ALTER VIEW ... ALTER COLUMN depth COMMENT 'Drilled depth in <unit>. NULL = not recorded.';

-- 2) Water quality: LONG format (one row per well × parameter × sample)
CREATE OR REPLACE VIEW calgary_agent_hackathon.alberta_water_well_data.v_water_quality
COMMENT 'Historical laboratory observations for wells. NULL value = no usable number. Not a safety assessment.'
AS
SELECT
  CAST(<QUALITY_WELL_ID_COL> AS STRING)   AS well_id,
  CAST(<PARAMETER_COL> AS STRING)         AS parameter,
  <VALUE_COL>                              AS value,       -- keep raw text if values such as "<0.5" occur
  CAST(<UNIT_COL> AS STRING)              AS unit,
  TRY_CAST(<SAMPLE_DATE_COL> AS DATE)     AS sample_date
FROM calgary_agent_hackathon.alberta_water_well_data.<QUALITY_TABLE>;

-- If the source quality table is WIDE (one column per parameter), unpivot it instead, e.g.:
-- SELECT well_id, parameter, value, unit, sample_date
-- FROM <wide_table>
-- UNPIVOT (value FOR parameter IN (<col_a> AS 'Iron', <col_b> AS 'Nitrate', ...));
-- (units must then be supplied explicitly from the data dictionary — never guessed)

-- 3) Optional: pre-aggregated per-well quality coverage, useful for Genie questions
-- CREATE OR REPLACE VIEW ...v_well_quality_coverage AS
-- SELECT well_id, COUNT(*) AS observations, COUNT(DISTINCT parameter) AS parameters, MAX(sample_date) AS latest_sample_date
-- FROM ...v_water_quality WHERE value IS NOT NULL GROUP BY well_id;
