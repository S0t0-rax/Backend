import asyncio
import sys

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role

async def run():
    async with AsyncSessionLocal() as session:
        # Load user
        res = await session.execute(select(User).where(User.email=='admin@system.com'))
        u = res.scalar_one_or_none()
        if not u:
            print("User not found")
            return
        
        # Manually load roles to avoid async lazy loading issue
        # or use options(joinedload(User.roles))
        from sqlalchemy.orm import selectinload
        res2 = await session.execute(
            select(User).options(selectinload(User.roles)).where(User.email=='admin@system.com')
        )
        u2 = res2.scalar_one_or_none()

        roles = [r.name for r in u2.roles]
        print(f"Roles BEFORE loop: {roles}")
        
        if 'admin' not in roles:
            print("Admin role missing. Adding it...")
            role_res = await session.execute(select(Role).where(Role.name == 'admin'))
            admin_role = role_res.scalar_one_or_none()
            if not admin_role:
                print("Admin role doesn't exist in DB! Creating...")
                admin_role = Role(name='admin', description='Administrator')
                session.add(admin_role)
                await session.flush()
            
            u2.roles.append(admin_role)
            await session.commit()
            print("Admin role added successfully!")
        else:
            print("Admin role IS already assigned.")

if __name__ == '__main__':
    asyncio.run(run())
