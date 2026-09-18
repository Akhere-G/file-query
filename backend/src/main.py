import logging

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from src.exceptions import AppError
from src.features.auth import user_routes

logger = logging.getLogger(__name__)


def create_app():
    app = FastAPI()
    create_exception_handlers(app)
    create_routes(app)
    return app


def create_exception_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    def handle_app_error(_, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(SQLAlchemyError)
    def handle_database_error(_, exc: SQLAlchemyError):
        logger.exception("Database request failed", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Something went wrong. Please try again."},
        )

    @app.exception_handler(Exception)
    def handle_unexpected_error(_, exc: Exception):
        logger.exception("Unhandled request error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Something went wrong. Please try again."},
        )


def create_routes(app: FastAPI):
    @app.get("/health", response_model=dict[str, str], status_code=status.HTTP_200_OK)
    def home():
        return {"status": "ok"}

    app.include_router(user_routes.router)
