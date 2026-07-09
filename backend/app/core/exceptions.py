"""Global exception handling for AgentForge."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception with HTTP status code."""
    status_code: int = 500
    message: str = "Internal server error"

    def __init__(self, message: str | None = None, status_code: int | None = None):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    status_code = 404
    message = "Resource not found"


class UnauthorizedException(AppException):
    status_code = 401
    message = "Authentication required"


class ForbiddenException(AppException):
    status_code = 403
    message = "Permission denied"


class ValidationException(AppException):
    status_code = 422
    message = "Validation error"


def register_exception_handlers(app: FastAPI):
    """Register all custom exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "status_code": exc.status_code},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "status_code": 422},
        )
