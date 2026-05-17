"""Cliente MinIO compartido."""

from services.shared.storage.minio_client import MinioStorage, get_storage

__all__ = ["MinioStorage", "get_storage"]
