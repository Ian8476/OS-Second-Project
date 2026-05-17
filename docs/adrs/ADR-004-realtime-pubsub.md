# ADR-004 — Realtime: Redis pub/sub → WebSocket

**Estado:** Aceptado
**Fecha:** 2026-05-16

## Contexto

El dashboard necesita ver progreso en vivo, no por polling cada 5s.
Hay tres formas de implementarlo:

- **WebSocket directo entre workers y frontend**: rompería el aislamiento
  de capas y requiere acceso de red de workers a clientes.
- **Server-Sent Events desde la API**: simple, pero unidireccional;
  algunos navegadores no lo soportan bien.
- **Redis pub/sub + WebSocket en FastAPI**: workers publican en
  `case:{id}:events`; FastAPI se suscribe y reenvía por WS al cliente.

## Decisión

Redis pub/sub como bus de eventos interno, expuesto al frontend mediante
un endpoint WebSocket que filtra por `case_id` (o suscripción global para
la vista de monitoreo).

Tipos de evento definidos en `services/shared/events/bus.py`:
`case.queued/started/progress/completed/failed/cancelled`,
`subtask.started/completed/failed/retrying`, `finding.created`,
`report.ready`, `alert.high_severity`.

## Consecuencias

**Positivas**
- Cero acoplamiento workers ↔ frontend.
- Múltiples consumidores del mismo evento (UI + monitoreo + alertas).
- Fácil de mockear en tests.

**Negativas**
- Pub/sub no garantiza entrega: si el cliente está desconectado al
  publicar, lo pierde. El dashboard combina WS con polling cada 5s para
  cubrir el gap.
