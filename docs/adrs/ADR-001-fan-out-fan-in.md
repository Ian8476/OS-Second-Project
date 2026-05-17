# ADR-001 — Fan-out / Fan-in con contador atómico Redis

**Estado:** Aceptado
**Fecha:** 2026-05-16
**Decisores:** equipo MediaIntel

## Contexto

Un caso es una unidad lógica que puede traer N mensajes, M imágenes y K
audios. Procesarlo como una sola tarea monolítica violaría el requisito
de paralelismo y dejaría una sola línea de ejecución por caso.

Necesitamos:

1. Disparar muchas sub-tareas simultáneamente (fan-out).
2. Saber cuándo *todas* terminaron para producir el reporte (fan-in).

Alternativas evaluadas:

- **Celery `chord` / `group`**: simple en código, pero el backend de
  resultados (Redis) acumula keys y se vuelve un cuello de botella con
  N alto. Además acopla el aggregator a la API.
- **Contador atómico en Redis + lock semáforo para el aggregator**: cada
  worker hace `INCR`. El que llega al total dispara el aggregator
  protegido por `SET NX`.
- **Coordinator service dedicado**: agrega complejidad sin beneficio.

## Decisión

Implementamos fan-in con **contador atómico Redis**:
- `case:{id}:total`, `case:{id}:done`, `case:{id}:failed`.
- Cada worker exitoso hace `INCR done`.
- Cada worker fallido hace `INCR failed`.
- Un solo worker (`SET NX case:{id}:aggregator_dispatched`) envía la
  tarea de aggregator al broker.

## Consecuencias

**Positivas**
- Independiente del result backend de Celery.
- Sincronización clásica de SO (contador + lock), fácil de explicar en la
  defensa.
- Si el broker reenruta, el contador no se duplica gracias al `SET NX`
  + tabla `processed_tasks`.

**Negativas**
- Si Redis se cae después de iniciar un caso, perdemos el progreso en
  memoria. Mitigación: AOF activado + reconstruir contador desde la BD
  contando `subtasks.status = completed`.
