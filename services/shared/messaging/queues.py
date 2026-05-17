"""Definicion de colas con soporte de prioridades.

Cada cola usa el argumento `x-max-priority` de RabbitMQ para permitir
que tareas criticas se procesen antes que tareas low en la misma cola.
Esta es la forma idiomatica de implementar prioridades en AMQP 0.9.1.
"""

from kombu import Exchange, Queue

EXCHANGE_NAME = "mediaintel.tasks"
DLX_NAME = "mediaintel.dlx"

QUEUE_TEXT = "queue.text"
QUEUE_AUDIO = "queue.audio"
QUEUE_IMAGE = "queue.image"
QUEUE_AGGREGATE = "queue.aggregate"

_default_exchange = Exchange(EXCHANGE_NAME, type="direct", durable=True)
_dlx = Exchange(DLX_NAME, type="direct", durable=True)


def _priority_queue(name: str) -> Queue:
    return Queue(
        name,
        _default_exchange,
        routing_key=name,
        queue_arguments={
            "x-max-priority": 10,
            "x-dead-letter-exchange": DLX_NAME,
            "x-dead-letter-routing-key": f"{name}.dlq",
        },
    )


CELERY_TASK_QUEUES = (
    _priority_queue(QUEUE_TEXT),
    _priority_queue(QUEUE_AUDIO),
    _priority_queue(QUEUE_IMAGE),
    _priority_queue(QUEUE_AGGREGATE),
    Queue(f"{QUEUE_TEXT}.dlq", _dlx, routing_key=f"{QUEUE_TEXT}.dlq"),
    Queue(f"{QUEUE_AUDIO}.dlq", _dlx, routing_key=f"{QUEUE_AUDIO}.dlq"),
    Queue(f"{QUEUE_IMAGE}.dlq", _dlx, routing_key=f"{QUEUE_IMAGE}.dlq"),
    Queue(f"{QUEUE_AGGREGATE}.dlq", _dlx, routing_key=f"{QUEUE_AGGREGATE}.dlq"),
)

CELERY_TASK_ROUTES = {
    "worker_text.*": {"queue": QUEUE_TEXT},
    "worker_audio.*": {"queue": QUEUE_AUDIO},
    "worker_image.*": {"queue": QUEUE_IMAGE},
    "worker_aggregator.*": {"queue": QUEUE_AGGREGATE},
}
