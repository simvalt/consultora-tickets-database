# Imagen de migraciones y seeds (se usa como job "migrate" en docker compose / despliegue).
FROM python:3.12.15-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY alembic ./alembic
COPY seed ./seed
COPY scripts ./scripts
RUN useradd -r -u 10001 migrator && chown -R migrator /app
USER migrator
# Por defecto aplica las migraciones y termina.
CMD ["alembic", "upgrade", "head"]
