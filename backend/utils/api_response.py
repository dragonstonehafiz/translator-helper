from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from utils.logger import setup_logger


ApiResponse = dict[str, Any]
logger = setup_logger()


def api_response(status: str, message: str | None = None, data: Any = None) -> ApiResponse:
    return {
        "status": status,
        "message": message,
        "data": data,
    }


def success_response(data: Any = None, message: str | None = None) -> ApiResponse:
    return api_response("success", message=message, data=data)


def processing_response(data: Any = None, message: str | None = None) -> ApiResponse:
    return api_response("processing", message=message, data=data)


def loading_response(data: Any = None, message: str | None = None) -> ApiResponse:
    return api_response("loading", message=message, data=data)


def complete_response(data: Any = None, message: str | None = None) -> ApiResponse:
    return api_response("complete", message=message, data=data)


def idle_response(data: Any = None, message: str | None = None) -> ApiResponse:
    return api_response("idle", message=message, data=data)


def error_response(message: str, data: Any = None) -> ApiResponse:
    return api_response("error", message=message, data=data)


def normalize_task_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if result is None:
        return None

    normalized = dict(result)
    normalized.pop("type", None)
    if "data" in normalized:
        normalized["text"] = normalized.pop("data")
    return normalized


def task_result_data(
    task_type: str,
    result: dict[str, Any] | None = None,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "result": normalize_task_result(result),
        "progress": progress,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(str(exc.detail)),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_response("Invalid request data.", {"details": exc.errors()}),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled API exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_response("Internal server error."),
        )
