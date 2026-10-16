# consultora-tickets-database

Única fuente de verdad del esquema de PostgreSQL del sistema de tickets. El backend **no** crea tablas ni mantiene migraciones propias.

Repos hermanos (carpeta común, p. ej. `E:\TicketsApp\`):

```
consultora-tickets-database/   ← este repo
consultora-tickets-backend/    ← contiene el docker-compose que levanta todo
consultora-tickets-frontend/
```

**Guía para levantar la solución completa: ver el README de `consultora-tickets-backend`.**

## Herramienta: Alembic

SQL explícito (sin modelos ORM) en `alembic/versions/`. Versiones fijadas en `requirements.txt` (Alembic 1.14, SQLAlchemy 2.0, psycopg 3). Postgres 16.4.

## Uso local (Docker)

```bash
cp .env.example .env                       # editar si hace falta
docker compose up -d db                    # PostgreSQL en 127.0.0.1:5432
docker compose --profile tools run --rm --build migrate                                  # alembic upgrade head
docker compose --profile tools run --rm migrate python seed/seed.py base                  # categorías, rol y usuario Administrador
docker compose --profile tools run --rm migrate python seed/seed.py demo                  # datos demo (solo local)
```

Otros comandos de migración (sustituir el comando final): `alembic current`, `alembic history`, `alembic downgrade -1`, `alembic revision -m "descripcion"` (crea una migración nueva).

Sin Docker: `pip install -r requirements.txt`, exportar `DATABASE_URL` y ejecutar `alembic upgrade head` / `python seed/seed.py base`.

## Seeds

| Comando | Contenido | Entorno |
|---|---|---|
| `seed.py base` | 6 categorías, rol *Administrador* (nivel 4 en todo) y usuario inicial `ADMIN_EMAIL` / `ADMIN_PASSWORD` (mín. 12 caracteres). Idempotente. | Cualquiera, incluido producción |
| `seed.py demo` | Roles Supervisor, Agente, Capturista, Consulta; 6 usuarios + 1 inactivo; 8 clientes; ~76 tickets en todos los estatus (vencidos, sin responsable, reabiertos) repartidos en 60 días, con comentarios e historial. | **Solo local**: se niega con `APP_ENV=production`; nunca se ejecuta automáticamente |

Credenciales locales (`.env.example`): admin `admin@consultora.local` / `Admin#Local1234`; usuarios demo `supervisor@`, `agente1@`, `agente2@`, `agente3@`, `capturista@`, `consulta@consultora.local` con `Demo#Local1234`; `inactivo@consultora.local` está desactivado. **Son credenciales de desarrollo; en producción define las tuyas y no ejecutes el seed demo.**

## Respaldo y restauración

```bash
# Respaldo (formato custom)
docker compose exec -T db pg_dump -U tickets --format=custom --no-owner tickets > backups/tickets.dump
# Restauración (limpia objetos existentes antes)
docker compose exec -T db pg_restore -U tickets --clean --if-exists --no-owner -d tickets < backups/tickets.dump
```

Con `psql/pg_dump` instalados y `DATABASE_URL` definida también sirven `scripts/backup.sh` y `scripts/restore.sh`. Los respaldos (`backups/`) no se versionan. Probado: dump → restore conserva los datos.

## Despliegue

1. Construir la imagen (`docker build -t tickets-migrate .`) y ejecutarla como paso previo al backend, con `DATABASE_URL` apuntando a la BD gestionada: `docker run --rm -e DATABASE_URL=... tickets-migrate` (ejecuta `alembic upgrade head`).
2. Una sola vez: `docker run --rm -e DATABASE_URL=... -e ADMIN_EMAIL=... -e ADMIN_PASSWORD=... tickets-migrate python seed/seed.py base`.
3. No ejecutar `seed.py demo`. Orden: base de datos → migraciones → backend → frontend.

## Modelo de datos

Ver [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

## Limitaciones

Las migraciones `downgrade` borran datos (solo para desarrollo). No hay particionado ni réplicas.
