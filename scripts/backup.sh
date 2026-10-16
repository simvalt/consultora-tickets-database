#!/usr/bin/env sh
# Respaldo lógico en formato custom. Uso: scripts/backup.sh [archivo]
# Requiere DATABASE_URL (o ejecutarse dentro del contenedor db: ver README).
set -eu
OUT="${1:-backups/tickets_$(date -u +%Y%m%dT%H%M%SZ).dump}"
pg_dump --format=custom --no-owner --dbname="$DATABASE_URL" --file="$OUT"
echo "Respaldo creado: $OUT"
