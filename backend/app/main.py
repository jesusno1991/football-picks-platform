from pathlib import Path
from time import time

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings


_rate_buckets: dict[str, list[float]] = {}
logger = logging.getLogger(__name__)

app = FastAPI(title="Football Picks Platform", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if request.url.path.startswith("/api/") and _is_rate_limited(request):
        return JSONResponse(
            {"detail": "rate_limit_exceeded", "message": "Demasiadas peticiones. Intentalo de nuevo en unos segundos."},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error", extra={"path": request.url.path, "method": request.method})
        return JSONResponse(
            {"detail": "internal_server_error", "message": "Error interno controlado."},
            status_code=500,
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if get_settings().environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _is_rate_limited(request: Request) -> bool:
    if request.method == "OPTIONS":
        return False
    limit = max(get_settings().rate_limit_requests_per_minute, 1)
    now = time()
    window_start = now - 60
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    bucket = [timestamp for timestamp in _rate_buckets.get(client_ip, []) if timestamp >= window_start]
    bucket.append(now)
    _rate_buckets[client_ip] = bucket
    return len(bucket) > limit

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")


@app.get("/")
def root():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "Football Picks Platform", "status": "ok"}


@app.get("/{full_path:path}")
def frontend_app(full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"name": "Football Picks Platform", "status": "ok"}
