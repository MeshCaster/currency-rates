from anyio import to_thread
from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def verify_and_rehash(password: str, hashed: str) -> tuple[bool, str | None]:
    return _password_hash.verify_and_update(password, hashed)


async def hash_password_async(password: str) -> str:
    return await to_thread.run_sync(hash_password, password)


async def verify_password_async(password: str, hashed: str) -> bool:
    return await to_thread.run_sync(verify_password, password, hashed)
