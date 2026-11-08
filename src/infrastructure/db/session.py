import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/currency_rates")

engine = create_async_engine(DATABASE_URL, pool_size=10, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
