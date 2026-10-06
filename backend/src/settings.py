from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str
    AWS_BUCKET_NAME: str
    DATABASE_URL: str
    ENVIRONMENT: str = "development"
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    SQS_QUEUE_URL: str
    BEDROCK_CHAT_MODEL_ID: str
    REDIS_URI: str
    FRONTEND_URL: str = "http://localhost:8000"
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore
