"""Sensibilidad por país: ¿cuánto cambian las cifras de 2025 si se excluye la organización editora de mayor volumen?
(paper, sección 3.4, Tabla 4)

Para cada país incluido, entre los candidatos (3 mayores por total acumulado y 3 mayores por DOI de 2025) se elige la
de mayor número exacto de artículos de revista de 2025, y se recalculan afiliación y bibliografía sin ella.
Salida: data/raw/crossref/<fecha>_sensibilidad_organizacion_mayor.json. Es un archivo local: identifica a la
organización de cada país, por eso data/sensibilidad_organizacion_mayor.csv (script 10) se publica sin ella.
Uso: uv run python scripts/07_sensibilidad_organizacion_mayor.py   (~5 minutos)
"""

import json
import statistics as st

from lcm.config import ruta_crudo
from lcm.crossref import completitud, contar
from lcm.db import conectar

FECHAS = "type:journal-article,from-pub-date:2025-01-01,until-pub-date:2025-12-31"


def dois_2025(js: str) -> int:
    """DOI de un miembro con año de emisión 2025 (todos los tipos): sirve solo para elegir candidatos."""
    return next((n for a, n in json.loads(js) if a == 2025), 0)


con = conectar(solo_lectura=True)
paises = sorted(r[0] for r in con.execute("SELECT pais FROM crossref.paises_incluidos WHERE incluido").fetchall())
tot = {f[0]: f for f in con.execute(
    """SELECT pais, sum(total), sum(afiliacion), sum(referencias) FROM crossref.completitud_bloques
       WHERE anio = 2025 AND grupo = 'miembros' GROUP BY 1"""
).fetchall()}
resultado = {}
for p in paises:
    filas = con.execute(
        """SELECT id, nombre, articulos, dois_por_anio FROM crossref.miembros
           WHERE pais_latam = ? AND articulos >= 100 AND lower(nombre) NOT LIKE '%scielo%'""", [p]
    ).fetchall()
    cand = {f[0]: f for f in sorted(filas, key=lambda f: -f[2])[:3]}
    cand.update({f[0]: f for f in sorted(filas, key=lambda f: -dois_2025(f[3]))[:3]})
    exactos = {mid: contar(f"member:{mid},{FECHAS}") for mid in cand}
    mid = max(exactos, key=exactos.get)
    r = completitud(mid, 2025)
    f = tot[p]
    t = f[1] - r["total"]
    resultado[p] = {
        "miembro_id": mid, "nombre": cand[mid][1], "peso_pct": 100 * r["total"] / f[1],
        "afiliacion_con_pct": 100 * f[2] / f[1], "afiliacion_sin_pct": 100 * (f[2] - r["afiliacion"]) / t,
        "bibliografia_con_pct": 100 * f[3] / f[1], "bibliografia_sin_pct": 100 * (f[3] - r["referencias"]) / t,
    }
    print(p, f"peso de la mayor {resultado[p]['peso_pct']:.1f} %", flush=True)
con.close()

v = resultado.values()
print("Mediana afiliación:", round(st.median(x["afiliacion_con_pct"] for x in v), 1), "->",
      round(st.median(x["afiliacion_sin_pct"] for x in v), 1))
print("Mediana bibliografía:", round(st.median(x["bibliografia_con_pct"] for x in v), 1), "->",
      round(st.median(x["bibliografia_sin_pct"] for x in v), 1))
destino = ruta_crudo("crossref", "sensibilidad_organizacion_mayor", "json")
destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
print("->", destino)
