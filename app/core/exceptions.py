import logging 
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

try:
    from sqlalchemy.exc import SQLAlchemyError
except Exception:
    SQLAlchemyError = tuple()

logger = logging.getLogger(__name__)

class AppError(Exception):
    """
    Base application error (maps to 500 by default)
    """
    status_code: int = 500
    code: str = "app_error"

    def __init__(self, message:str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.message = message

class NotFoundError(AppError):
    status_code: int = 404
    code: str = "not_found"

class UnauthorizedError(AppError):
    status_code: int = 401
    code: str = "unauthorized"

class ForbiddenError(AppError):
    status_code: int = 403
    code: str = "forbidden"

class ConflictError(AppError):
    status_code: int = 409
    code: str = "conflict"

def add_exception_handlers(app: FastAPI) -> None:
    """
    Add exception handlers to the FastAPI app.
    """
    @app.exception_handler(AppError)
    async def _app_error_handler(_:Request, exc: AppError) -> JSONResponse:
        logger.warning(f"AppError: {exc.code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}}
        )
    
    @app.exception_handler(ValidationError)
    async def _validation_error_handler(_:Request, exc: ValidationError) -> JSONResponse:
        logger.warning(f"ValidationError: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": "Invalid request", "details": exc.errors()}},
        )
    
    if SQLAlchemyError:
        @app.exception_handler(SQLAlchemyError)
        async def _sqlalchemy_error_handler(_:Request, exc: SQLAlchemyError) -> JSONResponse:
            logger.error(f"Database error: {exc}")
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "db_error", "message": "A database error occurred", "details": str(exc)}},
            )
    
    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.error("Unhandled server error", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "server_error", "message": "Internal server error."}},
        )
            