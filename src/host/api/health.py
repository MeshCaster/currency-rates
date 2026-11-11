from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    db = getattr(request.state, "db", None)
    ok = db is not None and await db.ping()
    return JSONResponse({"status": "ok" if ok else "unavailable", "database": ok},
                        status_code=200 if ok else 503)
