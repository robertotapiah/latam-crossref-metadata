"""Descarga todos los miembros de Crossref y los guarda como crudo fechado.

Se descargan todos (y no solo los de LATAM) porque Crossref no filtra por país: el país se
asigna después, localmente, desde el texto `location` (ver lcm/crossref.py).
Uso: uv run python scripts/01_miembros.py
"""

import json

from lcm.config import ruta_crudo
from lcm.crossref import miembros

items = miembros(todo=True)
destino = ruta_crudo("crossref", "miembros")
destino.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
print(f"{len(items)} miembros guardados en {destino}")
