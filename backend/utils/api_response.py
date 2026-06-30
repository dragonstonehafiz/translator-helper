from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from utils.logger import setup_logger


ApiResponse = dict[str, Any]
logger = setup_logger()


def api_response(status: str, message: str | None = None, data: Any = None) -> ApiResponse:
    """Build the standard `{status, message, data}` envelope used by every JSON endpoint."""
    return {
        "status": status,
        "message": message,
        "data": data,
    }


def success_response(data: Any = None, message: str | None = None) -> ApiResponse:
    """Return a success-status envelope."""
    return api_response("success", message=message, data=data)


def processing_response(data: Any = None, message: str | None = None) -> ApiResponse:
    """Return a processing-status envelope (task has started but not finished)."""
    return api_response("processing", message=message, data=data)


def loading_response(data: Any = None, message: str | None = None) -> ApiResponse:
    """Return a loading-status envelope (model is being loaded)."""
    return api_response("loading", message=message, data=data)


def complete_response(data: Any = None, message: str | None = None) -> ApiResponse:
    """Return a complete-status envelope (task finished successfully)."""
    return api_response("complete", message=message, data=data)


def idle_response(data: Any = None, message: str | None = None) -> ApiResponse:
    """Return an idle-status envelope (no task is running or queued)."""
    return api_response("idle", message=message, data=data)


def error_response(message: str, data: Any = None) -> ApiResponse:
    """Return an error-status envelope with a human-readable message."""
    return api_response("error", message=message, data=data)


def task_result_data(
    task_type: str,
    result: dict[str, Any] | None = None,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the `data` payload shape returned by every task-result polling response."""
    return {
        "task_type": task_type,
        "result": result,
        "progress": progress,
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers that return the standard API envelope for HTTP, validation, and unhandled errors."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Convert FastAPI HTTPException to an error-envelope JSON response."""
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(str(exc.detail)),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Convert Pydantic/FastAPI validation errors to a 422 error-envelope JSON response."""
        return JSONResponse(
            status_code=422,
            content=error_response("Invalid request data.", {"details": exc.errors()}),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch all other unhandled exceptions and return a 500 error-envelope JSON response."""
        logger.error("Unhandled API exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_response("Internal server error."),
        )
