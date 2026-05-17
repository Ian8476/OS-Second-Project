# Diagrama de secuencia — Procesamiento de un caso

```
Analyst        FastAPI        MinIO       Postgres      RabbitMQ        Worker(X)       Redis        Aggregator
   │              │              │             │              │              │             │              │
   │  POST /cases (multipart)    │             │              │              │             │              │
   ├─────────────►│              │             │              │              │             │              │
   │              │  put_object  │             │              │              │             │              │
   │              ├─────────────►│             │              │              │             │              │
   │              │   INSERT case + data_sources + subtasks   │              │             │              │
   │              ├──────────────────────────►│              │              │             │              │
   │              │   SET total/done/failed in Redis           │             │              │              │
   │              ├──────────────────────────────────────────────────────────────────────►│              │
   │              │              │             │     publish task (per subtask, priority)  │             │              │
   │              ├────────────────────────────────────────►│              │             │              │
   │  201 Created │              │             │              │              │             │              │
   │◄─────────────┤              │             │              │              │             │              │
   │              │              │             │              │  deliver task to worker  │             │              │
   │              │              │             │              ├────────────►│             │              │
   │              │              │             │              │              │ SET NX lock │              │
   │              │              │             │              │              ├────────────►│              │
   │              │              │ download file               │              │             │              │
   │              │              │◄────────────┼──────────────┤              │             │              │
   │              │              │             │              │              │             │              │
   │              │              │     UPDATE subtask processing             │             │              │
   │              │              │             │◄─────────────┤              │             │              │
   │              │              │             │              │   PUBLISH event   │        │              │
   │              │              │             │              │              ├────────────►│              │
   │              │              │             │              │              │  INCR done  │              │
   │              │              │             │              │              ├────────────►│              │
   │              │              │             │              │   write findings           │             │              │
   │              │              │             │◄─────────────────────────────┤             │              │
   │              │              │             │              │   ACK message              │              │
   │              │              │             │              │◄─────────────┤             │              │
   │   ... (repetido por cada subtask)                                                     │              │
   │              │              │             │              │   if done == total: SET NX aggregator      │              │
   │              │              │             │              │              ├────────────►│              │
   │              │              │             │              │   publish aggregator task                  │              │
   │              │              │             │              │              ├──────────────────────────►│
   │              │              │             │              │              │             │   render PDF │
   │              │              │             │              │              │             │              │
   │              │              │  put_object report.pdf     │              │             │              │
   │              │              │◄───────────────────────────────────────────────────────────────────────┤
   │              │              │             │ UPDATE case completed       │             │              │
   │              │              │             │◄───────────────────────────────────────────────────────────┤
   │              │              │             │              │   publish case.completed                   │
   │              │              │             │              │              │             │◄─────────────┤
   │   subscribe WS /ws/cases/{id}             │              │              │             │              │
   ├────────────►│              │             │              │              │             │              │
   │   case.completed event                                                  │              │             │
   │◄────────────────────────────────────────────────────────────────────────┘              │             │
```

(Diagrama editable disponible en `docs/diagrams/sequence.drawio` — TBD.)
