import asyncio
from sqlalchemy import text
from app.api.dependencies import get_db
from app.db.session import AsyncSessionLocal

async def update_schema():
    async with AsyncSessionLocal() as session:
        try:
            # Añadir la columna is_available si no existe
            await session.execute(text("ALTER TABLE workshops ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT TRUE"))
            await session.execute(text("UPDATE workshops SET is_available = TRUE WHERE is_available IS NULL"))
            await session.commit()
            print("Columna 'is_available' añadida y actualizada con éxito.")
        except Exception as e:
            await session.rollback()
            print(f"Error al actualizar el esquema: {e}")

if __name__ == "__main__":
    asyncio.run(update_schema())
