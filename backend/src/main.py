from fastapi import FastAPI


def create_app():
    app = FastAPI()
    create_routes(app)
    return app


def create_routes(app):
    @app.get("/")
    def home():
        return {"mmessage": "Hello World"}
