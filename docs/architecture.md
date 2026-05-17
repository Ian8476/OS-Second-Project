# Arquitectura

## Vista C4 Nivel 1 (contexto)

Actores:
- **Analyst**: sube casos y revisa hallazgos.
- **Admin**: gestiona usuarios; ve monitoreo global.

Sistema: **MediaIntel** — recibe archivos, los procesa con workers
especializados y emite reportes consolidados.

Sistemas externos:
- Almacenamiento S3 (en este proyecto, **MinIO** local).
- Broker AMQP (**RabbitMQ**) — interno pero opera como cola compartida.

## Vista C4 Nivel 2 (contenedores)

```
┌──────────────┐    HTTP+WS    ┌──────────────┐
│ React App    │──────────────►│  FastAPI     │
│  (Vite)      │               │ Gateway      │
└──────────────┘               └──────┬───────┘
                                      │
                       ┌──────────────┼─────────────────┐
                       ▼              ▼                 ▼
                 ┌──────────┐   ┌──────────┐     ┌──────────┐
                 │PostgreSQL│   │   MinIO  │     │  Redis   │
                 │ (state)  │   │ (files)  │     │ (events/ │
                 └──────────┘   └──────────┘     │  locks)  │
                                                 └─────▲────┘
                                                       │
                       FastAPI publica tareas          │
                                  │                    │
                                  ▼                    │
                            ┌──────────┐               │
                            │ RabbitMQ │               │
                            │ (broker) │               │
                            └────┬─────┘               │
            ┌───────────┬────────┼─────────┬───────────┘
            ▼           ▼        ▼         ▼
        ┌──────┐    ┌──────┐  ┌──────┐  ┌──────────┐
        │ text │    │audio │  │image │  │aggregator│
        └──────┘    └──────┘  └──────┘  └──────────┘
            │           │        │         │
            └───────────┴────────┴─────────┘
                  todos escriben en
                Postgres, MinIO, Redis
```

## Flujo end-to-end

1. **POST `/api/v1/cases`** con metadata + archivos multipart.
2. API:
   - Sube cada archivo a MinIO con clave `cases/{case_id}/{ds_id}/{filename}`.
   - Crea `case`, `data_source[]`, `subtask[]` en transacción.
   - Inicializa contador Redis: `case:{id}:total=N`, `done=0`, `failed=0`.
   - Publica una tarea Celery por subtask con prioridad numérica (1..10).
   - Emite evento `case.queued` en Redis pub/sub.
3. Workers consumen su cola (`queue.text`, `queue.audio`, `queue.image`):
   - Toman lock distribuido `SETNX subtask:{id}:lock` (idempotencia).
   - Verifican `processed_tasks` para descartar reprocesos.
   - Marcan subtask `processing` (transición auditada).
   - Procesan, persisten `finding[]`.
   - `INCR case:{id}:done`. Si llegan al total, encolan aggregator.
   - Emiten eventos `subtask.started`, `subtask.completed`, `case.progress`.
4. **Aggregator**:
   - Renderiza HTML del reporte con Jinja2.
   - Convierte a PDF con WeasyPrint.
   - Sube a MinIO bajo `cases/{id}/report/*.pdf`.
   - Marca `case.status = completed|failed`.
   - Emite `report.ready` + `case.completed`.
5. **Dashboard**:
   - Escucha WebSocket `/ws/cases/{id}` para barra de progreso.
   - Polling de fallback de 5s (TanStack Query).
   - Descarga reporte con URL pre-firmada de MinIO.

## Decisiones clave

Resumidas en [adrs/](adrs/):

- ADR-001 Fan-out / fan-in con contador atómico Redis (no Celery `chord`).
- ADR-002 Una cola por tipo de worker + prioridades por mensaje.
- ADR-003 Idempotencia obligatoria via tabla `processed_tasks`.
- ADR-004 Realtime: Redis pub/sub → WebSocket de FastAPI.
- ADR-005 Reportes con WeasyPrint (HTML→PDF) en lugar de ReportLab.

## Concurrencia y sincronización (rúbrica)

- **Concurrencia**: `--scale worker_text=4` arranca 4 procesos; cada uno
  ejecuta `--concurrency=4` hijos Celery. Hasta 16 tareas en paralelo
  por tipo de worker. Variables de entorno dejan ajustarlo sin rebuild.
- **Sincronización**:
  - Contador atómico Redis (`INCR`) para detectar completion del caso.
  - Lock distribuido (`SET NX`) por subtask antes de procesarla.
  - Semáforo Redis para el encolado único del aggregator
    (`SET NX case:{id}:aggregator_dispatched`).
- **Scheduling**:
  - Prioridades por mensaje (1, 3, 6, 10). RabbitMQ ordena dentro de cada
    cola; tareas `critical` adelantan a `low` en la misma fila.
  - `worker_prefetch_multiplier=1` evita acaparamiento.
  - `task_acks_late=True` garantiza redelivery si el worker se muere.

## Tolerancia a fallos

- Reintentos con backoff exponencial: `5, 10, 20s` y luego DLQ.
- DLQ por cola (`queue.text.dlq`, etc.) configurada en RabbitMQ.
- `task_reject_on_worker_lost=True` para mensajes huérfanos.
- Idempotencia: tabla `processed_tasks` con PK = `task_id`.
- Estado completo en BD: si el worker muere a la mitad, el contador no
  avanza y RabbitMQ redespacha la tarea al próximo consumidor libre.
