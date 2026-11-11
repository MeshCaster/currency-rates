import hashlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def lock_key(name: str) -> int:
    digest = hashlib.blake2b(name.encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


async def try_advisory_xact_lock(session: AsyncSession, name: str) -> bool:

    if session.get_bind().dialect.name != "postgresql":
        return True
    acquired = await session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"),
                                    {"key": lock_key(name)})
    return bool(acquired)
