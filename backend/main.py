"""AquaWise Alberta — FastAPI app. Serves /api/* and the compiled React app from one process."""
from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import ROOT, get_settings
from backend.errors import DatabricksUnavailable, ServiceNotConfigured
from backend.routes import comparison, genie, geocode, groundwater, health, quality, wells

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aquawise")


def _warm_up() -> None:
    """Open a warehouse session in the background so the first user query isn't a cold start."""
    from backend.deps import get_repository

    try:
        repo = get_repository()
        if repo.mode == "live":
            repo.ping()  # type: ignore[attr-defined]
            log.info("Databricks warm-up finished")
    except Exception:  # noqa: BLE001
        log.warning("Databricks warm-up failed (the app will retry on the first request)")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    log.info("Starting AquaWise (demo=%s, databricks_configured=%s, genie=%s)", s.demo_mode, s.databricks_configured, s.genie_configured)
    threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(title="AquaWise Alberta API", version="1.0.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=800)
_cors = get_settings().cors_origins
if _cors:  # only for local dev with the Vite server on another port
    app.add_middleware(CORSMiddleware, allow_origins=list(_cors), allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.middleware("http")
async def _cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/assets/"):  # Vite fingerprints these filenames
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, **extra}})


@app.exception_handler(ServiceNotConfigured)
async def _not_configured(_: Request, exc: ServiceNotConfigured):
    msg = ("The AI assistant isn't configured yet." if "AI assistant" in exc.what
           else "Groundwater data isn't connected yet." if "Databricks" in exc.what or "mapping" in exc.what.lower() or "Mapped" in exc.what
           else exc.what)
    return _error(503, "not_configured", msg, missing=exc.missing)


@app.exception_handler(DatabricksUnavailable)
async def _unavailable(_: Request, __: DatabricksUnavailable):
    return _error(502, "data_unavailable", "We couldn't retrieve groundwater information right now. Please try again.")


@app.exception_handler(RequestValidationError)
async def _invalid(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(x) for x in first.get("loc", []) if x not in ("query", "body"))
    return _error(422, "invalid_request", f"Invalid value for {where or 'request'}: {first.get('msg', 'please check your input')}.")


@app.exception_handler(StarletteHTTPException)
async def _http(_: Request, exc: StarletteHTTPException):
    return _error(exc.status_code, "invalid_request" if exc.status_code == 422 else "http_error", str(exc.detail))


@app.exception_handler(Exception)
async def _unexpected(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return _error(500, "internal_error", "Something went wrong on our side. Please try again.")


for r in (health, wells, groundwater, quality, comparison, genie, geocode):
    app.include_router(r.router, prefix="/api")


@app.api_route("/api/{path:path}", methods=["GET", "POST"], include_in_schema=False)
async def _api_404(path: str):
    return _error(404, "not_found", "Unknown API endpoint.")


# ---------------------------------------------------------------- React app
def _static_dir() -> Path | None:
    for candidate in (ROOT / "backend" / "static", ROOT / "frontend" / "dist"):
        if (candidate / "index.html").exists():
            return candidate
    return None


_STATIC = _static_dir()
if _STATIC:
    if (_STATIC / "assets").exists():
        # fingerprinted by Vite -> safe to cache for a year
        app.mount("/assets", StaticFiles(directory=_STATIC / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = (_STATIC / full_path).resolve()
        if full_path and candidate.is_file() and _STATIC.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_STATIC / "index.html", headers={"Cache-Control": "no-cache"})
else:
    @app.get("/", include_in_schema=False)
    async def no_frontend():
        return JSONResponse({"message": "Frontend not built. Run scripts/build.sh (API is available under /api)."})
