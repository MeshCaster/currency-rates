from fastapi import APIRouter, status

from host.api.deps import AuthDep, CurrentUserDep
from host.api.schemas import RegisterIn, SignInIn, TokenOut, UserOut

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, auth: AuthDep) -> UserOut:
    return UserOut.of(await auth.register(body.email, body.password))


@router.post("/auth/login", response_model=TokenOut)
async def login(body: SignInIn, auth: AuthDep) -> TokenOut:
    return TokenOut.of(await auth.sign_in(body.email, body.password))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUserDep) -> UserOut:
    return UserOut.of(user)
