"""Configuracion de logging estructurado (JSON) con structlog.

Todos los servicios deben llamar a `setup_logging()` en su entrypoint.
"""

import logging
import sys

import structlog


def setup_logging(level: str = "INFO", service_name: str | None = None) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if service_name:
        shared_processors.insert(0, _service_processor(service_name))

    structlog.configure(
        processors=shared_processors + [structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _service_processor(service_name: str):
    def _add_service(_, __, event_dict):
        event_dict["service"] = service_name
        return event_dict

    return _add_service


def get_logger(name: str | None = None):
    return structlog.get_logger(name) if name else structlog.get_logger()
