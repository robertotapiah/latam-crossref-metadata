"""Carga los miembros crudos más recientes a DuckDB (crossref.miembros) con el país asignado.

Supuesto de limpieza: el país sale del último tramo de `location`; si no es un país de LATAM
reconocido queda en NULL (pais_latam). `location_cruda` se conserva para auditar.
Uso: uv run python scripts/02_carga_miembros.py
"""

import json

import pandas as pd

from lcm.config import CRUDOS
from lcm.crossref import pais_de
from lcm.db import asegurar_esquema, conectar

archivo = sorted((CRUDOS / "crossref").glob("*_miembros.json"))[-1]
items = json.loads(archivo.read_text(encoding="utf-8"))

filas = []
for m in items:
    todos = (m.get("counts-type") or {}).get("all") or {}
    filas.append(
        {
            "id": m["id"],
            "nombre": m.get("primary-name"),
            "location_cruda": m.get("location"),
            "pais_latam": pais_de(m.get("location")),
            "dois_total": (m.get("counts") or {}).get("total-dois", 0),
            "articulos": todos.get("journal-article", 0),
            "dois_por_anio": json.dumps((m.get("breakdowns") or {}).get("dois-by-issued-year", [])),
            "fuente_archivo": archivo.name,
        }
    )
df = pd.DataFrame(filas)

con = conectar()
asegurar_esquema(con, "crossref")
con.execute("CREATE OR REPLACE TABLE crossref.miembros AS SELECT * FROM df")
print(f"{len(df)} miembros cargados desde {archivo.name}; {df.pais_latam.notna().sum()} de LATAM")
con.close()
