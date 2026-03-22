from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.auth_service import AuthService
from src.core.services.password_reset_service import PasswordResetService
from src.data.clients.postgres_client import get_db
from src.schemas.auth_schema import AccessTokenResponse, LoginRequest, TokenResponse
from src.schemas.password_reset_schema import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from src.utils.auth_utils import delete_refresh_cookie, set_refresh_cookie

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token_response, refresh_token = await AuthService(db).login(
        data.email, data.password
    )
    set_refresh_cookie(response, refresh_token)
    return token_response


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        from src.core.exceptions.auth_exceptions import InvalidTokenException
        raise InvalidTokenException("Refresh token missing")

    access_response, new_refresh_token = await AuthService(db).refresh_access_token(
        refresh_token
    )
    set_refresh_cookie(response, new_refresh_token)
    return access_response


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        # Revoke in DB — ignore errors (invalid/expired token is fine on logout)
        await AuthService(db).logout(refresh_token)

    delete_refresh_cookie(response)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await PasswordResetService(db).forgot_password(data.email)
    return ForgotPasswordResponse()  


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await PasswordResetService(db).reset_password(data.token, data.new_password)
    return ResetPasswordResponse()