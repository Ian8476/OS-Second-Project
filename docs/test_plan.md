# Plan de prueba — MediaIntel

Guía paso a paso para verificar que el proyecto corre end-to-end y que
cada concepto de la rúbrica está demostrado. Pensado para ejecutarse en
una máquina limpia con Docker Desktop y Windows 11 (PowerShell). Para
bash/WSL los comandos son equivalentes salvo `curl.exe` → `curl`.

> Tiempo estimado total: **20–25 minutos** la primera vez (descarga de
> imágenes + modelos), **5 minutos** las siguientes.

---

## 0. Pre-requisitos

| Requisito | Versión mínima | Verificar |
|---|---|---|
| Docker Engine | 24 | `docker --version` |
| Docker Compose | v2 | `docker compose version` |
| RAM libre para Docker | 8 GB | Docker Desktop → Settings → Resources |
| Disco libre | 5 GB | — |
| Puertos libres en host | 3000, 5173, 5555, 5672, 6379, 8000, 9000, 9001, 9090, 15672 | `Test-NetConnection localhost -Port 8000` |

Clonar / posicionarse en la raíz del repo y confirmar archivos clave:

```powershell
ls docker-compose.yml, .env.example, README.md
```

---

## 1. Arranque del stack (smoke test)

### 1.1 Variables de entorno

```powershell
Copy-Item .env.example .env
```

> No modificar nada todavía: los defaults sirven para localhost.

### 1.2 Levantar todos los contenedores

```powershell
docker compose up -d --build
```

Primera vez tarda 5–10 min (descarga de bases, instala dependencias).

### 1.3 Esperar que todo esté `healthy`

```powershell
docker compose ps
```

**Criterio de éxito:** los servicios `postgres`, `rabbitmq`, `redis`,
`minio` aparecen como `healthy`; `api`, `worker_*` y `dashboard` como
`running` (sin reinicios).

Si algún worker está en `restarting`, ver logs:

```powershell
docker compose logs --tail=50 worker_text
docker compose logs --tail=50 api
```

### 1.4 Aplicar migraciones y seed

```powershell
docker compose exec api alembic -c /app/services/shared/alembic.ini upgrade head
docker compose exec api python -m services.api.app.infrastructure.seed
```

**Criterio de éxito:** la última línea del seed dice
`seed_users_created` (o `seed_skipped_admin_exists` si ya se corrió).

### 1.5 Healthchecks de URLs

| URL | Esperado |
|---|---|
| http://localhost:8000/health | `{"status":"ok"}` |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:5173 | Login de MediaIntel |
| http://localhost:15672 | RabbitMQ login (mediaintel / mediaintel_dev) |
| http://localhost:9001 | MinIO console (mediaintel / mediaintel_dev) |
| http://localhost:5555 | Flower con 4 workers visibles |
| http://localhost:9090 | Prometheus (Status → Targets, todos UP) |
| http://localhost:3000 | Grafana (admin / admin) → dashboard "MediaIntel Overview" |

```powershell
curl.exe -s http://localhost:8000/health
```

✅ **Pasa el smoke test** si todos los endpoints anteriores responden.

---

## 2. Test funcional end-to-end (texto)

### 2.1 Login y obtener token

```powershell
$resp = curl.exe -s -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"analyst@mediaintel.local\",\"password\":\"ChangeMe123!\"}'

$token = ($resp | ConvertFrom-Json).access_token
$token
```

**Criterio:** `$token` es un string JWT no vacío.

### 2.2 Crear un caso con un archivo de texto

```powershell
"Voy a golpear y matar a esa persona, idiota." | Out-File -Encoding utf8 .\sample_text.txt

curl.exe -s -X POST http://localhost:8000/api/v1/cases `
  -H "Authorization: Bearer $token" `
  -F "title=Test texto" `
  -F "priority=high" `
  -F "files=@sample_text.txt"
```

**Criterio:** respuesta HTTP 201 con `id`, `status=queued`,
`total_subtasks=1`.

Guardar el id:

```powershell
$caseId = (curl.exe -s -X POST http://localhost:8000/api/v1/cases `
  -H "Authorization: Bearer $token" `
  -F "title=Test texto B" `
  -F "priority=high" `
  -F "files=@sample_text.txt" | ConvertFrom-Json).id
$caseId
```

### 2.3 Consultar el detalle hasta completar

```powershell
do {
  Start-Sleep -Seconds 2
  $detail = curl.exe -s "http://localhost:8000/api/v1/cases/$caseId" `
    -H "Authorization: Bearer $token" | ConvertFrom-Json
  Write-Host "status=$($detail.status) done=$($detail.completed_subtasks)/$($detail.total_subtasks)"
} while ($detail.status -in @("queued","processing"))

