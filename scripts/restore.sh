#!/usr/bin/env sh
# Restaura un respaldo sobre la base indicada (la limpia antes). Uso: scripts/restore.sh archivo.dump
set -eu
[ $# -eq 1 ] || { echo "Uso: $0 archivo.dump"; exit 1; }
pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$1"
echo "Restauración completada desde $1"
