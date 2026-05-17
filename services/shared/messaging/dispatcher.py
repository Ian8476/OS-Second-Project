"""Helper para encolar tareas con prioridad y opciones consistentes."""

from services.shared.messaging.celery_app import celery_app


def dispatch_subtask(
    task_name: str,
    subtask_id: str,
    case_id: str,
    storage_key: str | None,
    priority: int,
    queue: str,
    extra: dict | None = None,
) -> str:
    """Encola una subtarea y devuelve el `task_id` Celery.

    `priority` es el numerico de RabbitMQ (1..10). `task_id` se vuelve
    luego la clave de idempotencia en `processed_tasks`.
    """
    payload = {
        "subtask_id": subtask_id,
        "case_id": case_id,
        "storage_key": storage_key,
        "extra": extra or {},
    }
    result = celery_app.send_task(
        task_name,
        kwargs=payload,
        queue=queue,
        routing_key=queue,
        priority=priority,
    )
    return result.id


def dispatch_aggregator(case_id: str, priority: int) -> str:
    result = celery_app.send_task(
        "worker_aggregator.aggregate_case",
        kwargs={"case_id": case_id},
        queue="queue.aggregate",
        routing_key="queue.aggregate",
        priority=priority,
    )
    return result.id
