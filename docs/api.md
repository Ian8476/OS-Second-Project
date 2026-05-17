# API HTTP

> Documentación interactiva auto-generada por FastAPI en `/docs` (Swagger)
> y `/redoc`. Este archivo resume los endpoints estables.

Base path: `http://localhost:8000/api/v1`

## Auth

| Método | Path | Body | Resp |
|---|---|---|---|
| POST | `/auth/login` | `{ email, password }` | `{ access_token, role }` |
| POST | `/auth/register` (admin) | `{ email, password, role }` | `{ access_token, role }` |
| GET  | `/auth/me` | — | datos del usuario |

## Casos

| Método | Path | Descripción |
|---|---|---|
| POST   | `/cases` (multipart) | Crea caso. Campos: `title`, `description?`, `priority`, `files[]`. |
| GET    | `/cases` | Lista paginada. Query: `status?`, `page`, `page_size`. |
| GET    | `/cases/{id}` | Detalle con `data_sources`, `subtasks`, `findings`. |
| POST   | `/cases/{id}/cancel` | Cancela caso en cola/procesando. Body `{ reason? }`. |

## Reportes

| Método | Path | Descripción |
|---|---|---|
| GET | `/reports/{case_id}/pdf` | Descarga directa del PDF. |
| GET | `/reports/{case_id}/presigned` | URL pre-firmada de MinIO (10 min). |

## WebSockets

- `ws://localhost:8000/ws/cases/{case_id}?token=<jwt>` — eventos de un caso.
- `ws://localhost:8000/ws/monitoring?token=<jwt>` — eventos globales.

Mensajes (JSON):

```json
{
  "type": "case.progress",
  "case_id": "...",
  "payload": { "done": 3 },
  "occurred_at": "2026-05-18T14:32:11.872Z"
}
```

Tipos: `case.queued | case.started | case.progress | case.completed |
case.failed | case.cancelled | subtask.started | subtask.completed |
subtask.failed | subtask.retrying | finding.created | report.ready |
alert.high_severity`.

## Errores comunes

| Código | `detail` | Significado |
|---|---|---|
| 401 | `invalid_token` | JWT inválido o expirado |
| 401 | `invalid_credentials` | Login incorrecto |
| 403 | `admin_required` | Endpoint requiere rol admin |
| 404 | `case_not_found` | El UUID no existe |
| 409 | `case_already_terminal` | El caso ya está en estado terminal |
| 409 | `report_not_ready` | El aggregator todavía no produjo el PDF |
| 409 | `invalid_transition` | Transición de estado no permitida |
| 413 | `file_too_large` | Archivo supera 50 MB |
| 415 | `mime_not_allowed` | Tipo MIME no soportado |
| 429 | `rate_limited` | Rate limit (200 req/min default) |
