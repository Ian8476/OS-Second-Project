# Planning del Proyecto — Análisis Multiproceso y Distribuido de Datos en Aplicaciones de Mensajería v2.0

**Curso:** IC-4300 Sistemas Operativos — ITCR San Carlos
**Fecha de entrega:** 10 de junio de 2026
**Fecha actual:** 16 de mayo de 2026
**Ventana de ejecución:** ~25 días naturales

---

## 0. Resumen ejecutivo (conclusión primero)

El proyecto **no** es un proyecto de IA, es un proyecto de **infraestructura distribuida y multiproceso** donde la "carga de trabajo" da la vuelta a ser el análisis de texto/audio/imagen. La rúbrica lo confirma: el 55% de la nota está en arquitectura distribuida (20%), concurrencia (15%), gestión de cargas (10%) y escalabilidad/rendimiento (10%). El análisis multimedia pesa solo 10%.

**Stack recomendado para producción académica (no prototipo):**

| Capa | Tecnología | Por qué |
|---|---|---|
| API Gateway / Ingest | **FastAPI** (Python 3.11+) | Asíncrono nativo, validación con Pydantic, fácil de instrumentar. |
| Broker de tareas | **RabbitMQ** | Soporta colas con prioridad nativas (clave para el apartado de scheduling), DLQ, ACKs manuales. Más didáctico que Redis Streams para demostrar conceptos de SO. |
| Orquestador de workers | **Celery 5** | Integración nativa con RabbitMQ, soporta prioridades, retries con backoff exponencial, routing por queue. |
| Workers especializados | **Procesos Python independientes** (uno por tipo de dato) | Aísla CPU/memoria por tipo de carga, permite escalar horizontal cada tipo por separado. |
| Persistencia transaccional | **PostgreSQL 16** | Casos, estados, metadatos, auditoría. |
| Almacenamiento de archivos | **MinIO** (S3-compatible) | Self-hosted, gratis, simula S3 en local. |
| Caché y pub/sub en vivo | **Redis 7** | Estado en tiempo real del dashboard, locks distribuidos. |
| Dashboard | **React 19 + Vite** + WebSockets | Lo dominas y reusas la arquitectura de ReadFlow. |
| Realtime al frontend | **WebSockets vía FastAPI** + Redis pub/sub como bus | Cumple el requisito de "actualización asincrónica". |
| Contenedorización | **Docker + Docker Compose** | Mismo enfoque que ya usaste en Bases de Datos II. |
| Monitoreo | **Flower** (Celery) + **Prometheus + Grafana** | Flower cubre lo básico; Prometheus/Grafana suben la nota de la categoría de monitoreo. |
| Análisis Texto | **spaCy** + **VADER** + listas de keywords | Cero costo, rápido, suficiente para academia. |
| Análisis Audio | **faster-whisper** (modelo `tiny` o `base`) | CPU-friendly, mucho más rápido que Whisper original. |
| Análisis Imagen | **YOLOv8n** (Ultralytics) + **OpenCV** | Modelo ligero, detección de objetos lista. |

**Alternativas y por qué NO las elegiría como primera opción:**

- **Kafka**: overkill para 25 días, curva de aprendizaje alta, no aporta nada que RabbitMQ no haga para esta escala.
- **Redis Queue (RQ)** sin Celery: más simple, pero pierdes el soporte limpio de prioridades multinivel y routing por cola que es justo lo que la rúbrica premia.
- **Microservicios "puros"** (un servicio HTTP por análisis): añade complejidad de service discovery sin beneficio real. Los workers Celery ya son servicios desacoplados.

---

## 1. Mapeo de requisitos del enunciado a entregables técnicos

Antes de planificar tareas, hay que asegurar que **cada categoría de la rúbrica tiene un componente concreto que la evidencia**. Si algo no se mapea, no se entrega.

