"""Calcula las cifras del paper desde la base local y los crudos: tablas 1 a 5, sección 3.3 (OpenAlex) y Chile (3.5).

Imprime las tablas en formato Markdown, para compararlas con el paper. Usa crossref.completitud_bloques (04),
crossref.completitud_miembros (05), la línea base mundial (06), la sensibilidad (07) y
openalex.afiliacion_recuperada (08), siempre con el crudo más reciente.
Uso: uv run python scripts/09_cifras_paper.py
"""

import json
import math
import statistics as st
import sys

from lcm.config import CRUDOS
from lcm.db import conectar

sys.stdout.reconfigure(encoding="utf-8")

NOMBRES = {
    "AR": "Argentina", "BO": "Bolivia", "BR": "Brasil", "CL": "Chile", "CO": "Colombia", "CR": "Costa Rica",
    "DO": "Rep. Dominicana", "EC": "Ecuador", "GT": "Guatemala", "MX": "México", "PA": "Panamá", "PE": "Perú",
    "PY": "Paraguay", "UY": "Uruguay", "VE": "Venezuela",
}
CAMPOS = [("Resumen", "resumen"), ("Licencia", "licencia"), ("ORCID", "orcid"), ("Bibliografía", "referencias"),
          ("Afiliación", "afiliacion"), ("ROR", "ror"), ("Financiamiento", "financiamiento")]


def pct(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",") + " %"


