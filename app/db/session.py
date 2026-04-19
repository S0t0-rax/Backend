"""
Sesión de base de datos — SQLAlchemy 2.0 async.

Soporta dos backends:
  - PostgreSQL (asyncpg) en producción
  - SQLite   (aiosqlite) en desarrollo local sin C++ Build Tools

El backend se selecciona automáticamente según DATABASE_URL en .env.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles
from geoalchemy2.functions import ST_AsBinary, ST_GeomFromText, ST_GeogFromText

@compiles(ST_AsBinary, 'sqlite')
def compile_st_asbinary(element, compiler, **kw):
    return "NULL"

@compiles(ST_GeomFromText, 'sqlite')
def compile_st_geomfromtext(element, compiler, **kw):
    return "NULL"

@compiles(ST_GeogFromText, 'sqlite')
def compile_st_geogfromtext(element, compiler, **kw):
    return "NULL"

from app.core.config import settings


# ── Determinar driver disponible ─────────────────────────────────
# asyncpg requiere Microsoft C++ Build Tools en Windows.
# Si no está instalado, se usa aiosqlite (solo SQLite) como fallback.
_db_url = settings.DATABASE_URL
if _db_url.startswith("postgresql+asyncpg://"):
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        raise ImportError(
            "\n\n  [ERROR] asyncpg no esta instalado.\n"
            "  Para PostgreSQL en Windows necesitas Microsoft C++ Build Tools:\n"
            "  https://visualstudio.microsoft.com/visual-cpp-build-tools/\n\n"
            "  Alternativa para desarrollo local - cambia DATABASE_URL en .env a:\n"
            "  DATABASE_URL=sqlite+aiosqlite:///./dev.db\n"
        )

# ── Motor Async ─────────────────────────────────────────────────
engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    # Para SQLite no hay pool real; para PostgreSQL ajusta según carga
    **({} if "sqlite" in _db_url else {"pool_size": 10, "max_overflow": 20}),
    future=True,
)

# ── Session Factory ─────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency — provee una sesión de BD por request.

    Uso:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
