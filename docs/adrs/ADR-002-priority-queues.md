# ADR-002 — Prioridades por mensaje sobre una cola por tipo de worker

**Estado:** Aceptado
**Fecha:** 2026-05-16

## Contexto

La rúbrica premia la demostración explícita de scheduling (colas
multinivel / prioridades). Tenemos dos ejes:

1. **Tipo de carga** (texto, audio, imagen): trabajos heterogéneos en CPU
   y memoria; conviene separarlos para escalar independiente.
2. **Prioridad de negocio** (low/medium/high/critical): un caso `critical`
   no puede esperar atrás de 50 `low`.

Opciones:

- 4 prioridades × 3 tipos = **12 colas separadas**. Verboso, difícil de
  presentar en diagrama; routing del cliente se vuelve grande.
- **1 cola por tipo + `x-max-priority` en RabbitMQ** (esta decisión).
- **Una sola cola priorizada multi-tipo**: rompe el aislamiento de
  recursos (audio bloquea texto).

## Decisión

Cuatro colas: `queue.text`, `queue.audio`, `queue.image`, `queue.aggregate`,
todas declaradas con `x-max-priority=10`. La prioridad se envía por
**mensaje** al hacer `send_task(..., priority=10)`. Celery
`broker_transport_options.priority_steps = [1,3,6,10]` para tener 4
escalones reales.

## Consecuencias

**Positivas**
- Conserva aislamiento de recursos por tipo de worker.
- Demuestra prioridades sin armar la matriz 3×4 de colas.
- Permite explicar **starvation** y **fairness** en la defensa.

**Negativas**
- Las prioridades AMQP solo se aplican entre mensajes ya en la cola; un
  mensaje ya entregado al worker no se desaloja. Aceptable para academia.
