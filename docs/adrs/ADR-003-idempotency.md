# ADR-003 — Idempotencia obligatoria en workers

**Estado:** Aceptado
**Fecha:** 2026-05-16

## Contexto

Celery con `task_acks_late=True` + RabbitMQ con redelivery garantiza
*at-least-once*. Si un worker se cae después de procesar pero antes de
ACK, el mensaje vuelve a la cola y otro worker lo procesa. Si no somos
cuidadosos, generamos findings duplicados y los contadores se rompen.

## Decisión

Cada worker, antes de hacer trabajo costoso:

1. Toma `SET NX subtask:{id}:lock` (lock distribuido, TTL 300s).
2. Verifica que `processed_tasks.task_id` no exista; si existe, sale
   con `skipped_idempotent` sin tocar nada.
3. Al terminar exitosamente, inserta `processed_tasks` con PK = `task_id`
   (constraint de la tabla garantiza atomicidad).

`task_id` viene del header Celery (`self.request.id`), único por intento
de delivery del broker.

## Consecuencias

**Positivas**
- Semántica efectiva *exactly-once* (a nivel de findings persistidos).
- Soporta redelivery sin código defensivo en cada worker.
- Las pruebas pueden invocar dos veces la misma tarea y verificar que el
  segundo intento retorna `skipped_idempotent`.

**Negativas**
- Tabla `processed_tasks` crece sin parar; agregar TTL via cron mensual
  (`DELETE WHERE created_at < now() - interval '90 days'`).
