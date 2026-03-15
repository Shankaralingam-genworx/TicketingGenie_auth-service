"""Pydantic schemas for forgot/reset password endpoints."""

from pydantic import BaseModel, EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str = "If that email exists, a reset link has been sent."


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    message: str = "Password reset successful. Please log in."