"""Completitud de metadatos por país y año (2020-2025): conteos completos, sin muestreo, y reanudable.

Para cada país incluido (crossref.paises_incluidos) suma miembros válidos (>=100 artículos) en
bloques de 100 y cuenta cuántos artículos tienen cada campo. Los miembros con "SciELO" en el
nombre son cuentas de SciELO y se cuentan aparte (grupo 'cuenta_scielo'), porque registran artículos
de revistas de muchas instituciones y distorsionan las cifras del país (paper, secciones 2.1 y 3.4).

Reanudable: cada bloque se agrega al JSONL crudo del día apenas termina; al relanzar el mismo día se
saltan los hechos. Al final carga todo a crossref.completitud_bloques.
Uso: uv run python scripts/04_completitud_paises.py
"""

import json
import sys

import pandas as pd

from lcm.config import ruta_crudo
from lcm.crossref import completitud
from lcm.db import conectar

ANIOS = range(2020, 2026)
BLOQUE = 100

# Reanuda solo el crudo de hoy; si no existe, crea uno nuevo (así cada extracción lleva su fecha real).
archivo = ruta_crudo("crossref", "completitud_bloques", "jsonl")
hechos = set()
if archivo.exists():
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        r = json.loads(linea)
        hechos.add((r["pais"], r["anio"], r["grupo"], r["bloque"]))
print(f"Archivo: {archivo.name} ({len(hechos)} bloques ya hechos)", flush=True)

con = conectar(solo_lectura=True)
filas = con.execute(
    """
    SELECT m.pais_latam, m.id, lower(m.nombre) LIKE '%scielo%' AS es_scielo
    FROM crossref.miembros m JOIN crossref.paises_incluidos p ON p.pais = m.pais_latam
    WHERE p.incluido AND m.articulos >= 100
    ORDER BY m.pais_latam, m.id
    """
).fetchall()
con.close()

tareas = []  # (pais, grupo, bloque, [ids])
for pais in sorted({f[0] for f in filas}):
    for grupo, scielo in (("miembros", False), ("cuenta_scielo", True)):
        ids = [f[1] for f in filas if f[0] == pais and f[2] == scielo]
        for b in range(0, len(ids), BLOQUE):
            tareas.append((pais, grupo, b // BLOQUE, ids[b : b + BLOQUE]))
total = len(tareas) * len(ANIOS)
print(f"{len(tareas)} bloques x {len(ANIOS)} años = {total} consultas de bloque", flush=True)

hecho_n = 0
with archivo.open("a", encoding="utf-8") as f:
    for pais, grupo, bloque, ids in tareas:
        for anio in ANIOS:
            hecho_n += 1
            if (pais, anio, grupo, bloque) in hechos:
                continue
            res = completitud(ids, anio)
            reg = {"pais": pais, "anio": anio, "grupo": grupo, "bloque": bloque, "n_miembros": len(ids), **res}
            f.write(json.dumps(reg) + "\n")
            f.flush()
            print(f"[{hecho_n}/{total}] {pais} {anio} {grupo} bloque {bloque}: {res['total']} artículos", flush=True)

df = pd.DataFrame([json.loads(l) for l in archivo.read_text(encoding="utf-8").splitlines()])
con = conectar()
con.execute("CREATE OR REPLACE TABLE crossref.completitud_bloques AS SELECT * FROM df")
con.close()
print(f"LISTO: {len(df)} filas cargadas a crossref.completitud_bloques", flush=True)
sys.exit(0)