| Categoría rúbrica | % | Evidencia técnica concreta |
|---|---|---|
| Arquitectura Distribuida | 20% | Docker Compose con >= 6 servicios separados (API, broker, 3 tipos de worker, DB, Redis, MinIO, dashboard). Diagrama C4 nivel 1 y 2. |
| Gestión de Procesos y Concurrencia | 15% | Celery con N workers concurrentes por tipo, locks distribuidos en Redis para evitar doble procesamiento, semáforos para limitar concurrencia por tipo de recurso. |
| Gestión de Cargas de Trabajo | 10% | Máquina de estados explícita: `queued → processing → completed/failed/retrying/cancelled`. Tabla `case_state_history`. Endpoint de cancelación. |
| Procesamiento Multimedia | 10% | 3 workers reales (texto/audio/imagen) que devuelven hallazgos estructurados. |
| Dashboard y Monitoreo | 10% | Dashboard React + Flower + Grafana. Vista de workers activos, casos en cola, throughput. |
| Reportes y Evidencias | 10% | PDF/HTML consolidado por caso con timestamps, fragmentos, categorías, severidad. |
| Escalabilidad y Rendimiento | 10% | Pruebas de carga con `locust`, gráfica de throughput vs N° de workers, demo de escalado horizontal (`docker compose up --scale worker_text=4`). |
| Seguridad y Acceso | 5% | JWT para API, cifrado de archivos en MinIO (server-side), roles `admin`/`analyst`. |
| Documentación Técnica | 5% | README, diagramas, ADRs (Architecture Decision Records), `docs/deployment.md`. |
| Repositorio y Buenas Prácticas | 5% | Monorepo organizado, conventional commits, GitHub Actions con lint+tests. |

---

## 2. Arquitectura objetivo

### 2.1. Vista lógica (C4 nivel 2)

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   React     │◄────►│   FastAPI    │─────►│   PostgreSQL    │
│  Dashboard  │  WS  │  API Gateway │      │  (casos/estado) │
└─────────────┘      └──────┬───────┘      └─────────────────┘
                            │
                            │ publish task
                            ▼
                     ┌──────────────┐
                     │   RabbitMQ   │  ◄── colas con prioridad
                     │   (broker)   │       low / med / high / critical
                     └──────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
      ┌──────────┐    ┌──────────┐    ┌──────────┐
      │ Worker   │    │ Worker   │    │ Worker   │
      │  Text    │    │  Audio   │    │  Image   │
      │  pool    │    │  pool    │    │  pool    │
      └────┬─────┘    └────┬─────┘    └────┬─────┘
           │               │               │
           └───────┬───────┴───────┬───────┘
                   ▼               ▼
            ┌────────────┐  ┌────────────┐
            │  MinIO     │  │   Redis    │
            │ (archivos) │  │ (estado+   │
            │            │  │  pub/sub)  │
            └────────────┘  └────────────┘
                   │
                   ▼
            ┌────────────┐
            │ Aggregator │  ◄── arma reporte cuando todos los
            │   Worker   │      sub-jobs del caso terminan
            └────────────┘
```

### 2.2. Decisiones de arquitectura clave (ADRs resumidos)

**ADR-001: Un caso = N sub-tareas (fan-out / fan-in)**
Un caso de análisis puede traer 100 mensajes + 20 imágenes + 5 audios. No procesar como una sola tarea monolítica: hacer **fan-out** (una sub-tarea Celery por unidad) y **fan-in** con un `chord` de Celery o un aggregator que cuenta sub-jobs completados en Redis. Esto demuestra **paralelismo real** y **sincronización** (los dos pilares de la nota de SO).

**ADR-002: Colas separadas por tipo de worker**
`queue.text`, `queue.audio`, `queue.image`, `queue.aggregate`. Permite escalar independiente y evita que un audio lento bloquee 100 mensajes de texto rápidos. Conecta directamente con el concepto de **colas multinivel** que pide el enunciado.

**ADR-003: Prioridades a nivel de mensaje, no de cola**
RabbitMQ soporta `x-max-priority` por cola; usar valores `1=low, 2=med, 5=high, 10=critical`. Más limpio que tener cuatro colas por tipo de worker (12 colas en total). Permite hablar de **starvation** y **fairness** sin construir colas multinivel manualmente.

**ADR-004: Idempotencia obligatoria en workers**
Toda tarea debe poder reejecutarse sin efectos secundarios duplicados. Implementar con clave `task_id` única en una tabla `processed_tasks`. Esto cubre el requisito de **tolerancia a fallos** y permite usar reintentos con confianza.

**ADR-005: Comunicación realtime vía Redis pub/sub → WebSocket**
Los workers publican eventos en canales Redis (`case:{id}:progress`). FastAPI los reenvía por WebSocket al dashboard. Esto desacopla totalmente workers del frontend.

---

## 3. Modelo de datos (PostgreSQL)

```sql
-- Casos de análisis
cases (
  id UUID PRIMARY KEY,
  owner_id UUID,
  title TEXT,
  priority SMALLINT,  -- 1,2,5,10
  status TEXT,        -- queued, processing, completed, failed, retrying, cancelled
  created_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  total_subtasks INT,
  completed_subtasks INT,
  failed_subtasks INT
)

