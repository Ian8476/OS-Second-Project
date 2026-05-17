"""Healthcheck simple. Permite que Docker healthcheck/k8s lo consulten."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
