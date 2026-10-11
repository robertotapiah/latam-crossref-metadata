"""Línea base del resto del mundo (2025) con los mismos criterios que el estudio (paper, sección 2.2).

Miembros de Crossref con 100 o más artículos acumulados, sin los países latinoamericanos asignados y sin las
cuentas de SciELO. Conteos completos por bloques de 100 miembros (varios `member:ID` en un filtro suman miembros).
Salida: data/raw/crossref/<fecha>_linea_base_mundial_2025.json (miembros, artículos y conteo de cada metadato).
Uso: uv run python scripts/06_linea_base_mundial.py   (~15 minutos)
"""

import json

from lcm.config import ruta_crudo
from lcm.crossref import CAMPOS, contar
from lcm.db import conectar

FECHAS = "type:journal-article,from-pub-date:2025-01-01,until-pub-date:2025-12-31"

con = conectar(solo_lectura=True)
ids = [r[0] for r in con.execute(
    """SELECT id FROM crossref.miembros
       WHERE articulos >= 100 AND pais_latam IS NULL AND lower(nombre) NOT LIKE '%scielo%' ORDER BY id"""
).fetchall()]
con.close()
print(f"{len(ids)} miembros del resto del mundo con >=100 artículos", flush=True)

bloques = [ids[i:i + 100] for i in range(0, len(ids), 100)]
acum = {"total": 0, **{c: 0 for c in CAMPOS}}
for k, bl in enumerate(bloques, 1):
    base = ",".join(f"member:{i}" for i in bl) + "," + FECHAS
    t = contar(base)
    acum["total"] += t
    if t:
        for campo, filtro in CAMPOS.items():
            acum[campo] += contar(base + "," + filtro)
    if k % 10 == 0 or k == len(bloques):
        print(f"[{k}/{len(bloques)}] artículos acumulados: {acum['total']:,}", flush=True)

destino = ruta_crudo("crossref", "linea_base_mundial_2025", "json")
destino.write_text(json.dumps({"miembros": len(ids), "bloques": len(bloques), **acum}), encoding="utf-8")
print("LISTO", acum, "->", destino, flush=True)
