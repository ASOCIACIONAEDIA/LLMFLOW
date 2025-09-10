import asyncio
from app.db.session import engine
from app.db.base import Base
import app.models  # noqa: ensure all models are imported and registered


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✅ Tables created (idempotent).")

if __name__ == "__main__":
    asyncio.run(main())