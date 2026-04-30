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
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
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
            logger.error(f"[{request_id}] [ERROR] ({ms:.1f}ms): {exc}")

            raise
        ms = (time.perf_counter() - start) * 1000
        lvl = "info" if response.status_code < 400 else "warning"
        getattr(logger, lvl)(
            f"[{request_id}] [OK] {request.method} {request.url.path} "
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
    import asyncio
    
    logger.info("[DB] Revisando migraciones y extensiones de base de datos...")

    try:
        # Nos aseguramos de que PostGIS esté activo
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            
            # Parche automático para nuevas columnas en users (evita errores de migración)
            try:
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'available'"))
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS current_incident_id BIGINT REFERENCES incidents(id)"))
                logger.info("[DB] Columnas de estado y asignación verificadas en 'users'.")
            except Exception as patch_err:
                logger.warning(f"[DB] No se pudo aplicar el parche de columnas (quizás ya existen): {patch_err}")

            await db.commit()
            logger.info("[OK] Extensión PostGIS y esquema base verificados.")
        
        # Usamos run_in_executor para que alembic (que es síncrono) no bloquee el loop
        alembic_cfg = Config("alembic.ini")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")
        logger.info("[OK] Base de datos actualizada.")

    except Exception as e:
        logger.error(f"[ERROR] Al ejecutar migraciones: {e}")


async def seed_data():
    """Crea roles iniciales, usuario admin y rescata usuarios viejos."""
    from app.db.session import AsyncSessionLocal
    from app.models.role import Role
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy import select
    import bcrypt
    
    def is_bcrypt_hash(h: str) -> bool:
        return h.startswith("$2") and len(h) == 60

    logger.info("🌱 Verificando datos iniciales y rescate de usuarios...")
    async with AsyncSessionLocal() as db:
        try:
            # 1. Crear roles básicos
            role_names = ["admin", "workshop_owner", "mechanic", "client"]
            roles_map = {}
            for rname in role_names:
                result = await db.execute(select(Role).where(Role.name == rname))
                role = result.scalar_one_or_none()
                if not role:
                    role = Role(name=rname, description=f"Rol de {rname}")
                    db.add(role)
                    await db.flush()
                roles_map[rname] = role
            
            await db.commit()
            
            # 2. Rescatar usuarios existentes (encriptar si es necesario y asignar roles)
            result = await db.execute(select(User))
            users = result.scalars().all()
            migrated = 0
            for user in users:
                needs_update = False
                # Encriptar si es texto plano
                if not is_bcrypt_hash(user.password_hash):
                    user.password_hash = hash_password(user.password_hash)
                    needs_update = True
                
                # Asignar rol admin (o client) si no tiene
                if not user.roles:
                    # Por seguridad, si es el primer rescate, les damos 'admin' 
                    # para que el usuario pueda entrar. Luego puede bajarlos de rango.
                    user.roles.append(roles_map["admin"])
                    needs_update = True
                
                if needs_update:
                    migrated += 1
            
            if migrated > 0:
                await db.commit()
                logger.info(f"[OK] Se rescataron {migrated} usuarios con éxito.")


            # 3. Crear admin desde .env solo si no hay ningún admin todavía
            result = await db.execute(select(User).where(User.email == settings.FIRST_ADMIN_EMAIL))
            if not result.scalar_one_or_none():
                logger.info(f"[USER] Creando usuario admin inicial: {settings.FIRST_ADMIN_EMAIL}")

                new_admin = User(
                    email=settings.FIRST_ADMIN_EMAIL,
                    password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
                    full_name="Administrador Sistema",
                    is_active=True,
                    roles=[roles_map["admin"]]
                )
                db.add(new_admin)
                await db.commit()
                logger.info("[OK] Admin creado con éxito.")


        except Exception as e:
            logger.error(f"[ERROR] Al sembrar/rescatar datos: {e}")

            await db.rollback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"[START] Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")

    # Ejecutar migraciones antes de que la app acepte tráfico
    await run_migrations()
    # Sembrar datos y rescatar usuarios
    await seed_data()
    yield
    logger.info("[STOP] Servidor detenido.")



# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## SaaS de Gestión de Servicios Mecánicos con Geolocalización

### Módulos
-  **Auth / Usuarios** — JWT + RBAC (admin, workshop_owner, mechanic, client)
-  **Geolocalización** — PostGIS + GeoAlchemy2 (tracking en tiempo real)
-  **Vehículos (Cars)** — Registro y gestión de vehículos
-  **Incidentes** — Reporte con foto + análisis de IA
-  **Órdenes de Servicio** — Asignación y tracking de mecánicos
-  **Pagos QR** — Integración con pasarela QR interoperable (Bolivia)
-  **Facturación** — CUF/CUFD según normativa SIN Bolivia
    """,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# ── Proxy Headers (Railway HTTPS fix) ────────────────────────────
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

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

# ── Static Files (Uploads) ────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
os.makedirs("uploads/incidents", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


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
