"""Bus de eventos pub/sub sobre Redis.

Los workers publican y la API (websocket) reenvia al frontend. Esto
desacopla totalmente workers del transporte hacia los clientes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from functools import lru_cache

import redis

from services.shared.config import settings


class EventType(StrEnum):
    CASE_QUEUED = "case.queued"
    CASE_STARTED = "case.started"
    CASE_PROGRESS = "case.progress"
    CASE_COMPLETED = "case.completed"
    CASE_FAILED = "case.failed"
    CASE_CANCELLED = "case.cancelled"
    SUBTASK_STARTED = "subtask.started"
    SUBTASK_COMPLETED = "subtask.completed"
    SUBTASK_FAILED = "subtask.failed"
    SUBTASK_RETRYING = "subtask.retrying"
    FINDING_CREATED = "finding.created"
    REPORT_READY = "report.ready"
    ALERT_HIGH_SEVERITY = "alert.high_severity"


@dataclass
class Event:
    type: EventType
    case_id: str
    payload: dict = field(default_factory=dict)
    occurred_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_json(self) -> str:
        d = asdict(self)
        d["type"] = self.type.value if isinstance(self.type, EventType) else self.type
        return json.dumps(d, default=str)


def case_channel(case_id: str) -> str:
    return f"case:{case_id}:events"


def global_channel() -> str:
    return "mediaintel:events"


class EventBus:
    def __init__(self, url: str) -> None:
        self._redis: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    def publish(self, event: Event) -> int:
        body = event.to_json()
        published = self._redis.publish(case_channel(event.case_id), body)
        self._redis.publish(global_channel(), body)
        return published

    def subscribe(self, channels: list[str]):
        pubsub = self._redis.pubsub()
        pubsub.subscribe(*channels)
        return pubsub

    @property
    def raw(self) -> redis.Redis:
        return self._redis


@lru_cache(maxsize=1)
def get_event_bus() -> EventBus:
    return EventBus(settings.redis_pubsub_url)
