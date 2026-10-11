"""Cuando falta la afiliación en Crossref, ¿la tiene OpenAlex? (artículos 2025, 15 países; paper, sección 3.3)

Pregunta: si un artículo no declara afiliación en Crossref, ¿tiene OpenAlex igual una institución
(obtenida por otras vías, que no se conocen)? Se mide presencia, no si la institución es correcta.

Método:
1. Muestra aleatoria de ~100 artículos de revista 2025 por país (miembros válidos, sin cuentas de
   SciELO), repartida entre bloques de 100 miembros en proporción a sus artículos. Crossref no
   filtra `has-affiliation:false` (lo ignora), por eso se muestrea todo y se clasifica aquí:
   con afiliación = algún autor con `affiliation` no vacía. Los que sí la tienen sirven de
   comparación descriptiva (son revistas distintas: no es un grupo de control).
   `sample` de Crossref no acepta semilla: para repetir el análisis con los mismos artículos, pasar la
   lista publicada (data/muestra_2025.csv) como argumento; se usan sus DOI y sus marcas de Crossref.
2. Cada DOI se busca en OpenAlex (lotes de 50) y se mide si algún autor tiene institución, país
   o al menos el texto de afiliación.

Uso: uv run python scripts/08_muestra_openalex.py                         (muestra nueva)
     uv run python scripts/08_muestra_openalex.py data/muestra_2025.csv   (los mismos artículos del paper)
Reutiliza la muestra cruda del día si ya existe.
"""

import json
import sys

import pandas as pd

from lcm.config import ruta_crudo
from lcm.crossref import contar, muestra as muestra_crossref
from lcm.db import asegurar_esquema, conectar
from lcm.openalex import trabajos

ANIO = 2025
N_PAIS = 100
BLOQUE = 100
FECHAS = f"type:journal-article,from-pub-date:{ANIO}-01-01,until-pub-date:{ANIO}-12-31"


# --- 1. Muestra en Crossref -------------------------------------------------
archivo_muestra = ruta_crudo("crossref", f"muestra_afiliacion_{ANIO}", "jsonl")
if len(sys.argv) > 1:  # lista publicada: mismos DOI y marcas de Crossref que el paper
    lista = pd.read_csv(sys.argv[1])
    muestra = lista[["pais", "doi", "n_autores_cr", "afil_crossref"]].to_dict("records")
    print(f"Uso la lista {sys.argv[1]}: {len(muestra)} artículos", flush=True)
elif archivo_muestra.exists():
    muestra = [json.loads(l) for l in archivo_muestra.read_text(encoding="utf-8").splitlines()]
    print(f"Reutilizo {archivo_muestra.name}: {len(muestra)} artículos", flush=True)
else:
    con = conectar(solo_lectura=True)
    filas = con.execute(
        """
        SELECT m.pais_latam, m.id
        FROM crossref.miembros m JOIN crossref.paises_incluidos p ON p.pais = m.pais_latam
        WHERE p.incluido AND m.articulos >= 100 AND lower(m.nombre) NOT LIKE '%scielo%'
        ORDER BY m.pais_latam, m.id
        """
    ).fetchall()
    con.close()

    muestra = []
    for pais in sorted({f[0] for f in filas}):
        ids = [f[1] for f in filas if f[0] == pais]
        bloques = [ids[b : b + BLOQUE] for b in range(0, len(ids), BLOQUE)]
        tamanos = [contar(",".join(f"member:{i}" for i in bl) + "," + FECHAS) for bl in bloques]
        total = sum(tamanos)
        for bl, n in zip(bloques, tamanos):
            k = round(N_PAIS * n / total) if total else 0
            for it in muestra_crossref(",".join(f"member:{i}" for i in bl) + "," + FECHAS, k):
                autores = it.get("author", [])
                muestra.append({
                    "pais": pais,
                    "doi": it["DOI"].lower(),
                    "miembro": int(it["member"]),
                    "n_autores_cr": len(autores),
                    "afil_crossref": any(a.get("affiliation") for a in autores),
                })
        print(f"{pais}: {sum(1 for m in muestra if m['pais'] == pais)} artículos de {total}", flush=True)
    archivo_muestra.write_text("\n".join(json.dumps(m) for m in muestra), encoding="utf-8")

# --- 2. Búsqueda en OpenAlex ------------------------------------------------
archivo_oa = ruta_crudo("openalex", f"afiliacion_muestra_{ANIO}", "jsonl")
if archivo_oa.exists():
    obras = [json.loads(l) for l in archivo_oa.read_text(encoding="utf-8").splitlines()]
else:
    # Los DOIs con '|' o ',' romperían el filtro OR de OpenAlex: se omiten (y se reportan).
    dois = [m["doi"] for m in muestra if "|" not in m["doi"] and "," not in m["doi"]]
    print(f"Busco {len(dois)} DOIs en OpenAlex ({len(muestra) - len(dois)} omitidos)", flush=True)
    obras = []
    for i in range(0, len(dois), 50):
        lote = dois[i : i + 50]
        obras += list(trabajos("doi:" + "|".join(lote), seleccion="doi,authorships"))
    archivo_oa.write_text("\n".join(json.dumps(o) for o in obras), encoding="utf-8")

por_doi = {}
for o in obras:
    autores = o.get("authorships") or []
    por_doi[o["doi"].replace("https://doi.org/", "").lower()] = {
        "en_openalex": True,
        "n_autores_oa": len(autores),
        "inst_oa": any(a.get("institutions") for a in autores),
        "todos_inst_oa": bool(autores) and all(a.get("institutions") for a in autores),
        "pais_oa": any(a.get("countries") for a in autores),
        "texto_afil_oa": any(a.get("raw_affiliation_strings") for a in autores),
    }

vacio = {"en_openalex": False, "n_autores_oa": 0, "inst_oa": False, "todos_inst_oa": False,
         "pais_oa": False, "texto_afil_oa": False}
df = pd.DataFrame([{**m, **por_doi.get(m["doi"], vacio)} for m in muestra])

con = conectar()
asegurar_esquema(con, "openalex")
con.execute("CREATE OR REPLACE TABLE openalex.afiliacion_recuperada AS SELECT * FROM df")
con.close()

# --- 3. Resultado -------------------------------------------------------------
pct = lambda s: f"{100 * s.mean():.0f} %"
print(f"\nMuestra: {len(df)} artículos; en OpenAlex: {pct(df.en_openalex)}")
encontrados = df[df.en_openalex]
for grupo, sub in encontrados.groupby("afil_crossref"):
    nombre = "CON afiliación en Crossref (comparación)" if grupo else "SIN afiliación en Crossref"
    print(f"\n{nombre}: {len(sub)} artículos")
    print(f"  OpenAlex asigna institución a algún autor: {pct(sub.inst_oa)}")
    print(f"  ... a todos los autores:                   {pct(sub.todos_inst_oa)}")
    print(f"  OpenAlex asigna país a algún autor:        {pct(sub.pais_oa)}")
    print(f"  OpenAlex tiene texto de afiliación:        {pct(sub.texto_afil_oa)}")

sin = encontrados[~encontrados.afil_crossref]
print("\nSIN afiliación en Crossref, por país (% con institución en OpenAlex):")
print(sin.groupby("pais").agg(n=("doi", "size"), inst_oa=("inst_oa", "mean"))
      .assign(inst_oa=lambda d: (100 * d.inst_oa).round(0)).sort_values("inst_oa").to_string())
