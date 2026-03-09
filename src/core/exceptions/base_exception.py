"""Base exception class for the auth service."""


class AppException(Exception):
    """Base class for all custom exceptions."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
        
        

class NotFoundException(AppException):
    def __init__(self, resource: str, resource_id: int | str):
        message = f"{resource} with id '{resource_id}' not found"
        super().__init__(message, status_code=404)
