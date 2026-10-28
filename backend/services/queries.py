"""SQL builders (Databricks / Spark SQL).

Safety rules:
  * User-supplied values (coordinates, radius, ids, thresholds) are ALWAYS bound
    as named parameters (:name). They are never formatted into the SQL string.
  * Table/column identifiers cannot be bound, so they come only from the
    env-var mapping and pass `quote_ident` (strict ^[A-Za-z_][A-Za-z0-9_]*$).
  * The only formatted numbers are LIMIT (already validated and cast to int).

Data rules:
  * One row per well (`QUALIFY ROW_NUMBER()`), so joins can never inflate counts.
  * TRY_CAST turns dirty values into NULL instead of failing the query.
  * Invalid / missing coordinates are excluded; (0, 0) is treated as "no location".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.config import Settings
from backend.services.spatial import bounding_box, haversine_sql


@dataclass(frozen=True)
class Query:
    sql: str
    params: dict[str, Any] = field(default_factory=dict)


def _num(expr: str) -> str:
    return f"TRY_CAST({expr} AS DOUBLE)"


def _well_expressions(s: Settings) -> dict[str, str]:
    """Per-column SELECT expressions. Unmapped optional columns become typed NULLs."""
    c = s.wells_col
    depth = _num(c("depth")) if c("depth") else None
    yld = _num(c("well_yield")) if c("well_yield") else None
    swl = _num(c("static_water_level")) if c("static_water_level") else None
    date = f"TRY_CAST({c('drilling_date')} AS DATE)" if c("drilling_date") else None
    status = f"CAST({c('status')} AS STRING)" if c("status") else None
    return {
        "well_id": f"CAST({c('id')} AS STRING)",
        "latitude": _num(c("latitude")),
        "longitude": _num(c("longitude")),
        # depth <= 0 is impossible -> missing. Yield 0 is a real recorded value, negatives are not.
        "depth": f"CASE WHEN {depth} > 0 THEN {depth} END" if depth else "CAST(NULL AS DOUBLE)",
        "well_yield": f"CASE WHEN {yld} >= 0 THEN {yld} END" if yld else "CAST(NULL AS DOUBLE)",
        "static_water_level": swl or "CAST(NULL AS DOUBLE)",
        "drilling_date": date or "CAST(NULL AS DATE)",
        "status": status or "CAST(NULL AS STRING)",
    }


def _nearby_cte(s: Settings) -> str:
    """CTE chain ending in `nearby` (deduplicated wells inside the radius, with distance_km)."""
    e = _well_expressions(s)
    lat_raw, lon_raw, id_raw = s.wells_col("latitude"), s.wells_col("longitude"), s.wells_col("id")
    order = "drilling_date DESC NULLS LAST, well_id" if s.wells_col("drilling_date") else "well_id"
    return f"""base AS (
  SELECT
    {e['well_id']} AS well_id,
    {e['latitude']} AS latitude,
    {e['longitude']} AS longitude,
    {e['depth']} AS depth,
    {e['well_yield']} AS well_yield,
    {e['static_water_level']} AS static_water_level,
    {e['drilling_date']} AS drilling_date,
    {e['status']} AS status
  FROM {s.wells_fqn}
  WHERE {id_raw} IS NOT NULL
    AND {_num(lat_raw)} BETWEEN :min_lat AND :max_lat
    AND {_num(lon_raw)} BETWEEN :min_lon AND :max_lon
),
deduped AS (
  SELECT * FROM base
  WHERE latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180
    AND NOT (latitude = 0 AND longitude = 0)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY well_id ORDER BY {order}) = 1
),
nearby AS (
  SELECT * FROM (
    SELECT *, {haversine_sql('latitude', 'longitude')} AS distance_km FROM deduped
  ) WHERE distance_km <= :radius_km
)"""


def _search_params(lat: float, lon: float, radius_km: float) -> dict[str, Any]:
    box = bounding_box(lat, lon, radius_km)
    return {"lat": float(lat), "lon": float(lon), "radius_km": float(radius_km), **box}


# ------------------------------------------------------------------ nearby wells
def nearby_wells(s: Settings, lat: float, lon: float, radius_km: float, limit: int) -> Query:
    limit = int(limit)  # validated upstream (1..MAX_WELL_LIMIT); LIMIT cannot take a marker everywhere
    sql = f"""WITH {_nearby_cte(s)}
