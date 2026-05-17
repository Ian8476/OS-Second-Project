"""Wrapper minimo sobre el SDK oficial de MinIO.

Convencion de keys: `{case_id}/{data_source_id}/{filename}`.
"""

from __future__ import annotations

import io
import os
from functools import lru_cache
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from services.shared.config import settings


class MinioStorage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self._client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self.bucket):
            self._client.make_bucket(self.bucket)

    def put_object(
        self,
        key: str,
        data: BinaryIO,
        size: int,
        content_type: str | None = None,
    ) -> str:
        self._client.put_object(
            bucket_name=self.bucket,
            object_name=key,
            data=data,
            length=size,
            content_type=content_type or "application/octet-stream",
        )
        return key

    def put_bytes(
        self, key: str, data: bytes, content_type: str | None = None
    ) -> str:
        return self.put_object(
            key, io.BytesIO(data), len(data), content_type=content_type
        )

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def download_to_tempfile(self, key: str, suffix: str = "") -> str:
        import tempfile

        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self._client.fget_object(self.bucket, key, path)
        return path

    def presigned_get(self, key: str, expires_seconds: int = 3600) -> str:
        from datetime import timedelta

        return self._client.presigned_get_object(
            self.bucket, key, expires=timedelta(seconds=expires_seconds)
        )

    def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self.bucket, key)
            return True
        except S3Error:
            return False


@lru_cache(maxsize=1)
def get_storage() -> MinioStorage:
    return MinioStorage(
        endpoint=f"{settings.minio_host}:{settings.minio_port}",
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        bucket=settings.minio_bucket,
        secure=settings.minio_use_ssl,
    )