def n(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def crudo_reciente(patron: str) -> dict:
    return json.loads(sorted((CRUDOS / "crossref").glob(patron))[-1].read_text(encoding="utf-8"))


con = conectar(solo_lectura=True)

# --- Tabla 1: resto del mundo, mediana y conjunto de los 15 países (2025, sin cuentas de SciELO)
mundo = crudo_reciente("*_linea_base_mundial_2025.json")
por_pais = con.execute(
    """SELECT pais, sum(total), sum(referencias), sum(resumen), sum(orcid), sum(afiliacion), sum(ror),
              sum(financiamiento), sum(licencia)
       FROM crossref.completitud_bloques WHERE anio = 2025 AND grupo = 'miembros' GROUP BY pais"""
).fetchall()
cols = {"total": 1, "referencias": 2, "resumen": 3, "orcid": 4, "afiliacion": 5, "ror": 6, "financiamiento": 7,
        "licencia": 8}
tot_conj = {k: sum(r[i] for r in por_pais) for k, i in cols.items()}
print("## Tabla 1\n")
print("| Metadato, 2025 | Resto del mundo (conjunto) | América Latina, mediana de los 15 países | América Latina, conjunto de los 15 países |")
print("|---|---|---|---|")
for etiqueta, k in CAMPOS:
    med = st.median(100 * r[cols[k]] / r[1] for r in por_pais)
    print(f"| {etiqueta} | {pct(100 * mundo[k] / mundo['total'])} | {pct(med)} | {pct(100 * tot_conj[k] / tot_conj['total'])} |")
print(f"\nResto del mundo: {n(mundo['miembros'])} organizaciones, {n(mundo['total'])} artículos. "
      f"América Latina: {n(tot_conj['total'])} artículos")
miembros_validos = con.execute(
    """SELECT count(*) FROM crossref.miembros m JOIN crossref.paises_incluidos p ON p.pais = m.pais_latam
       WHERE p.incluido AND m.articulos >= 100 AND lower(m.nombre) NOT LIKE '%scielo%'"""
).fetchone()[0]
print(f"Organizaciones de América Latina con 100 o más artículos, sin cuentas de SciELO: {n(miembros_validos)}")
print(f"Miembros de Crossref: {n(con.execute('SELECT count(*) FROM crossref.miembros').fetchone()[0])}; "
      f"asignados a países de América Latina: "
      f"{n(con.execute('SELECT count(*) FROM crossref.miembros WHERE pais_latam IS NOT NULL').fetchone()[0])}; "
      f"países: {con.execute('SELECT count(DISTINCT pais_latam) FROM crossref.miembros').fetchone()[0]}")

# --- Tabla 2: evolución del conjunto de los 15 países
print("\n## Tabla 2\n")
anios = range(2020, 2026)
ev = {}
for a in anios:
    fila = con.execute(
        """SELECT sum(total), sum(referencias), sum(resumen), sum(orcid), sum(afiliacion), sum(ror),
                  sum(financiamiento), sum(licencia)
           FROM crossref.completitud_bloques WHERE anio = ? AND grupo = 'miembros'""", [a]
    ).fetchone()
    ev[a] = dict(zip(["total", "referencias", "resumen", "orcid", "afiliacion", "ror", "financiamiento", "licencia"], fila))
print("| Metadato | " + " | ".join(str(a) for a in anios) + " |")
print("|---|" + "---|" * 6)
for etiqueta, k in CAMPOS:
    print(f"| {etiqueta} | " + " | ".join(pct(100 * ev[a][k] / ev[a]["total"]) for a in anios) + " |")
print("| *Artículos* | " + " | ".join(f"*{n(ev[a]['total'])}*" for a in anios) + " |")

# --- Tabla 3: afiliación y bibliografía por país, 2020 y 2025
print("\n## Tabla 3\n")
datos = {}
for p in NOMBRES:
    d = {}
    for a in (2020, 2025):
        t, af, bi = con.execute(
            """SELECT sum(total), sum(afiliacion), sum(referencias) FROM crossref.completitud_bloques
               WHERE pais = ? AND anio = ? AND grupo = 'miembros'""", [p, a]).fetchone()
        d[a] = (t, 100 * af / t, 100 * bi / t)
    datos[p] = d
orden = sorted(datos, key=lambda p: -datos[p][2025][0])
print("| País | Artículos 2020 | Artículos 2025 | Afiliación 2020 | Afiliación 2025 | Bibliografía 2020 | Bibliografía 2025 |")
print("|---|---|---|---|---|---|---|")
for p in orden:
    d = datos[p]
    print(f"| {NOMBRES[p]} | {n(d[2020][0])} | {n(d[2025][0])} | {pct(d[2020][1])} | {pct(d[2025][1])} | {pct(d[2020][2])} | {pct(d[2025][2])} |")

# --- Sección 3.3: OpenAlex, artículos de 2025 de la muestra
print("\n## Sección 3.3 (OpenAlex)\n")


def wilson(k: int, m: int, z: float = 1.96) -> float:
    """Mitad del intervalo de Wilson al 95 % para una proporción, en puntos porcentuales."""
    p = k / m
    return 100 * z * math.sqrt(p * (1 - p) / m + z * z / (4 * m * m)) / (1 + z * z / m)


oa = con.execute(
    "SELECT pais, en_openalex, afil_crossref, inst_oa, texto_afil_oa FROM openalex.afiliacion_recuperada"
).df()
enc = oa[oa.en_openalex]
sin = enc[~enc.afil_crossref]
con_af = enc[enc.afil_crossref]
inst = 100 * sin.inst_oa.mean()
solo_texto = 100 * (sin.texto_afil_oa & ~sin.inst_oa).mean()
print(f"Muestra: {n(len(oa))}; encontrados en OpenAlex: {n(len(enc))} ({pct(100 * len(enc) / len(oa), 0)}); "
      f"sin afiliación en Crossref: {n(len(sin))}")
print(f"Sin afiliación en Crossref: institución identificada {pct(inst)}, solo texto {pct(solo_texto)}, "
      f"ningún dato {pct(100 - inst - solo_texto)}; con texto de afiliación {pct(100 * sin.texto_afil_oa.mean())}")
grupos = sin.groupby("pais").inst_oa.agg(["sum", "size"])
por_pais_oa = 100 * grupos["sum"] / grupos["size"]
arts25 = {p: datos[p][2025][0] for p in por_pais_oa.index}
ponderado = sum(por_pais_oa[p] * arts25[p] for p in arts25) / sum(arts25.values())
margenes = [wilson(int(k), int(m)) for k, m in zip(grupos["sum"], grupos["size"])]
print(f"Mediana de los 15 países: {pct(st.median(por_pais_oa))} (de {pct(por_pais_oa.min(), 0)} en "
      f"{NOMBRES[por_pais_oa.idxmin()]} a {pct(por_pais_oa.max(), 0)} en {NOMBRES[por_pais_oa.idxmax()]}); "
      f"ponderado por artículos de 2025: {pct(ponderado)}")
print(f"Artículos por país: de {grupos['size'].min()} a {grupos['size'].max()}; margen de error al 95 % "
      f"(Wilson): de ±{min(margenes):.0f} a ±{max(margenes):.0f} puntos")
print(f"Con afiliación en Crossref: {n(len(con_af))} artículos; institución identificada {pct(100 * con_af.inst_oa.mean())}")

# --- Tabla 4: sensibilidad
print("\n## Tabla 4\n")
sens = crudo_reciente("*_sensibilidad_organizacion_mayor.json")
orden4 = sorted(sens, key=lambda p: -sens[p]["peso_pct"])


def negrita(a: float, b: float) -> str:
    return f"**{pct(b)}**" if abs(b - a) >= 5 else pct(b)


print("| País | Peso de la mayor | Afiliación, todas las organizaciones | Afiliación, sin la mayor | Bibliografía, todas las organizaciones | Bibliografía, sin la mayor |")
print("|---|---|---|---|---|---|")
for p in orden4:
    s = sens[p]
    print(f"| {NOMBRES[p]} | {pct(s['peso_pct'])} | {pct(s['afiliacion_con_pct'])} | {negrita(s['afiliacion_con_pct'], s['afiliacion_sin_pct'])} | {pct(s['bibliografia_con_pct'])} | {negrita(s['bibliografia_con_pct'], s['bibliografia_sin_pct'])} |")
med = lambda k: st.median(sens[p][k] for p in sens)
print(f"| *Mediana de los 15* | *{pct(med('peso_pct'))}* | *{pct(med('afiliacion_con_pct'))}* | *{pct(med('afiliacion_sin_pct'))}* | *{pct(med('bibliografia_con_pct'))}* | *{pct(med('bibliografia_sin_pct'))}* |")

# --- Tabla 5: cuentas de SciELO
print("\n## Tabla 5\n")


def afil(pais: str | None, con_scielo: bool) -> float:
    filtro = "" if con_scielo else "AND grupo = 'miembros'"
    pcond = "AND pais = ?" if pais else ""
    q = f"SELECT sum(afiliacion)*100.0/sum(total) FROM crossref.completitud_bloques WHERE anio = 2025 {filtro} {pcond}"
    return con.execute(q, [pais] if pais else []).fetchone()[0]


print("| Afiliación, 2025 | Sin cuentas de SciELO | Con cuentas de SciELO |")
print("|---|---|---|")
print(f"| Brasil | {pct(afil('BR', False))} | {pct(afil('BR', True))} |")
print(f"| Conjunto de los 15 países | {pct(afil(None, False))} | {pct(afil(None, True))} |")
print(f"| Mediana de los 15 países | {pct(st.median(afil(p, False) for p in NOMBRES))} | "
      f"{pct(st.median(afil(p, True) for p in NOMBRES))} |")

# --- Sección 3.5: Chile por organización (solo cifras agregadas)
print("\n## Sección 3.5 (Chile, 2025, organizaciones con 20 o más artículos, sin cuentas de SciELO)\n")
fil = con.execute(
    """SELECT total, referencias, orcid, afiliacion FROM crossref.completitud_miembros
       WHERE pais = 'CL' AND anio = 2025 AND total >= 20 AND lower(nombre) NOT LIKE '%scielo%'"""
).fetchall()
tot = sum(f[0] for f in fil)
sin_ref = [f for f in fil if f[1] == 0]
bib50 = [f for f in fil if f[1] / f[0] >= 0.5]
af50 = [f for f in fil if f[3] / f[0] >= 0.5]
orc50 = [f for f in fil if f[2] / f[0] > 0.5]
print(f"Organizaciones: {len(fil)} ({n(tot)} artículos); sin bibliografía: {len(sin_ref)}; bibliografía en la mitad o "
      f"más: {len(bib50)}; afiliación en la mitad o más: {len(af50)}; ORCID en más de la mitad: {len(orc50)}")
tot_ref = sum(f[1] for f in fil)
print(f"Las {len(bib50)} con bibliografía en la mitad o más: {n(sum(f[0] for f in bib50))} artículos "
      f"({pct(100 * sum(f[0] for f in bib50) / tot, 0)}); aportan {n(sum(f[1] for f in bib50))} de {n(tot_ref)} "
      f"con bibliografía ({pct(100 * sum(f[1] for f in bib50) / tot_ref, 0)})")
tot_af = sum(f[3] for f in fil)
print(f"Las {len(af50)} con afiliación en la mitad o más: {n(sum(f[0] for f in af50))} artículos "
      f"({pct(100 * sum(f[0] for f in af50) / tot, 0)}); aportan {n(sum(f[3] for f in af50))} de {n(tot_af)} "
      f"({pct(100 * sum(f[3] for f in af50) / tot_af, 0)})")
print(f"Las {len(sin_ref)} sin bibliografía suman {n(sum(f[0] for f in sin_ref))} artículos")
con.close()
