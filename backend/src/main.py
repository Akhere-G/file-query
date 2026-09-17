from fastapi import FastAPI
from src.features.auth import user_routes


def create_app():
    app = FastAPI()
    create_routes(app)
    return app


def create_routes(app: FastAPI):
    @app.get("/health")
    def home():
        return {"message": "Ok"}

    app.include_router(user_routes.router)
