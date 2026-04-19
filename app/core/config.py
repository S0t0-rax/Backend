"""
Configuración global — Pydantic Settings.
Carga variables desde el archivo .env automáticamente.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────
    APP_NAME: str = "AAA Serv Meca API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"   # development | staging | production
    DEBUG: bool = True

    # ── Server ─────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database (PostgreSQL + PostGIS) ────────────────────────
    # postgresql+asyncpg://user:pass@host:5432/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aaa_serv_meca"
    # URL sync para Alembic (env.py offline mode)
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/aaa_serv_meca"

    # ── JWT Security ───────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ───────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:4200,https://frontend-3vho21c0d-s0t0-raxs-projects.vercel.app"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # ── Rate Limiting ──────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── AWS S3 (almacenamiento de imágenes) ───────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "aaa-serv-meca-images"
    AWS_REGION: str = "us-east-1"

    # ── IA / Vision API ────────────────────────────────────────
    AI_VISION_API_URL: str = ""
    AI_VISION_API_KEY: str = ""

    # ── QR / Pasarela de pago ──────────────────────────────────
    QR_GATEWAY_URL: str = ""
    QR_GATEWAY_API_KEY: str = ""
    QR_MERCHANT_ID: str = ""

    # ── Admin inicial (seed) ───────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@aaa-serv-meca.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@1234!"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
