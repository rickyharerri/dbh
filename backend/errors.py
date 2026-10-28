"""Domain errors, mapped to friendly JSON responses in main.py."""


class ServiceNotConfigured(Exception):
    """Databricks / Genie / geocoder is not configured. `missing` lists env vars to set."""

    def __init__(self, what: str, missing: list[str] | None = None):
        super().__init__(what)
        self.what = what
        self.missing = missing or []


class DatabricksUnavailable(Exception):
    """Warehouse unreachable, auth failed or the statement failed/timed out."""