-- Fuentes de datos asociadas al caso
data_sources (
  id UUID PRIMARY KEY,
  case_id UUID REFERENCES cases(id),
  type TEXT,          -- 'text', 'audio', 'image', 'video', 'doc'
  storage_key TEXT,   -- ruta en MinIO
  size_bytes BIGINT,
  metadata JSONB
)

-- Sub-tareas (una por unidad procesable)
subtasks (
  id UUID PRIMARY KEY,
  case_id UUID REFERENCES cases(id),
  data_source_id UUID REFERENCES data_sources(id),
  worker_type TEXT,
  status TEXT,
  attempts SMALLINT DEFAULT 0,
  result JSONB,
  error TEXT,
  enqueued_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ
)

-- Hallazgos (lo que se muestra como evidencia)
findings (
  id UUID PRIMARY KEY,
  case_id UUID REFERENCES cases(id),
  subtask_id UUID REFERENCES subtasks(id),
  category TEXT,      -- 'violence', 'threats', 'offensive', 'weapon_detected', ...
  severity SMALLINT,  -- 1..5
  confidence NUMERIC, -- 0..1
  evidence JSONB,     -- snippet, timestamp_ms, bbox, keywords, etc.
  created_at TIMESTAMPTZ
)

-- Auditoría de estados (didáctico para la defensa)
case_state_history (
  id BIGSERIAL PRIMARY KEY,
  case_id UUID,
  from_status TEXT,
  to_status TEXT,
  changed_at TIMESTAMPTZ,
  reason TEXT
)

-- Usuarios y roles
users (id UUID, email, password_hash, role)  -- 'admin' | 'analyst'
```

---

## 4. Estructura del repositorio (monorepo)

```
project-root/
├── docker-compose.yml
├── docker-compose.override.yml          # dev
├── .env.example
├── README.md
├── docs/
│   ├── architecture.md
│   ├── adrs/
│   ├── deployment.md
│   ├── api.md
│   └── diagrams/                        # draw.io + PNG export
├── services/
│   ├── api/                             # FastAPI gateway
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/
│   │   │   │   └── v1/
│   │   │   │       ├── cases.py
│   │   │   │       ├── auth.py
│   │   │   │       ├── reports.py
│   │   │   │       └── ws.py
│   │   │   ├── core/                    # config, security, db
│   │   │   ├── domain/                  # entidades + reglas
│   │   │   ├── application/             # casos de uso
│   │   │   ├── infrastructure/          # repos, brokers
│   │   │   └── schemas/                 # pydantic DTOs
│   │   └── tests/
│   ├── worker_text/
│   │   ├── tasks.py
│   │   ├── analyzers/
│   │   │   ├── keyword.py
│   │   │   ├── sentiment.py
│   │   │   └── offensive.py
│   │   └── tests/
│   ├── worker_audio/
│   │   ├── tasks.py
│   │   ├── transcriber.py               # faster-whisper
│   │   └── tests/
│   ├── worker_image/
│   │   ├── tasks.py
│   │   ├── detectors/
│   │   │   ├── yolo_objects.py
│   │   │   └── content_filter.py
│   │   └── tests/
│   ├── worker_aggregator/
│   │   ├── tasks.py
│   │   └── report_builder.py
│   └── shared/
│       ├── models/                      # SQLAlchemy + alembic
│       ├── messaging/                   # celery_app, queues, priorities
│       ├── storage/                     # MinIO client wrapper
│       └── events/                      # event types y publishers
├── dashboard/                           # React 19 + Vite
│   ├── src/
│   │   ├── features/
│   │   │   ├── cases/
│   │   │   ├── monitoring/
│   │   │   ├── reports/
│   │   │   └── auth/
│   │   ├── shared/
│   │   └── app/
│   └── tests/
├── infra/
│   ├── rabbitmq/                        # definitions.json con colas, prioridades
│   ├── postgres/                        # init.sql
│   ├── prometheus/
│   ├── grafana/                         # dashboards.json
│   └── nginx/                           # opcional, reverse proxy
├── loadtests/
│   └── locustfile.py
└── .github/workflows/
    ├── ci.yml                           # lint + tests
    └── docker-build.yml
