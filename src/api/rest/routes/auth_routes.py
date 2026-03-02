"""Authentication routes: register, login, refresh, logout."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_current_user
from src.core.services.auth_service import AuthService
from src.data.clients.postgres_client import get_db
from src.schemas.auth_schema import (
    AccessTokenResponse,
    LoginRequest,
    TokenResponse,
)
from src.schemas.customer_schema import CustomerRegisterRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: CustomerRegisterRequest,
    response: Response, db: AsyncSession = Depends(get_db)):
    """Register a new customer account and receive tokens."""
    service = AuthService(db)
    token_response, refresh_token =  await service.register_customer(data)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,      # True in production (HTTPS)
        samesite="Strict",
        max_age=7 * 24 * 60 * 60,
    )
    
    return token_response


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    token_response, refresh_token = await service.login(data.email, data.password)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,      # True in production (HTTPS)
        samesite="Strict",
        max_age=7 * 24 * 60 * 60,
    )

    return token_response


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    # print("="*30)
    # print(refresh_token)

    service = AuthService(db)
    return await service.refresh_access_token(refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")

    service = AuthService(db)
    await service.logout(refresh_token)

    response.delete_cookie("refresh_token")


@router.get("/validate")
async def validate_token(current_user: dict = Depends(get_current_user)):
    """
    Validate an access token.
    Used by Ticket Service to verify JWT and retrieve user info.
    """
    return {
        "user_id": current_user.get("sub"),
        "role": current_user.get("role"),
        "token_type": current_user.get("type"),
    }