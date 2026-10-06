import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError
from src.exceptions import AppError
from src.features.auth import user_routes
from src.features.chat import chat_routes
from src.features.files import file_routes
from src.features.project import project_routes
from src.limiter import limiter
from src.settings import settings

logger = logging.getLogger(__name__)


def create_app():
    app = FastAPI()
    create_exception_handlers(app)
    register_models()
    configure_app(app)
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


def register_models():
    from src.features.auth.user_model import User
    from src.features.chat.message_model import Citation, Message, MessageOwner
    from src.features.files.file_model import Chunk, File, Project


def configure_app(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", settings.FRONTEND_URL],
        allow_credentials=True,
        allow_headers=["*"],
        allow_methods=["*"],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore


def create_routes(app: FastAPI):
    @app.get("/health", response_model=dict[str, str], status_code=status.HTTP_200_OK)
    def home():
        return {"status": "ok"}

    app.include_router(user_routes.router)
    app.include_router(file_routes.router)
    app.include_router(project_routes.router)
    app.include_router(chat_routes.router)


app = create_app()