$detail
```

**Criterio:** termina con `status = completed`, al menos un finding con
`category = violence` o `threats`, `report_storage_key` no nulo.

### 2.4 Descargar reporte PDF

```powershell
curl.exe -s "http://localhost:8000/api/v1/reports/$caseId/pdf" `
  -H "Authorization: Bearer $token" -o "report.pdf"
```

**Criterio:** archivo `report.pdf` > 5 KB; abrirlo y verificar que
muestra titulo, severidad, hallazgos y auditoría de subtareas.

---

## 3. Test del dashboard (UI)

1. Abrir http://localhost:5173 → login con `admin@mediaintel.local` /
   `ChangeMe123!`.
2. **Casos → Nuevo caso**: subir `sample_text.txt` con prioridad `critical`.
3. En la página de detalle, verificar:
   - Barra de progreso pasa de 0% a 100%.
   - Sección "Eventos en vivo" muestra mensajes WS:
     `case.queued → subtask.started → subtask.completed →
      case.progress → report.ready → case.completed`.
   - Aparece botón "Descargar reporte" cuando termina.
   - El badge de estado cambia visualmente (`queued` → `processing` →
     `completed`).
4. **Monitoreo**: las tarjetas reflejan el conteo por estado y el
   stream global de eventos muestra el caso recién procesado.

✅ Pasa si el progreso se actualiza **sin recargar la página**
(WebSocket en vivo).

---

## 4. Test de concurrencia y prioridades (rúbrica: 15%+10%)

### 4.1 Escalar workers

```powershell
docker compose up -d --scale worker_text=3
docker compose ps worker_text
```

**Criterio:** aparecen 3 contenedores `mediaintel-worker_text-{1,2,3}`.

### 4.2 Avalancha de casos con prioridades mixtas

Crear un script `flood.ps1`:

```powershell
$ErrorActionPreference = "Stop"
$base = "http://localhost:8000/api/v1"
$login = curl.exe -s -X POST "$base/auth/login" -H "Content-Type: application/json" `
  -d '{\"email\":\"analyst@mediaintel.local\",\"password\":\"ChangeMe123!\"}' | ConvertFrom-Json
$token = $login.access_token

"Texto de baja prioridad" | Out-File -Encoding utf8 .\low.txt
"Critico: amenaza inminente, voy a matar" | Out-File -Encoding utf8 .\crit.txt

