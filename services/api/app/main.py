"""Entrypoint del API Gateway.

Aplica:
- Logging estructurado
- CORS
- Metricas Prometheus
- Rate limiting (slowapi)
- Routers v1
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from services.api.app.api.v1 import auth, cases, health, reports, ws
from services.api.app.core.exceptions import register_exception_handlers
from services.shared.config import settings
from services.shared.logging_setup import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging(level=settings.log_level, service_name="api")
    yield


limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


def create_app() -> FastAPI:
    app = FastAPI(
        title="MediaIntel API",
        version="1.0.0",
        description="Gateway del sistema distribuido de analisis multimedia.",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limit_handler(_, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429, content={"detail": "rate_limited", "limit": str(exc)}
        )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(ws.router, prefix="/ws", tags=["ws"])

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    return app


app = create_app()
