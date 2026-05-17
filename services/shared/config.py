"""Configuracion global cargada desde variables de entorno.

Se usa una unica instancia exportada como `settings`. Cualquier servicio
puede importarla; pydantic-settings valida que las variables requeridas
existan al instanciarse.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "mediaintel"
    log_level: str = "INFO"

    # JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Postgres
    database_url: str = Field(
        default="postgresql+psycopg://mediaintel:mediaintel_dev@postgres:5432/mediaintel"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://mediaintel:mediaintel_dev@postgres:5432/mediaintel"
    )

    # Celery / RabbitMQ
    celery_broker_url: str = "amqp://mediaintel:mediaintel_dev@rabbitmq:5672//"
    celery_result_backend: str = "redis://redis:6379/1"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_pubsub_url: str = "redis://redis:6379/2"

    # MinIO
    minio_host: str = "minio"
    minio_port: int = 9000
    minio_root_user: str = "mediaintel"
    minio_root_password: str = "mediaintel_dev"
    minio_bucket: str = "mediaintel-cases"
    minio_use_ssl: bool = False

    # Workers
    worker_queue: str = "queue.text"
    worker_concurrency: int = 4
    task_max_retries: int = 3
    task_retry_backoff_base: int = 5
    task_soft_time_limit: int = 120
    task_hard_time_limit: int = 180

    # ML
    whisper_model_size: str = "tiny"
    yolo_model: str = "yolov8n.pt"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
