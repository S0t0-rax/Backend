import asyncio
import os
import bcrypt
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import settings and models safely
import sys
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.config import settings
from app.models.role import Role
from app.models.user import User

def is_bcrypt_hash(h: str) -> bool:
    # Bcrypt hashes start with $2a$, $2b$ or $2y$ and are 60 chars long
    return h.startswith("$2") and len(h) == 60

async def migrate():
    print("🚀 Iniciando rescate de usuarios...")
    
    # Usamos la URL de la base de datos de settings
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Asegurar que los roles básicos existen
            print("🎭 Verificando roles...")
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

            # 2. Buscar usuarios y "rescatarlos"
            print("👥 Buscando usuarios para rescatar...")
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            migrated_count = 0
            for user in users:
                needs_update = False
                
                # A. Encriptar contraseña si es texto plano
                # Si el hash no parece bcrypt, asumimos que es texto plano
                if not is_bcrypt_hash(user.password_hash):
                    print(f"🔑 Encriptando contraseña para: {user.email}")
                    pwd_bytes = user.password_hash.encode('utf-8')
                    hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode('utf-8')
                    user.password_hash = hashed
                    needs_update = True
                
                # B. Asignar rol admin por defecto si no tiene roles
                # (Para asegurar que el usuario puede entrar al panel)
                if not user.roles:
                    print(f"🛡️ Asignando rol 'admin' a: {user.email}")
                    user.roles.append(roles_map["admin"])
                    needs_update = True
                
                if needs_update:
                    migrated_count += 1
            
            await db.commit()
            print(f"✅ ¡Rescate completado! Se actualizaron {migrated_count} usuarios.")
            
        except Exception as e:
            print(f"❌ Error durante la migración: {e}")
            await db.rollback()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(migrate())
