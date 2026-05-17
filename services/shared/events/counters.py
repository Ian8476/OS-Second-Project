"""Contadores atomicos y locks distribuidos sobre Redis.

Se usa para sincronizar workers: cada worker incrementa el contador
del caso al terminar; cuando llega al total, el ultimo dispara la
tarea del aggregator. El lock previene doble procesamiento.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache

import redis

from services.shared.config import settings


def _counter_key(case_id: str) -> str:
    return f"case:{case_id}:done"


def _total_key(case_id: str) -> str:
    return f"case:{case_id}:total"


def _failed_key(case_id: str) -> str:
    return f"case:{case_id}:failed"


def _lock_key(subtask_id: str) -> str:
    return f"subtask:{subtask_id}:lock"


class CaseCounters:
    def __init__(self, url: str) -> None:
        self._r: redis.Redis = redis.Redis.from_url(url, decode_responses=True)

    def set_total(self, case_id: str, total: int) -> None:
        self._r.set(_total_key(case_id), total)
        self._r.set(_counter_key(case_id), 0)
        self._r.set(_failed_key(case_id), 0)

    def increment_done(self, case_id: str) -> int:
        return int(self._r.incr(_counter_key(case_id)))

    def increment_failed(self, case_id: str) -> int:
        return int(self._r.incr(_failed_key(case_id)))

    def get_progress(self, case_id: str) -> tuple[int, int, int]:
        total = int(self._r.get(_total_key(case_id)) or 0)
        done = int(self._r.get(_counter_key(case_id)) or 0)
        failed = int(self._r.get(_failed_key(case_id)) or 0)
        return done, failed, total

    def is_complete(self, case_id: str) -> bool:
        done, failed, total = self.get_progress(case_id)
        return total > 0 and (done + failed) >= total

    def cleanup(self, case_id: str) -> None:
        self._r.delete(_total_key(case_id), _counter_key(case_id), _failed_key(case_id))

    @contextmanager
    def subtask_lock(self, subtask_id: str, ttl_seconds: int = 300):
        """Lock distribuido SETNX. Si ya esta tomado, el contexto cede.

        Se usa para evitar que dos workers procesen el mismo subtask si
        RabbitMQ redespacha por timeout antes que el ACK llegue.
        """
        key = _lock_key(subtask_id)
        acquired = self._r.set(key, "1", nx=True, ex=ttl_seconds)
        try:
            yield bool(acquired)
        finally:
            if acquired:
                self._r.delete(key)


@lru_cache(maxsize=1)
def get_counters() -> CaseCounters:
    return CaseCounters(settings.redis_url)
