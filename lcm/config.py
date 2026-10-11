"""Rutas del repositorio, claves de API y convenciones de archivos crudos."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"
CRUDOS = DATOS / "raw"
BASE = DATOS / "latam_crossref.duckdb"

load_dotenv(RAIZ / ".env")


def clave(nombre: str, obligatoria: bool = True) -> str | None:
    """Devuelve una variable del archivo .env.

    Si es obligatoria y falta, explica cómo configurarla en vez de fallar en silencio.
    """
    valor = os.getenv(nombre) or None
    if obligatoria and not valor:
        raise RuntimeError(
            f"Falta {nombre} en .env. Copia .env.example como .env y completa el valor."
        )
    return valor


def ruta_crudo(fuente: str, nombre: str, extension: str = "json", fecha: date | None = None) -> Path:
    """Ruta fechada para una descarga cruda: data/raw/<fuente>/<AAAA-MM-DD>_<nombre>.<ext>.

    Crea la carpeta de la fuente si no existe.
    """
    fecha = fecha or date.today()
    carpeta = CRUDOS / fuente
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta / f"{fecha.isoformat()}_{nombre}.{extension.lstrip('.')}"
