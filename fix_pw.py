import asyncio
import sys

from app.core.security import hash_password
from sqlalchemy import update
from app.db.session import AsyncSessionLocal
from app.models.user import User

async def run():
    h = hash_password('Admin123*')
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.email == 'admin@system.com').values(password_hash=h))
        await session.commit()
    print('Password updated')

if __name__ == '__main__':
    asyncio.run(run())
