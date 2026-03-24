"""Auth-specific exceptions."""

from src.core.exceptions.base_exception import AppException


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class UserNotFoundException(AppException):
    def __init__(self, message: str = "User not found"):
        super().__init__(message, status_code=404)


class UserAlreadyExistsException(AppException):
    def __init__(self, message: str = "Email already registered"):
        super().__init__(message, status_code=409)


class InvalidCredentialsException(AppException):
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message, status_code=401)


class TokenExpiredException(AppException):
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, status_code=401)


class InvalidTokenException(AppException):
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, status_code=401)