```

> Nota: la separación `domain / application / infrastructure` en el API aplica directamente las preferencias de Clean Architecture y SRP que ya manejas en proyectos previos.

---

## 5. Flujo end-to-end (con énfasis en concurrencia y sincronización)

1. **POST `/api/v1/cases`** con metadata + lista de archivos.
2. API sube archivos a MinIO, persiste `case` con estado `queued`, crea N `data_sources` y N `subtasks`.
3. API publica una **tarea por sub-tarea** en la cola correspondiente con la prioridad del caso.
4. Workers consumen en paralelo. Cada uno:
   - Toma un lock en Redis (`SETNX subtask:{id}:lock`) — evita procesamiento doble si dos workers compiten.
   - Marca subtask como `processing` (transición auditada).
   - Procesa, escribe `findings`.
   - Incrementa contador atómico en Redis (`INCR case:{id}:done`).
   - Publica evento en Redis pub/sub.
5. Cuando `done == total_subtasks`, el último worker dispara la tarea del **Aggregator**.
6. Aggregator construye el reporte consolidado, actualiza caso a `completed`, notifica vía WebSocket.

**Puntos donde se demuestra cada concepto del curso:**

- **Concurrencia**: N workers procesan simultáneamente.
- **Sincronización**: contador atómico Redis + lock distribuido + chord/fan-in.
- **IPC**: AMQP entre productores y consumidores; Redis pub/sub para eventos.
- **Scheduling**: prioridades de RabbitMQ + concurrency por cola.
- **Tolerancia a fallos**: retry con backoff exponencial, dead-letter queue.
- **Recursos**: límite de procesos por worker (`--concurrency`), memoria controlada por contenedor.

---

## 6. Plan de trabajo por sprints (25 días)

> **Estrategia general:** vertical slice primero. Día 7 ya debe haber un caso entrando por API, una tarea procesándose por un worker y un estado visible. Lo demás se agrega encima sin romper.

### Sprint 0 — Setup y diseño (Días 1–3, 16–18 mayo)

- [ ] Crear repo, README inicial, `.gitignore`, licencia.
- [ ] Definir ADRs 001–005 en `docs/adrs/`.
- [ ] Diagrama C4 nivel 1 y 2 en draw.io.
- [ ] Diagrama de secuencia del flujo end-to-end.
- [ ] `docker-compose.yml` con: postgres, rabbitmq (con `definitions.json` precargado), redis, minio.
- [ ] Verificar que los 4 servicios levantan y se ven en sus respectivas UIs de admin.
- [ ] Crear esquema de DB con Alembic (migración inicial).
- [ ] Estructura de carpetas del monorepo creada y vacía.

**Criterio de cierre:** `docker compose up` levanta infra base; `alembic upgrade head` aplica migraciones.

### Sprint 1 — Vertical slice mínima (Días 4–7, 19–22 mayo)

- [ ] FastAPI con endpoint `POST /cases` que persiste un caso y sube archivos a MinIO.
- [ ] Celery app configurada apuntando a RabbitMQ.
- [ ] **Solo worker_text** con una tarea trivial (contar palabras) que actualiza subtask.
- [ ] Endpoint `GET /cases/{id}` devuelve estado.
- [ ] Logging estructurado (JSON) en todos los servicios con `structlog`.

**Criterio de cierre:** crear caso por curl/Postman → ver subtask `completed` en DB en < 5s.

### Sprint 2 — Multi-worker y fan-out/fan-in (Días 8–11, 23–26 mayo)

- [ ] Implementar `worker_audio` con `faster-whisper` (modelo `tiny`).
- [ ] Implementar `worker_image` con YOLOv8n.
- [ ] Implementar `worker_aggregator` que arma reporte cuando todas las subtasks de un caso terminan.
- [ ] Mecanismo de contador atómico en Redis + trigger del aggregator.
- [ ] Prioridades en RabbitMQ funcionando (probar con caso `critical` que adelanta a 50 `low`).
- [ ] Retries con backoff exponencial + DLQ.
- [ ] Endpoint de cancelación (`POST /cases/{id}/cancel`).

**Criterio de cierre:** caso con texto + audio + imagen se procesa en paralelo, aggregator emite reporte.

### Sprint 3 — Dashboard y realtime (Días 12–15, 27–30 mayo)

- [ ] React 19 + Vite con la estructura feature-based (reusa tu skill `clean-frontend-architecture`).
- [ ] Login con JWT (rol admin / analyst).
- [ ] Vista de lista de casos con filtros y polling de fallback.
- [ ] Vista de detalle de caso con WebSocket para progreso en vivo.
- [ ] Vista de monitoreo: workers activos, throughput, casos por estado (consume métricas de Flower API + queries a DB).
- [ ] Endpoint WebSocket `/ws/cases/{id}` que reenvía eventos de Redis pub/sub.
- [ ] CSS Modules + cero hardcoded strings, según tu estilo.

**Criterio de cierre:** subir un caso desde el dashboard, ver barra de progreso avanzar en tiempo real, ver reporte final.

### Sprint 4 — Reportes, alertas, monitoreo serio (Días 16–19, 31 mayo–3 junio)

- [ ] Generación de reporte PDF con `weasyprint` (HTML → PDF, fácil de versionar el template).
- [ ] Sistema de alertas: cuando un finding tiene `severity >= 4`, emitir notificación.
- [ ] Endpoint de descarga de reporte.
- [ ] Integrar Prometheus: exportar métricas custom (tareas por segundo, latencia p50/p95, tamaño de colas).
- [ ] Dashboard Grafana con paneles preconfigurados.
- [ ] Flower expuesto en el dashboard como iframe o link.

**Criterio de cierre:** reporte descargable, alertas visibles, Grafana con datos reales.

### Sprint 5 — Pruebas de carga, seguridad y pulido (Días 20–23, 4–7 junio)

- [ ] `locust` con escenario realista (10/50/100 casos concurrentes).
- [ ] Gráficas de **throughput vs N° de workers** (escalado horizontal).
- [ ] Documentar resultados en `docs/performance.md` con tablas y conclusiones.
- [ ] Cifrado en reposo en MinIO (SSE-S3).
- [ ] HTTPS local con certificados autofirmados (`mkcert`) si da tiempo.
- [ ] Hardening: rate limiting en API (`slowapi`), validación estricta de tipos MIME en uploads.
- [ ] CI: GitHub Actions con lint (`ruff`), tests (`pytest`), build de imágenes.

**Criterio de cierre:** reporte de pruebas de carga con números reales, CI verde, seguridad básica activa.

### Sprint 6 — Documentación final y defensa (Días 24–25, 8–10 junio)

- [ ] README completo con quickstart, arquitectura, troubleshooting.
- [ ] `docs/deployment.md` con paso a paso desde clone hasta primera petición.
- [ ] Diagramas finales actualizados en draw.io.
- [ ] Reporte final del proyecto (PDF) con: resumen, arquitectura, decisiones, resultados de pruebas, casos de estudio, anexos.
- [ ] Video demo de 5 minutos (opcional pero suma).
- [ ] Ensayo de defensa: practicar explicar la arquitectura en 3 minutos.

**Criterio de cierre:** repositorio público con tag `v1.0`, todos los entregables listos.

---

## 7. Riesgos identificados y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| `faster-whisper` consume mucha RAM en laptop | Alta | Medio | Forzar modelo `tiny`, limitar `worker_audio` a 1 proceso concurrente. |
| YOLOv8 sin GPU es lento | Alta | Bajo | Usar `yolov8n` (nano), imágenes redimensionadas a 640px. |
| Scope creep (querer hacer microservicios "puros") | Alta | Alto | Congelar el stack al final del Sprint 0. No tocar arquitectura después. |
| Trabajo grupal mal coordinado | Media | Alto | Asignar dueños por servicio desde día 1 (ver sección 9). |
| Docker en Windows con WSL2 lento al montar volúmenes | Media | Medio | Mantener código en filesystem de WSL, no en `/mnt/c/`. |
| Reintentos infinitos por bug en un worker | Media | Alto | `max_retries=3` siempre, DLQ obligatoria, alertas en logs. |
| Pruebas de carga revelan bottleneck que no da tiempo arreglar | Media | Medio | Hacer una prueba "boba" al final del Sprint 2, no esperar al 5. |
| Choque con entrega de Bases de Datos II (21 mayo) | Alta | Alto | Bloquear los días 19–21 mayo para BD II, recuperar Sprint 1 los días 22–23. |

---

## 8. Choques con otras entregas

- **21 mayo**: Entrega 2 de Bases de Datos II (PostgreSQL Logical Replication). Días 19–21 mayo van a estar saturados. Plan: terminar Sprint 0 antes del 19, empezar Sprint 1 el 22.
- Revisar fechas de Software Design y Web Design para ajustar.

---

## 9. División de trabajo grupal (propuesta)

Si son 3–4 personas, dividir por servicio (no por capa, eso genera contención):

| Responsable | Servicios / Áreas |
|---|---|
| Dev 1 (tú, líder técnico) | API Gateway + shared/messaging + integración + CI/CD + dirige diseño |
| Dev 2 | Worker text + worker aggregator + reporte |
| Dev 3 | Worker audio + worker image + análisis |
| Dev 4 | Dashboard React + WebSocket + monitoreo (Grafana/Prometheus) |

Si son 3, fusionar Dev 3 y Dev 4 parcialmente, o que el dashboard lo lleves tú aprovechando que ya manejas React.

---

## 10. Checklist final antes de entregar

- [ ] `docker compose up` arranca todo el stack en una máquina limpia.
- [ ] `make seed` o equivalente crea usuario admin y caso demo.
- [ ] README permite a alguien externo correr el sistema en < 10 minutos.
- [ ] Todos los servicios tienen al menos un test unitario.
- [ ] CI verde en `main`.
- [ ] Reporte final PDF en `docs/final_report.pdf`.
- [ ] Tag `v1.0` en Git.
- [ ] Video demo grabado.
- [ ] Defensa ensayada al menos 2 veces.

---

## 11. Próximos pasos inmediatos (esta semana)

1. Confirmar tamaño del grupo y repartir roles.
2. Crear repo en GitHub, invitar al equipo.
3. Levantar `docker-compose.yml` con postgres + rabbitmq + redis + minio.
4. Escribir ADR-001 a ADR-005 (los tienes ya bosquejados en sección 2.2).
5. Bosquejar el diagrama C4 nivel 1 en draw.io.

Cuando muevas este archivo a la carpeta del proyecto, lo siguiente que conviene atacar es el `docker-compose.yml` base y el esquema Alembic. Avísame cuál de los dos quieres arrancar primero.
