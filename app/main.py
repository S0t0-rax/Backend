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
async def run_migrations():
    """Ejecuta migraciones de Alembic programáticamente."""
    from alembic.config import Config
    from alembic import command
    import os
    
    logger.info("🛠️ Revisando migraciones de base de datos...")
    try:
        # Nos aseguramos de estar en el directorio raíz para encontrar alembic.ini
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Base de datos actualizada.")
    except Exception as e:
        logger.error(f"❌ Error al ejecutar migraciones: {e}")

async def seed_data():
    """Crea roles iniciales y usuario admin si no existen."""
    from app.db.session import AsyncSessionLocal
    from app.models.role import Role
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select
    
    logger.info("🌱 Verificando datos iniciales...")
    async with AsyncSessionLocal() as db:
        try:
            # 1. Crear roles básicos
            role_names = ["admin", "workshop_owner", "mechanic", "client"]
            for rname in role_names:
                result = await db.execute(select(Role).where(Role.name == rname))
                if not result.scalar_one_or_none():
                    db.add(Role(name=rname, description=f"Rol de {rname}"))
            
            await db.commit()
            
            # 2. Crear admin inicial desde .env
            result = await db.execute(select(User).where(User.email == settings.FIRST_ADMIN_EMAIL))
            if not result.scalar_one_or_none():
                logger.info(f"👤 Creando usuario admin inicial: {settings.FIRST_ADMIN_EMAIL}")
                admin_role_result = await db.execute(select(Role).where(Role.name == "admin"))
                admin_role = admin_role_result.scalar_one()
                
                new_admin = User(
                    email=settings.FIRST_ADMIN_EMAIL,
                    password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
                    full_name="Administrador Sistema",
                    is_active=True,
                    roles=[admin_role]
                )
                db.add(new_admin)
                await db.commit()
                logger.info("✨ Admin creado con éxito.")
            else:
                logger.debug("Admin ya existe.")

        except Exception as e:
            logger.error(f"❌ Error al sembrar datos: {e}")
            await db.rollback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    # Ejecutar migraciones antes de que la app acepte tráfico
    await run_migrations()
    # Sembrar datos iniciales (Roles y Admin)
    await seed_data()
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4200",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
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
