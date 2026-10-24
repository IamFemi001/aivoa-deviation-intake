"""
Application-level exceptions and the FastAPI handlers that turn them into
the stable error envelope the frontend expects:

    { "error": { "code": "SOME_CODE", "message": "Human readable message" } }

See frontend/src/services/deviationApi.js -> parseErrorResponse(), which
reads exactly this shape. Every error code used here should be one the
frontend either handles explicitly or falls back to displaying generically.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all deliberately-raised, client-facing errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "UNKNOWN_ERROR"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class EmptySourceError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "EMPTY_SOURCE"


class InvalidFileError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "INVALID_FILE"


class UnsupportedFileTypeError(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(AppError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "FILE_TOO_LARGE"


class ExtractionFailedError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "EXTRACTION_FAILED"


class AiServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "AI_SERVICE_UNAVAILABLE"


class DeviationNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "DEVIATION_NOT_FOUND"


class DatabaseError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "DATABASE_ERROR"


class ValidationFailedError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "VALIDATION_ERROR"


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning("AppError on %s %s: %s (%s)", request.method, request.url.path, exc.message, exc.code)
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # Collapse pydantic's verbose error list into one readable message
        # while keeping the stable { error: { code, message } } shape.
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        detail = first.get("msg", "Invalid request payload.")
        message = f"{field}: {detail}" if field else detail
        logger.info("Validation error on %s %s: %s", request.method, request.url.path, message)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("VALIDATION_ERROR", message),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", "Something went wrong. Please try again."),
        )
