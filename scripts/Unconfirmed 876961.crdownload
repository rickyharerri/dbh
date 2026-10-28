#!/usr/bin/env python
"""Read-only profiling of the Alberta water-well tables, so the curated view is built from facts, not guesses.

Uses DATABRICKS_CATALOG / DATABRICKS_SCHEMA from .env (set them to users / david_hurley first).
Prints compact results to paste back. Every statement is a SELECT. No secrets are printed.

    python scripts/profile_wells.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings, quote_ident  # noqa: E402
from backend.services.queries import Query  # noqa: E402

AB = "BETWEEN 48.9 AND 60.1"  # rough Alberta latitude band, used only to count obviously-wrong coordinates
AB_LON = "BETWEEN -120.1 AND -109.9"


def sections(p: str) -> list[tuple[str, str]]:
    """(title, sql). `p` is the quoted `catalog`.`schema` prefix. Table names come from the schema inventory."""
    t = lambda name: f"{p}.`{name}`"  # noqa: E731
    W, WT, WM, YT = t("alberta_wtest_well"), t("alberta_wtest_well_test"), t("alberta_wtest_well_measures"), t("alberta_wtest_yield_test")
    QD, QA, STD = t("alberta_wtest_wqual_details"), t("alberta_wtest_wqual_analysis_info"), t("alberta_wtest_gcdwq_standard")
    DW, DR = t("alberta_wdrill_wells"), t("alberta_wdrill_well_reports")
    return [
        ("1. Row counts", " UNION ALL ".join(
            f"SELECT '{n}' AS table_name, COUNT(*) AS n FROM {tbl}" for n, tbl in
            [("wtest_well", W), ("wtest_well_test", WT), ("wtest_well_measures", WM), ("wtest_yield_test", YT),
             ("wtest_wqual_details", QD), ("wtest_wqual_analysis_info", QA), ("wdrill_wells", DW), ("wdrill_well_reports", DR)])),

        ("2. wtest_well: ids and coordinates", f"""SELECT COUNT(*) AS rows, COUNT(DISTINCT WELL_ID) AS distinct_well_id,
  COUNT(DISTINCT WELL_GIC_ID) AS distinct_gic, SUM(CASE WHEN LATTITUDE IS NULL OR LONGITUDE IS NULL THEN 1 ELSE 0 END) AS null_coords,
  SUM(CASE WHEN LATTITUDE {AB} AND LONGITUDE {AB_LON} THEN 0 ELSE 1 END) AS outside_alberta_box,
  MIN(LATTITUDE) AS min_lat, MAX(LATTITUDE) AS max_lat, MIN(LONGITUDE) AS min_lon, MAX(LONGITUDE) AS max_lon,
  MIN(YEAR_WELL_DRILLED) AS min_year, MAX(YEAR_WELL_DRILLED) AS max_year FROM {W}"""),

        ("3. wdrill_wells: ids and coordinates", f"""SELECT COUNT(*) AS rows, COUNT(DISTINCT Well_ID) AS distinct_well_id, COUNT(DISTINCT GIC_Well_ID) AS distinct_gic,
  SUM(CASE WHEN Latitude IS NULL OR Longitude IS NULL THEN 1 ELSE 0 END) AS null_coords,
  SUM(CASE WHEN Latitude {AB} AND Longitude {AB_LON} THEN 0 ELSE 1 END) AS outside_alberta_box,
  MIN(Latitude) AS min_lat, MAX(Latitude) AS max_lat, MIN(Longitude) AS min_lon, MAX(Longitude) AS max_lon FROM {DW}"""),

        ("4a. Depth units (wtest_well_measures)", f"""SELECT DEPTH_UNIT, WELL_COMPLETION_UNIT, COUNT(*) AS n, COUNT(WELL_DEPTH) AS with_depth,
  percentile(WELL_DEPTH, 0.1) AS p10, percentile(WELL_DEPTH, 0.5) AS median, percentile(WELL_DEPTH, 0.9) AS p90, MAX(WELL_DEPTH) AS max
  FROM {WM} GROUP BY 1, 2 ORDER BY n DESC LIMIT 15"""),

        ("4b. Yield units (wtest_yield_test)", f"""SELECT PUMPING_RATE_UNITS, COUNT(*) AS n, COUNT(CONST_PUMPING_RATE) AS with_rate,
  percentile(CONST_PUMPING_RATE, 0.1) AS p10, percentile(CONST_PUMPING_RATE, 0.5) AS median, percentile(CONST_PUMPING_RATE, 0.9) AS p90,
  MIN(CONST_PUMPING_RATE) AS min, MAX(CONST_PUMPING_RATE) AS max FROM {YT} GROUP BY 1 ORDER BY n DESC LIMIT 15"""),

        ("4c. Water-level units (wtest_yield_test)", f"""SELECT NON_PUMPING_WATERLEVEL_UNIT, WATERLEVEL_MSMT_DATUM, COUNT(*) AS n, COUNT(NON_PUMPING_WATERLEVEL) AS with_level,
  percentile(NON_PUMPING_WATERLEVEL, 0.5) AS median, MIN(NON_PUMPING_WATERLEVEL) AS min, MAX(NON_PUMPING_WATERLEVEL) AS max
  FROM {YT} GROUP BY 1, 2 ORDER BY n DESC LIMIT 15"""),

        ("4d. Drilling-report depth (wdrill_well_reports; NO unit column)", f"""SELECT COUNT(Total_Depth_Drilled) AS with_total_depth,
  percentile(Total_Depth_Drilled, 0.1) AS p10, percentile(Total_Depth_Drilled, 0.5) AS median, percentile(Total_Depth_Drilled, 0.9) AS p90,
  MAX(Total_Depth_Drilled) AS max, COUNT(Finished_Well_Depth) AS with_finished_depth, percentile(Finished_Well_Depth, 0.5) AS finished_median,
  COUNT(Recommended_Rate) AS with_rec_rate, percentile(Recommended_Rate, 0.5) AS rec_rate_median FROM {DR}"""),

        ("5. How many tests / measures / yield tests per well", f"""SELECT 'tests per well' AS what, COUNT(*) AS wells, MAX(c) AS max_per_well, SUM(CASE WHEN c > 1 THEN 1 ELSE 0 END) AS wells_with_more_than_one
  FROM (SELECT WELL_ID, COUNT(*) AS c FROM {WT} GROUP BY 1)
  UNION ALL SELECT 'measures per test', COUNT(*), MAX(c), SUM(CASE WHEN c > 1 THEN 1 ELSE 0 END) FROM (SELECT WELL_TEST_ID, COUNT(*) AS c FROM {WM} GROUP BY 1)
  UNION ALL SELECT 'yield tests per test', COUNT(*), MAX(c), SUM(CASE WHEN c > 1 THEN 1 ELSE 0 END) FROM (SELECT WELL_TEST_ID, COUNT(*) AS c FROM {YT} GROUP BY 1)
  UNION ALL SELECT 'water-quality details per test', COUNT(*), MAX(c), SUM(CASE WHEN c > 1 THEN 1 ELSE 0 END) FROM (SELECT WELL_TEST_ID, COUNT(*) AS c FROM {QD} GROUP BY 1)"""),

        ("6. Join integrity (rows with no parent)", f"""SELECT 'well_test -> well' AS link, COUNT(*) AS orphans FROM {WT} x LEFT ANTI JOIN {W} w ON x.WELL_ID = w.WELL_ID
  UNION ALL SELECT 'measures -> well_test', COUNT(*) FROM {WM} x LEFT ANTI JOIN {WT} w ON x.WELL_TEST_ID = w.WELL_TEST_ID
  UNION ALL SELECT 'yield_test -> well_test', COUNT(*) FROM {YT} x LEFT ANTI JOIN {WT} w ON CAST(x.WELL_TEST_ID AS BIGINT) = w.WELL_TEST_ID
  UNION ALL SELECT 'wqual_details -> well_test', COUNT(*) FROM {QD} x LEFT ANTI JOIN {WT} w ON CAST(x.WELL_TEST_ID AS BIGINT) = w.WELL_TEST_ID
  UNION ALL SELECT 'wqual_analysis -> wqual_details', COUNT(*) FROM {QA} x LEFT ANTI JOIN {QD} w ON x.WQUAL_DETAILS_ID = CAST(w.WQUAL_DETAILS_ID AS BIGINT)"""),

        ("7. Do the two well systems share ids? (wtest GIC id vs wdrill GIC id)", f"""SELECT COUNT(*) AS wtest_wells,
  SUM(CASE WHEN d.GIC_Well_ID IS NOT NULL THEN 1 ELSE 0 END) AS also_in_wdrill FROM {W} w
  LEFT JOIN (SELECT DISTINCT GIC_Well_ID FROM {DW}) d ON CAST(w.WELL_GIC_ID AS BIGINT) = d.GIC_Well_ID"""),

        ("8. Water-quality parameters (top 40)", f"""SELECT PARAMETER_NAME, PARAMETER_UNITS, COUNT(*) AS n, COUNT(PARAMETER_VALUE) AS with_value,
  COUNT(DISTINCT PARAMETER_OP) AS n_ops, MAX(PARAMETER_OP) AS an_op, COUNT(GCDWQ_STANDARD_ID) AS with_standard
  FROM {QA} GROUP BY 1, 2 ORDER BY n DESC LIMIT 40"""),

        ("9. PARAMETER_OP values (e.g. '<' = below detection limit?)", f"SELECT PARAMETER_OP, COUNT(*) AS n, COUNT(PARAMETER_VALUE) AS with_value, COUNT(DETECT_LIMIT) AS with_detect_limit FROM {QA} GROUP BY 1 ORDER BY n DESC LIMIT 10"),

        ("10. Date formats (samples)", f"""(SELECT 'ASSESSMENT_DATE' AS col, ASSESSMENT_DATE AS sample FROM {WT} WHERE ASSESSMENT_DATE IS NOT NULL LIMIT 4)
  UNION ALL (SELECT 'RECEIVED_DATE', RECEIVED_DATE FROM {QD} WHERE RECEIVED_DATE IS NOT NULL LIMIT 4)
  UNION ALL (SELECT 'Drilling_End_Date', Drilling_End_Date FROM {DR} WHERE Drilling_End_Date IS NOT NULL LIMIT 4)"""),

        ("11. GCDWQ guideline reference table (is it a trustworthy, versioned reference?)", f"""SELECT GCDWQ_STANDARD_ID, PARAMETER_NAME, GCDWQ_MIN_VALUE, GCDWQ_MAX_VALUE, GCDWQ_UNITS, GCDWQ_OBJECTIVE_TYPE, GCDWQ_APPROVAL_YEAR
  FROM {STD} ORDER BY PARAMETER_NAME LIMIT 80"""),
    ]


def show(rows: list[dict], limit: int = 80) -> None:
    if not rows:
        print("  (no rows)")
        return
    cols = list(rows[0])
    print("  " + " | ".join(cols))
    for r in rows[:limit]:
        print("  " + " | ".join("NULL" if r[c] is None else (f"{r[c]:.4g}" if isinstance(r[c], float) else str(r[c])) for c in cols))


def main() -> int:
    s = get_settings()
    if not s.databricks_configured:
        print("Set DATABRICKS_HOST and DATABRICKS_WAREHOUSE_ID (and credentials) in .env", file=sys.stderr)
        return 2
    from backend.services.databricks import DatabricksClient

    db = DatabricksClient(s)
    prefix = f"{quote_ident(s.catalog)}.{quote_ident(s.schema)}"
    print(f"# Profile of {s.catalog}.{s.schema}\n")
    for title, sql in sections(prefix):
        print(f"## {title}")
        try:
            show(db.query(Query(sql)))
        except Exception as exc:  # noqa: BLE001 - keep going; a failed section is itself information
            print(f"  FAILED: {type(exc).__name__}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
