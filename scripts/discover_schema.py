#!/usr/bin/env python
"""Inspect the Databricks schema and write databricks/schema_inventory.md.

Run this BEFORE filling in the WELLS_* / QUALITY_* variables in .env. It lists the real tables and
columns (SHOW TABLES + information_schema.columns) and, for each logical field the app needs,
suggests candidate columns by name. Suggestions are hints only: a person must confirm the meaning
and the units of every column before mapping it.

    python scripts/discover_schema.py                # prints + writes databricks/schema_inventory.md
    python scripts/discover_schema.py --no-write     # print only
Secrets are never printed. Credentials come from the same DATABRICKS_* environment as the app.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings, quote_ident  # noqa: E402
from backend.services.queries import Query  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "databricks" / "schema_inventory.md"

# logical field -> (env var it feeds, name patterns that suggest a candidate)
FIELD_HINTS: dict[str, tuple[str, str]] = {
    "well identifier": ("WELLS_COL_ID", r"well.*(id|no|num)|^id$|gic|wid"),
    "latitude": ("WELLS_COL_LATITUDE", r"lat"),
    "longitude": ("WELLS_COL_LONGITUDE", r"lon"),
    "drilling depth": ("WELLS_COL_DEPTH", r"depth"),
    "yield / pumping rate": ("WELLS_COL_YIELD", r"yield|rate|pump|gpm"),
    "static water level": ("WELLS_COL_STATIC_WATER_LEVEL", r"static|swl|water_?level|rest"),
    "drilling / completion date": ("WELLS_COL_DRILL_DATE", r"date|drill|complet"),
    "well status": ("WELLS_COL_STATUS", r"status|condition|state"),
    "quality: well identifier": ("QUALITY_COL_WELL_ID", r"well.*(id|no|num)|^id$|gic"),
    "quality: parameter name": ("QUALITY_COL_PARAMETER", r"param|analyte|constituent|test|variable|name"),
    "quality: measured value": ("QUALITY_COL_VALUE", r"value|result|conc|amount"),
    "quality: unit": ("QUALITY_COL_UNIT", r"unit|uom"),
    "quality: sample date": ("QUALITY_COL_SAMPLE_DATE", r"date|sampl"),
}
QUALITY_TABLE_HINT = re.compile(r"chem|quality|analys|sample|water_?q|lab", re.I)


def render_inventory(catalog: str, schema: str, columns: list[dict], generated: str | None = None) -> str:
    """Pure function (unit-tested): turn information_schema rows into the markdown inventory."""
    by_table: dict[str, list[dict]] = defaultdict(list)
    for c in columns:
        by_table[c["table_name"]].append(c)

    lines = [
        f"# Schema inventory: `{catalog}.{schema}`",
        "",
        f"Generated {generated or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `scripts/discover_schema.py`.",
        "",
        "> Column suggestions below are **name-based hints only**. Confirm each column's meaning and **units** with the data",
        "> owner / data dictionary before putting it in `.env`.",
        "",
        f"## Tables ({len(by_table)})",
        "",
    ]
    if not by_table:
        lines += ["_No tables visible. Check the catalog/schema names and that the principal has `USE CATALOG`, `USE SCHEMA` and `SELECT`._", ""]
    for table in sorted(by_table):
        cols = sorted(by_table[table], key=lambda c: int(c.get("ordinal_position") or 0))
        tag = "  ← possible water-quality table" if QUALITY_TABLE_HINT.search(table) else ""
        lines += [f"### `{table}`{tag}", "", "| # | column | type |", "|---|--------|------|"]
        lines += [f"| {c.get('ordinal_position', '')} | `{c['column_name']}` | {c['data_type']} |" for c in cols]
        lines.append("")

    lines += ["## Suggested mapping (to confirm)", "", "| logical field | env var | candidate columns (table.column) |", "|---|---|---|"]
    for label, (env, pattern) in FIELD_HINTS.items():
        rx = re.compile(pattern, re.I)
        want_quality = label.startswith("quality:")
        hits = [
            f"`{t}.{c['column_name']}`"
            for t, cols in sorted(by_table.items())
            for c in cols
            if rx.search(c["column_name"]) and bool(QUALITY_TABLE_HINT.search(t)) == want_quality
        ]
        lines.append(f"| {label} | `{env}` | {', '.join(hits[:8]) or '_none found — field will show “Not available”_'} |")

    lines += [
        "",
        "## Decisions to record here after review",
        "",
        "- Well table → `WELLS_TABLE` = ",
        "- Unit of depth → `WELLS_DEPTH_UNIT` = ",
        "- Unit of yield → `WELLS_YIELD_UNIT` = ",
        "- Is there one row per well? (the app de-duplicates by well id regardless) = ",
        "- Quality table is long format (parameter / value / unit rows)? If it is wide, unpivot it in `databricks/views.sql`. = ",
        "- Low-yield threshold (in yield units) → `LOW_YIELD_THRESHOLD` = ",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-write", action="store_true", help="print only; do not write databricks/schema_inventory.md")
    args = ap.parse_args()

    s = get_settings()
    if not s.databricks_configured:
        print("Databricks is not configured. Set DATABRICKS_HOST and DATABRICKS_WAREHOUSE_ID (plus credentials) in .env.", file=sys.stderr)
        return 2

    from backend.services.databricks import DatabricksClient

    db = DatabricksClient(s)
    q = Query(
        f"SELECT table_name, column_name, data_type, ordinal_position FROM {quote_ident(s.catalog)}.information_schema.columns "
        "WHERE table_schema = :schema ORDER BY table_name, ordinal_position",
        {"schema": s.schema},
    )
    try:
        rows = db.query(q)
    except Exception as exc:  # noqa: BLE001
        print(f"Could not read information_schema ({type(exc).__name__}). Check credentials, warehouse and permissions.", file=sys.stderr)
        return 1

    text = render_inventory(s.catalog, s.schema, rows)
    print(text)
    if not args.no_write:
        OUT.write_text(text, encoding="utf-8")
        print(f"\nWritten to {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
