# Deployment

## Requisitos

- Docker Engine ≥ 24 y Docker Compose v2.
- 8 GB RAM disponibles para Docker (los workers de audio/imagen son hambrientos).
- ~5 GB de disco para imágenes + volúmenes.
- (Opcional) Make o pwsh para los scripts.

## Pasos

```bash
# 1) Clonar e ingresar al repo
git clone <url> mediaintel && cd mediaintel

# 2) Variables de entorno
cp .env.example .env
# editar JWT_SECRET y passwords si se publica fuera de localhost.

# 3) Construir e iniciar
docker compose up -d --build

# 4) Esperar a que rabbitmq, postgres y minio estén healthy
docker compose ps

# 5) Migraciones (el API las corre al arrancar; redundante pero seguro)
docker compose exec api alembic -c /app/services/shared/alembic.ini upgrade head

# 6) Crear usuarios demo
docker compose exec api python -m services.api.app.infrastructure.seed

# 7) Smoke test
curl http://localhost:8000/health
# -> {"status":"ok"}
```

## Escalar workers

```bash
docker compose up -d --scale worker_text=4 --scale worker_image=2
```

> Importante: si se sube `worker_audio` arriba de 1 sin GPU, el modelo
> Whisper compite por CPU y los tiempos se degradan. Mejor agregar más
> contenedores, no más concurrency interna.

## Apagar y limpiar

```bash
docker compose down            # mantiene volúmenes (DB, MinIO, etc.)
docker compose down -v          # destruye todo
```

## Producción (siguiente paso, no requerido para entrega)

- Cambiar SQLite-style passwords a secrets reales (Docker secrets / Vault).
- Poner Nginx como reverse proxy de API + dashboard con TLS.
- Activar `MINIO_KMS_AUTO_ENCRYPTION=on` y cifrado SSE-S3 ya queda
  habilitado por `minio-init` (ver `docker-compose.yml`).
- Sustituir Redis solo + Postgres solo por instancias HA gestionadas.
- Configurar Prometheus alerting + Alertmanager.

## Troubleshooting rápido

| Síntoma | Probable causa | Solución |
|---|---|---|
| `api` reiniciando | DB no aplicó migraciones | Ver logs: `docker compose logs api`. Reaplicar `alembic upgrade head`. |
| `worker_audio` muere por OOM | Whisper modelo grande | Ajustar `WHISPER_MODEL_SIZE=tiny` en `.env`. |
| Casos quedan en `processing` | Algún worker se cayó | Revisar DLQ en RabbitMQ UI; reencolar manualmente. |
| WebSocket no conecta | JWT expirado | Re-login en el dashboard. |
| `minio-init` falla | Bucket existe con SSE distinto | Borrar volumen `minio-data` y volver a subir. |
