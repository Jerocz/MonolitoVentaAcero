#!/bin/sh
# Database per Service: cada microservicio tiene su propia base de datos y su
# propio usuario; ninguno puede leer las tablas de otro.
set -e

crear() {
  base="$1"; usuario="$2"; clave="$3"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE USER ${usuario} WITH PASSWORD '${clave}';
CREATE DATABASE ${base} OWNER ${usuario};
REVOKE ALL ON DATABASE ${base} FROM PUBLIC;
SQL
}

crear catalogo    catalogo    "$CATALOGO_DB_PASSWORD"
crear pagos       pagos       "$PAGOS_DB_PASSWORD"
crear fabricacion fabricacion "$FABRICACION_DB_PASSWORD"