SELECT well_id, latitude, longitude, distance_km, depth, well_yield, static_water_level,
       drilling_date, status, COUNT(*) OVER () AS total_wells
FROM nearby
ORDER BY distance_km, well_id
LIMIT {limit}"""
    return Query(sql, _search_params(lat, lon, radius_km))


# ------------------------------------------------------------------ summary
def summary_stats(s: Settings, lat: float, lon: float, radius_km: float) -> Query:
    params = _search_params(lat, lon, radius_km)
    if s.low_yield_threshold is not None and s.wells_col("well_yield"):
        low = "COALESCE(SUM(CASE WHEN well_yield < :low_yield THEN 1 ELSE 0 END), 0)"
        params["low_yield"] = float(s.low_yield_threshold)
    else:
        low = "CAST(NULL AS BIGINT)"

    stats = f"""stats AS (
  SELECT
    COUNT(*) AS total_wells,
    COUNT(depth) AS depth_n,               percentile(depth, 0.5) AS depth_median,
    COUNT(well_yield) AS yield_n,          percentile(well_yield, 0.5) AS yield_median,
    COUNT(static_water_level) AS swl_n,    percentile(static_water_level, 0.5) AS swl_median,
    COUNT(drilling_date) AS date_n,        MAX(drilling_date) AS latest_record_date,
    {low} AS low_yield_n
  FROM nearby
)"""
    if s.quality_enabled:
        q = s.quality_col
        sql = f"""WITH {_nearby_cte(s)},
{stats},
qual AS (
  SELECT COUNT(DISTINCT n.well_id) AS quality_wells, COUNT(*) AS quality_obs
  FROM nearby n
  JOIN {s.quality_fqn} q ON CAST(q.{q('well_id')} AS STRING) = n.well_id
  WHERE q.{q('value')} IS NOT NULL
)
SELECT stats.*, qual.quality_wells, qual.quality_obs FROM stats CROSS JOIN qual"""
    else:
        sql = f"""WITH {_nearby_cte(s)},
{stats}
SELECT stats.*, CAST(NULL AS BIGINT) AS quality_wells, CAST(NULL AS BIGINT) AS quality_obs FROM stats"""
    return Query(sql, params)


def histograms(s: Settings, lat: float, lon: float, radius_km: float) -> Query | None:
    """Bucket counts computed in the warehouse so charts always match the full filtered set."""
    parts: list[str] = []
    params = _search_params(lat, lon, radius_km)
    params["last_bin"] = s.hist_bins - 1
    if s.wells_col("depth"):
        parts.append(
            "SELECT 'depth' AS metric, LEAST(CAST(FLOOR(depth / :depth_bw) AS INT), :last_bin) AS bin, "
            "COUNT(*) AS n FROM nearby WHERE depth IS NOT NULL GROUP BY 1, 2"
        )
        params["depth_bw"] = float(s.hist_depth_bin)
    if s.wells_col("well_yield"):
        parts.append(
            "SELECT 'well_yield' AS metric, LEAST(CAST(FLOOR(well_yield / :yield_bw) AS INT), :last_bin) AS bin, "
            "COUNT(*) AS n FROM nearby WHERE well_yield IS NOT NULL GROUP BY 1, 2"
        )
        params["yield_bw"] = float(s.hist_yield_bin)
    if not parts:
        return None
    return Query(f"WITH {_nearby_cte(s)}\n" + "\nUNION ALL\n".join(parts), params)


# ------------------------------------------------------------------ single well
def well_by_id(s: Settings, well_id: str) -> Query:
    e = _well_expressions(s)
    id_raw = s.wells_col("id")
    order = "TRY_CAST(" + s.wells_col("drilling_date") + " AS DATE) DESC NULLS LAST" if s.wells_col("drilling_date") else "1"
    sql = f"""SELECT
  {e['well_id']} AS well_id, {e['latitude']} AS latitude, {e['longitude']} AS longitude,
  {e['depth']} AS depth, {e['well_yield']} AS well_yield,
  {e['static_water_level']} AS static_water_level,
  {e['drilling_date']} AS drilling_date, {e['status']} AS status
