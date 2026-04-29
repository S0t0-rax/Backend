import asyncio
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.user import User

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(User.id, User.email, User.fcm_token))
        users = result.all()
        for u in users:
            print(f"ID: {u.id}, Email: {u.email}, FCM_TOKEN: {u.fcm_token is not None}")

if __name__ == "__main__":
    asyncio.run(main())