for ($i=0; $i -lt 30; $i++) {
  curl.exe -s -X POST "$base/cases" -H "Authorization: Bearer $token" `
    -F "title=low-$i" -F "priority=low" -F "files=@low.txt" | Out-Null
}

# El critico entra al final pero deberia procesarse antes
$crit = curl.exe -s -X POST "$base/cases" -H "Authorization: Bearer $token" `
  -F "title=CRITICAL-late" -F "priority=critical" -F "files=@crit.txt" | ConvertFrom-Json

$crit.id
```

```powershell
$critId = .\flood.ps1
```

### 4.3 Verificar que el `critical` adelanta

```powershell
do {
  Start-Sleep -Seconds 1
  $detail = curl.exe -s "http://localhost:8000/api/v1/cases/$critId" `
    -H "Authorization: Bearer $token" | ConvertFrom-Json
  Write-Host "critical status=$($detail.status)"
} while ($detail.status -ne "completed")
```

**Criterio:** el caso `critical` termina **antes** que los últimos
`low`. Verificarlo listando:

```powershell
curl.exe -s "http://localhost:8000/api/v1/cases?page_size=50" `
  -H "Authorization: Bearer $token" | ConvertFrom-Json `
  | Select-Object -ExpandProperty items `
  | Sort-Object finished_at `
  | Format-Table title, status, priority, finished_at
```

✅ Pasa si en la tabla ordenada por `finished_at`, el `CRITICAL-late`
aparece **antes** de los últimos `low-*`.

### 4.4 Idempotencia / lock distribuido

```powershell
docker compose exec redis redis-cli keys "subtask:*:lock"
```

**Criterio:** durante el procesamiento de la avalancha aparecen
claves de lock; al terminar, todas se borran (TTL o `DEL` post-tarea).

```powershell
docker compose exec postgres psql -U mediaintel -d mediaintel `
  -c "SELECT count(*) FROM processed_tasks;"
```

**Criterio:** el conteo coincide con el total de subtasks completadas.

---

## 5. Test de tolerancia a fallos

### 5.1 Matar un worker en pleno procesamiento

```powershell
# Disparar varios casos
for ($i=0; $i -lt 5; $i++) {
  curl.exe -s -X POST "http://localhost:8000/api/v1/cases" `
    -H "Authorization: Bearer $token" `
    -F "title=resilience-$i" -F "priority=medium" -F "files=@sample_text.txt" | Out-Null
}

# Matar un worker
docker compose kill worker_text
docker compose up -d worker_text
```

**Criterio:** ningún caso queda en `processing` indefinidamente. Tras
unos segundos:

```powershell
curl.exe -s "http://localhost:8000/api/v1/cases?status=processing" `
  -H "Authorization: Bearer $token" | ConvertFrom-Json `
  | Select-Object -ExpandProperty total
# -> 0 (o decreciente)
```

Esto demuestra `task_acks_late=True` + redelivery de RabbitMQ.

### 5.2 Dead Letter Queue

Forzar un fallo permanente (cambiar `WHISPER_MODEL_SIZE=does-not-exist`
y reiniciar `worker_audio`, subir audio). Tras 3 reintentos el mensaje
va a `queue.audio.dlq`:

1. http://localhost:15672 → Queues → `queue.audio.dlq`.
2. **Criterio:** `Ready ≥ 1` después de los 3 reintentos.

Restaurar `.env` al valor original cuando termine.

---

## 6. Test de cancelación

```powershell
$big = curl.exe -s -X POST "http://localhost:8000/api/v1/cases" `
  -H "Authorization: Bearer $token" `
  -F "title=Cancel me" -F "priority=low" `
  -F "files=@sample_text.txt" -F "files=@sample_text.txt" -F "files=@sample_text.txt" `
  | ConvertFrom-Json

curl.exe -s -X POST "http://localhost:8000/api/v1/cases/$($big.id)/cancel" `
  -H "Authorization: Bearer $token" -H "Content-Type: application/json" `
  -d '{\"reason\":\"prueba\"}' | ConvertFrom-Json
```

**Criterio:** respuesta con `status = cancelled` y todas las
`subtasks[].status` cancelladas o ya completadas. Validar auditoria:

```powershell
docker compose exec postgres psql -U mediaintel -d mediaintel `
  -c "SELECT from_status, to_status, reason FROM case_state_history WHERE case_id = '$($big.id)' ORDER BY changed_at;"
```

---

## 7. Tests unitarios automáticos

```powershell
docker compose run --rm api pytest services/api/tests -q
docker compose run --rm worker_text pytest services/worker_text/tests -q
docker compose run --rm worker_image pytest services/worker_image/tests -q
docker compose run --rm worker_aggregator pytest services/worker_aggregator/tests -q
docker compose run --rm worker_audio pytest services/worker_audio/tests -q
```

**Criterio:** todas las suites en verde (`X passed in Ys`).

Frontend:

```powershell
cd dashboard
npm install
npm test
cd ..
```

---

## 8. Test de carga (Locust)

En otra terminal:

```powershell
docker run --rm -p 8089:8089 -v ${PWD}/loadtests:/mnt/locust `
  locustio/locust -f /mnt/locust/locustfile.py `
  --host http://host.docker.internal:8000
```

1. Abrir http://localhost:8089.
2. **Escenarios sugeridos** (anotar resultados para `docs/performance.md`):

| Usuarios | Spawn rate | Duración | Métrica a capturar |
|---|---|---|---|
| 10  | 2/s | 2 min | latencia p50 y p95, RPS |
| 50  | 5/s | 3 min | mismas + tasa de error |
| 100 | 10/s | 3 min | mismas + tamaño cola RabbitMQ |

3. Repetir con `--scale worker_text=4` y `--scale worker_text=1` para
   sacar la **gráfica throughput vs workers**.

**Criterio:** la tasa de error a 50 usuarios concurrentes < 2%.

---

## 9. Test de monitoreo

| Vista | Qué verificar |
|---|---|
| Flower → Workers | 4 workers (text/audio/image/aggregator) en estado `Online`. |
| Flower → Tasks | Tareas recientes con tiempos por tipo. |
| RabbitMQ → Queues | `queue.text/audio/image/aggregate` con métricas; DLQ con 0 (estado normal). |
| Prometheus → Status → Targets | Todos los jobs `UP`. |
| Grafana → MediaIntel Overview | 4 paneles con datos reales tras varios casos. |
| API → `/metrics` | Texto Prometheus con `http_requests_total`. |

---

## 10. Cleanup

```powershell
docker compose down       # mantiene volumenes (datos persisten)
# o
docker compose down -v    # borra todos los datos
```

---

## Resumen de criterios de aceptación

Si todos los pasos anteriores pasan, el proyecto cumple los entregables
mapeados en `PLANNING.md §1`:

- [x] **Arquitectura Distribuida** (paso 1) — >= 6 servicios separados.
- [x] **Concurrencia** (paso 4.1, 4.2) — escalado horizontal demostrado.
- [x] **Gestión de cargas** (paso 6) — estados auditados + cancelación.
- [x] **Procesamiento multimedia** (paso 2 + dashboard) — texto/audio/imagen.
- [x] **Dashboard + monitoreo** (paso 3 + paso 9).
- [x] **Reportes** (paso 2.4) — PDF descargable.
- [x] **Escalabilidad** (paso 8) — números reales de Locust.
- [x] **Seguridad** (paso 2.1) — JWT.
- [x] **Documentación** — `docs/` con ADRs, architecture, deployment.
- [x] **Repo / buenas prácticas** — monorepo + CI verde.
