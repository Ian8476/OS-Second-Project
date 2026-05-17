-- Inicializacion de Postgres: extensiones requeridas por la app.
-- El schema en si lo crea Alembic (migracion 0001_initial).
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
