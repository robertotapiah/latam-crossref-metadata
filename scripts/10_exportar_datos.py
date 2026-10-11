"""Exporta a data/ las cifras agregadas que acompañan al paper (CSV, sin nombres de organizaciones ni de personas).

- completitud_pais_anio.csv: artículos de revista 2020–2025 por país y año, y cuántos tienen cada metadato
  (organizaciones editoras con 100 o más artículos, sin cuentas de SciELO).
- paises.csv: los 20 países de América Latina con miembros en Crossref y si alcanzan el criterio de inclusión.
- linea_base_mundial_2025.csv: el resto del mundo en 2025 con los mismos criterios (organizaciones, artículos y
  cuántos tienen cada metadato).
- sensibilidad_organizacion_mayor.csv: por país, peso de la organización editora de mayor volumen en 2025 y
  afiliación y bibliografía con y sin ella (sin identificar a la organización).
- muestra_2025.csv: la muestra de 1.500 artículos de 2025 con sus marcas en Crossref y OpenAlex.

El detalle por organización (script 05) y las cifras propias de cada cuenta de SciELO no se exportan.
Uso: uv run python scripts/10_exportar_datos.py
"""

import csv
import json

from lcm.config import CRUDOS, DATOS
from lcm.db import conectar

CAMPOS = ["resumen", "licencia", "orcid", "referencias", "afiliacion", "ror", "financiamiento"]

con = conectar(solo_lectura=True)
DATOS.mkdir(parents=True, exist_ok=True)


def exportar(consulta: str, nombre: str) -> None:
    destino = (DATOS / nombre).as_posix()
    con.execute(f"COPY ({consulta}) TO '{destino}' (HEADER, DELIMITER ',')")
    print(f"{nombre}: {con.execute(f'SELECT count(*) FROM ({consulta})').fetchone()[0]} filas")


def crudo_reciente(patron: str) -> dict:
    return json.loads(sorted((CRUDOS / "crossref").glob(patron))[-1].read_text(encoding="utf-8"))


sumas = ", ".join(f"sum({c})::BIGINT AS {c}" for c in CAMPOS)
exportar(
    f"""SELECT pais, anio, sum(n_miembros)::INT AS organizaciones, sum(total)::BIGINT AS articulos, {sumas}
        FROM crossref.completitud_bloques WHERE grupo = 'miembros'
        GROUP BY pais, anio ORDER BY pais, anio""",
    "completitud_pais_anio.csv",
)
exportar(
    """SELECT pais, miembros_validos AS organizaciones_100_o_mas, articulos, incluido
       FROM crossref.paises_incluidos ORDER BY incluido DESC, articulos DESC""",
    "paises.csv",
)
exportar(
    """SELECT pais, doi, n_autores_cr, afil_crossref, en_openalex, n_autores_oa, inst_oa, todos_inst_oa,
              pais_oa, texto_afil_oa
       FROM openalex.afiliacion_recuperada ORDER BY pais, doi""",
    "muestra_2025.csv",
)
con.close()

mundo = crudo_reciente("*_linea_base_mundial_2025.json")
with (DATOS / "linea_base_mundial_2025.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["organizaciones", "articulos", *CAMPOS])
    w.writerow([mundo["miembros"], mundo["total"], *(mundo[c] for c in CAMPOS)])
print("linea_base_mundial_2025.csv: 1 fila")

sens = crudo_reciente("*_sensibilidad_organizacion_mayor.json")
columnas = ["peso_pct", "afiliacion_con_pct", "afiliacion_sin_pct", "bibliografia_con_pct", "bibliografia_sin_pct"]
with (DATOS / "sensibilidad_organizacion_mayor.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["pais", *columnas])  # sin nombre ni número de miembro de la organización
    for p in sorted(sens):
        w.writerow([p, *(round(sens[p][c], 2) for c in columnas)])
print(f"sensibilidad_organizacion_mayor.csv: {len(sens)} filas")
