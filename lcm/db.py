"""Acceso a la base DuckDB local (un esquema por fuente: crossref, openalex)."""

from __future__ import annotations

import duckdb

from lcm.config import BASE


def conectar(solo_lectura: bool = False) -> duckdb.DuckDBPyConnection:
    """Abre la base local (la crea si no existe)."""
    BASE.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(BASE), read_only=solo_lectura)


def asegurar_esquema(con: duckdb.DuckDBPyConnection, esquema: str) -> None:
    """Crea el esquema de una fuente si no existe."""
    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{esquema}"')
