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
    INTERNAL_API_SECRET: str | None = None
    FRONTEND_URL: str = "http://localhost:8000"
    RAG_SIMILARITY_THRESHOLD: float = 0.14
    RAG_TOP_K: int = 20
    RAG_RERANK_K: int = 5
    MAX_MONTHLY_MESSAGES: int = 40
    MAX_MESSAGE_LENGTH: int = 2000
    MAX_PROJECTS_PER_USER: int = 3
    MAX_FILE_SIZE: int = 1024 * 1024 * 50
    MAX_FILES_PER_REQUEST: int = 10
    MAX_PDF_PAGES: int = 300
    MAX_EXTRACTED_CHARS: int = 1_500_000
    MAX_CHUNKS_PER_FILE: int = 1000
    EMBED_CONCURRENCY: int = 4
    CHUNK_TITLE_MODE: str = "heuristic"  # "heuristic" or "llm" (one LLM call per chunk)
    MAX_USER_STORAGE: int = 1024 * 1024 * 1024 * 2
    DEMO_USER_EMAIL: str = "demo@example.com"
    DEMO_SEED_TIMEOUT_SECONDS: int = 600
    DEMO_TOKEN_EXPIRE_MINUTES: int = 120
    DEMO_MAX_DAILY_MESSAGES: int = 100
    BEDROCK_RERANK_REGION: str = "eu-central-1"
    BEDROCK_RERANK_MODEL_ARN: str = (
        "arn:aws:bedrock:eu-central-1::foundation-model/cohere.rerank-v3-5:0"
    )
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    POSTHOG_API_KEY: str | None = None
    POSTHOG_HOST: str = "https://eu.i.posthog.com"
    POSTHOG_ID_SALT: str | None = None
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore
