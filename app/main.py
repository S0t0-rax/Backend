"""
Punto de entrada principal — FastAPI SaaS Mecánica.

Configura middlewares (CORS, Rate Limiting, Logging),
registra el router principal v1 e inicializa la app.
"""
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_router

# ── Logging setup (loguru) ───────────────────────────────────────
import sys
logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG" if settings.DEBUG else "INFO",
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{module}</cyan>:<cyan>{line}</cyan> — "
        "<level>{message}</level>"
    ),
    colorize=True,
)


# ── Rate Limiter ─────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)


# ── Logging Middleware ───────────────────────────────────────────
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()
        logger.info(f"[{request_id}] ➜ {request.method} {request.url.path}")
        try:
            response = await call_next(request)
        except Exception as exc:
            ms = (time.perf_counter() - start) * 1000
            logger.error(f"[{request_id}] ✖ ERROR ({ms:.1f}ms): {exc}")
            raise
        ms = (time.perf_counter() - start) * 1000
        lvl = "info" if response.status_code < 400 else "warning"
        getattr(logger, lvl)(
            f"[{request_id}] ✔ {request.method} {request.url.path} "
            f"→ {response.status_code} ({ms:.1f}ms)"
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{ms:.1f}ms"
        return response


# ── Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    logger.info("🛑 Servidor detenido.")


# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## SaaS de Gestión de Servicios Mecánicos con Geolocalización

### Módulos
- 🔐 **Auth / Usuarios** — JWT + RBAC (admin, workshop_owner, mechanic, client)
- 🗺️ **Geolocalización** — PostGIS + GeoAlchemy2 (tracking en tiempo real)
- 🚗 **Vehículos (Cars)** — Registro y gestión de vehículos
- 🚨 **Incidentes** — Reporte con foto + análisis de IA
- 🔧 **Órdenes de Servicio** — Asignación y tracking de mecánicos
- 💳 **Pagos QR** — Integración con pasarela QR interoperable (Bolivia)
- 🧾 **Facturación** — CUF/CUFD según normativa SIN Bolivia
    """,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

# ── Logging Middleware ────────────────────────────────────────────
app.add_middleware(LoggingMiddleware)

# ── Audit Logger Middleware ───────────────────────────────────────
from app.api.middleware.audit_logger import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)

# ── Rate Limiting ─────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception Handlers ────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    })

# Trigger reload

# Trigger reload 2

# Trigger reload 3

# Trigger reload 4

# Trigger reload 5

# Trigger reload 6

# Trigger reload 7

# Trigger reload 8

# Trigger reload Supabase

# Trigger reload 9

# Trigger reload 10

# Trigger reload 11

# Trigger reload 12
