#!/usr/bin/env sh
# Backup completo do esquema do ServiceConnect com pg_dump (além dos backups diários do Render).
# Uso: DATABASE_URL=postgres://... ./scripts_backup.sh
set -eu
SCHEMA="${DB_SCHEMA:-serviceconnect}"
mkdir -p backups
FILE="backups/serviceconnect-$(date +%Y%m%d-%H%M%S).sql.gz"
pg_dump "$DATABASE_URL" --schema="$SCHEMA" --no-owner --no-privileges | gzip > "$FILE"
echo "Backup criado: $FILE"