FROM {s.wells_fqn}
WHERE CAST({id_raw} AS STRING) = :well_id
ORDER BY {order}
LIMIT 1"""
    return Query(sql, {"well_id": well_id})


# ------------------------------------------------------------------ water quality
def _quality_select(s: Settings) -> dict[str, str]:
    q = s.quality_col
    unit = f"CAST(q.{q('unit')} AS STRING)" if q("unit") else "CAST(NULL AS STRING)"
    date = f"TRY_CAST(q.{q('sample_date')} AS DATE)" if q("sample_date") else "CAST(NULL AS DATE)"
    return {
        "parameter": f"CAST(q.{q('parameter')} AS STRING)",
        "value": f"TRY_CAST(q.{q('value')} AS DOUBLE)",
        "value_raw": f"CAST(q.{q('value')} AS STRING)",
        "unit": unit,
        "sample_date": date,
    }


def quality_measurements(s: Settings, lat: float, lon: float, radius_km: float, limit: int) -> Query:
    x, q = _quality_select(s), s.quality_col
    sql = f"""WITH {_nearby_cte(s)}
SELECT n.well_id, n.distance_km,
       {x['parameter']} AS parameter, {x['value']} AS value, {x['value_raw']} AS value_raw,
       {x['unit']} AS unit, {x['sample_date']} AS sample_date,
       COUNT(*) OVER () AS total_records
FROM nearby n
JOIN {s.quality_fqn} q ON CAST(q.{q('well_id')} AS STRING) = n.well_id
WHERE q.{q('value')} IS NOT NULL AND q.{q('parameter')} IS NOT NULL
ORDER BY sample_date DESC NULLS LAST, n.distance_km, parameter
LIMIT {int(limit)}"""
    return Query(sql, _search_params(lat, lon, radius_km))


def quality_parameters(s: Settings, lat: float, lon: float, radius_km: float) -> Query:
    x, q = _quality_select(s), s.quality_col
    sql = f"""WITH {_nearby_cte(s)}
SELECT {x['parameter']} AS parameter,
       COUNT(*) AS observations,
       COUNT(DISTINCT n.well_id) AS wells,
       MAX({x['sample_date']}) AS latest_sample_date
FROM nearby n
JOIN {s.quality_fqn} q ON CAST(q.{q('well_id')} AS STRING) = n.well_id
WHERE q.{q('value')} IS NOT NULL AND q.{q('parameter')} IS NOT NULL
GROUP BY 1
ORDER BY observations DESC
LIMIT 100"""
    return Query(sql, _search_params(lat, lon, radius_km))


def quality_for_well(s: Settings, well_id: str) -> Query:
    x, q = _quality_select(s), s.quality_col
    sql = f"""SELECT {x['parameter']} AS parameter, {x['value']} AS value, {x['value_raw']} AS value_raw,
       {x['unit']} AS unit, {x['sample_date']} AS sample_date
FROM {s.quality_fqn} q
WHERE CAST(q.{q('well_id')} AS STRING) = :well_id AND q.{q('value')} IS NOT NULL
ORDER BY sample_date DESC NULLS LAST, parameter
LIMIT 200"""
    return Query(sql, {"well_id": well_id})


# ------------------------------------------------------------------ schema validation
def mapped_columns_check(s: Settings, table: str) -> Query:
    """Lists the real columns of a table so the mapping can be verified (values are bound)."""
    from backend.config import quote_ident

    sql = (
        f"SELECT column_name FROM {quote_ident(s.catalog)}.information_schema.columns "
        "WHERE table_schema = :schema AND table_name = :table"
    )
    return Query(sql, {"schema": s.schema, "table": table})
