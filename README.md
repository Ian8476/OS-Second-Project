# MediaIntel — Análisis Multiproceso y Distribuido v2.0

**Curso:** IC-4300 Sistemas Operativos — ITCR San Carlos
**Versión:** 1.0.0
**Entrega:** 10 de junio de 2026

Sistema distribuido y multiproceso para análisis de texto, audio e imagen
proveniente de aplicaciones de mensajería. La carga útil del proyecto no es
la IA: es la **infraestructura** (procesos, colas, sincronización,
escalabilidad, tolerancia a fallos).

---

## Stack

| Capa | Tecnología |
|---|---|
| API Gateway | FastAPI (Python 3.11) |
| Broker | RabbitMQ 3.13 con colas + prioridades |
| Workers | Celery 5 + procesos Python por tipo de carga |
| DB | PostgreSQL 16 |
| Storage | MinIO (S3 compatible) |
| Cache + pub/sub | Redis 7 |
| Dashboard | React 19 + Vite + TanStack Query + WebSockets |
| Monitoreo | Flower + Prometheus + Grafana |
| Análisis texto | VADER + listas de keywords |
| Análisis audio | faster-whisper (CPU, modelo tiny) |
| Análisis imagen | YOLOv8n (Ultralytics) |

Toda la documentación de decisiones está en [`docs/adrs/`](docs/adrs).

---

## Quickstart (10 minutos)

```bash
# 1. Copiar variables de entorno y arrancar todo
cp .env.example .env
docker compose up -d --build

# 2. Aplicar migraciones (lo hace el API al arrancar, pero por si acaso)
docker compose exec api alembic -c /app/services/shared/alembic.ini upgrade head

# 3. Crear usuarios demo (admin + analyst)
docker compose exec api python -m services.api.app.infrastructure.seed
```

Servicios y puertos:

| Servicio | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API | http://localhost:8000 (docs en `/docs`) |
| Flower | http://localhost:5555 |
| RabbitMQ | http://localhost:15672 (mediaintel / mediaintel_dev) |
| MinIO console | http://localhost:9001 (mediaintel / mediaintel_dev) |
| Grafana | http://localhost:3000 (admin / admin) |
| Prometheus | http://localhost:9090 |

**Credenciales demo:**
- Admin: `admin@mediaintel.local` / `ChangeMe123!`
- Analyst: `analyst@mediaintel.local` / `ChangeMe123!`

---

## Cómo escalar horizontalmente

```bash
# Más workers de texto para procesar una avalancha de mensajes
docker compose up -d --scale worker_text=4

# Más workers de imagen sin tocar el resto
docker compose up -d --scale worker_image=3
```

Cada worker es un proceso/contenedor independiente con su propia pool de
concurrency interna (`celery --concurrency`). Esto demuestra a la vez
escalado de procesos (entre contenedores) y de hilos/sub-procesos
(dentro de cada worker).

---

## Demostración de conceptos del curso

| Concepto SO | Dónde lo demuestra el sistema |
|---|---|
| Concurrencia | N workers Celery procesan en paralelo distintas colas |
| Sincronización | Contadores atómicos Redis + locks distribuidos (SETNX) por subtask |
| IPC | AMQP entre API↔workers, Redis pub/sub entre workers↔API↔frontend |
| Scheduling | RabbitMQ priority queues (1=low … 10=critical) en la misma cola |
| Tolerancia a fallos | Reintentos con backoff exponencial + DLQ por cola |
| Gestión de procesos | Concurrency configurable por tipo de worker (env vars) |
| Recursos | Límites de memoria/CPU por contenedor (Compose); pool size en DB y MinIO |
| Estados | Máquina de estados explícita (`services/shared/state_machine.py`) auditada en `case_state_history` |

---

## Arquitectura (resumen)

```
React Dashboard ──HTTP/WS──► FastAPI ──AMQP──► RabbitMQ ──► [text|audio|image] workers
                                │                                │
                                ├──► PostgreSQL ◄────────────────┤
                                ├──► MinIO ◄─────────────────────┤
                                └──► Redis pub/sub ◄─────────────┘
                                                                 │
                                                         ┌───────▼────────┐
                                                         │ Aggregator     │
                                                         │ → reporte PDF  │
                                                         └────────────────┘
```

Detalle completo y diagramas en [`docs/architecture.md`](docs/architecture.md).

---

## Ejecución de tests

```bash
# Tests Python (pure functions, sin broker ni DB)
docker compose run --rm api pytest services/api/tests
docker compose run --rm worker_text pytest services/worker_text/tests
docker compose run --rm worker_image pytest services/worker_image/tests
docker compose run --rm worker_aggregator pytest services/worker_aggregator/tests

# Tests dashboard
cd dashboard && npm install && npm test
```

---

## Pruebas de carga (Locust)

```bash
docker run --rm -p 8089:8089 -v $(pwd)/loadtests:/mnt/locust \
  locustio/locust -f /mnt/locust/locustfile.py --host http://host.docker.internal:8000
```

Abrir http://localhost:8089 y disparar 10 / 50 / 100 usuarios.

Los resultados deberían ir en `docs/performance.md` (ver Sprint 5).

---

## Estructura del repositorio

```
.
├── docker-compose.yml          # 11 servicios orquestados
├── docker-compose.override.yml # hot-reload para dev
├── services/
│   ├── api/                    # FastAPI gateway (Clean Architecture)
│   ├── worker_text/            # Análisis de texto
│   ├── worker_audio/           # Whisper + reanálisis del transcript
│   ├── worker_image/           # YOLOv8n + clasificación
│   ├── worker_aggregator/      # Fan-in y generación de reporte PDF
│   └── shared/                 # Modelos, Celery, MinIO, Redis bus, Alembic
├── dashboard/                  # React 19 + Vite (CSS Modules + i18n)
├── infra/                      # Configs de Rabbit / Prom / Grafana
├── loadtests/                  # Locust
└── docs/                       # ADRs, arquitectura, deployment, API
```

---

## Roadmap por sprints

Ver [`PLANNING.md`](PLANNING.md). El repositorio implementa Sprints 0–3
completos y deja Sprints 4–6 (alertas avanzadas, hardening de seguridad,
documentación final del reporte académico) como trabajo de pulido.

---

## Equipo

Definir en `PLANNING.md §9` antes del kick-off.
