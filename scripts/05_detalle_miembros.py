"""Completitud por miembro y año (2020-2025) para un país: detalle por organización editora (paper, sección 3.5).

Un país por ejecución (por defecto CL). Solo miembros válidos (>=100 artículos acumulados).
Reanudable: cada miembro-año se agrega al JSONL crudo del día apenas termina. Al final carga a
crossref.completitud_miembros (reemplaza solo las filas del país ejecutado).
El detalle por organización queda en la base local y no se publica: el paper solo usa cifras agregadas.
Uso: uv run python scripts/05_detalle_miembros.py [PAIS]
"""

import json
import sys

import pandas as pd

from lcm.config import ruta_crudo
from lcm.crossref import completitud
from lcm.db import asegurar_esquema, conectar

PAIS = sys.argv[1] if len(sys.argv) > 1 else "CL"
ANIOS = range(2020, 2026)

# Reanuda solo el crudo de hoy; si no existe, crea uno nuevo (cada extracción lleva su fecha real).
archivo = ruta_crudo("crossref", f"detalle_miembros_{PAIS}", "jsonl")
hechos = set()
if archivo.exists():
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        r = json.loads(linea)
        hechos.add((r["miembro_id"], r["anio"]))
print(f"Archivo: {archivo.name} ({len(hechos)} miembro-años ya hechos)", flush=True)

con = conectar(solo_lectura=True)
miembros = con.execute(
    "SELECT id, nombre FROM crossref.miembros WHERE pais_latam = ? AND articulos >= 100 ORDER BY id",
    [PAIS],
).fetchall()
con.close()

total = len(miembros) * len(ANIOS)
n = 0
with archivo.open("a", encoding="utf-8") as f:
    for mid, nombre in miembros:
        for anio in ANIOS:
            n += 1
            if (mid, anio) in hechos:
                continue
            res = completitud(mid, anio)
            reg = {"miembro_id": mid, "nombre": nombre, "pais": PAIS, "anio": anio, **res}
            f.write(json.dumps(reg) + "\n")
            f.flush()
            print(f"[{n}/{total}] {nombre} {anio}: {res['total']} artículos", flush=True)

df = pd.DataFrame([json.loads(l) for l in archivo.read_text(encoding="utf-8").splitlines()])
con = conectar()
asegurar_esquema(con, "crossref")
con.execute("CREATE TABLE IF NOT EXISTS crossref.completitud_miembros AS SELECT * FROM df WHERE false")
con.execute("DELETE FROM crossref.completitud_miembros WHERE pais = ?", [PAIS])
con.execute("INSERT INTO crossref.completitud_miembros SELECT * FROM df")
con.close()
print(f"LISTO: {len(df)} filas de {PAIS} en crossref.completitud_miembros", flush=True)
