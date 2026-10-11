"""Conector de Crossref: miembros (editores) y su país.

La API REST es abierta; con correo de contacto entra al "polite pool" (más estable).
Crossref no tiene campo ni filtro de país para los miembros: solo `location`, texto libre
("Managua, Nicaragua", "Brazil"). Por eso `pais_de` toma el último tramo y lo normaliza.
"""

from __future__ import annotations

import time
import unicodedata

import requests

from lcm.config import clave

URL = "https://api.crossref.org"
PAUSA = 0.2
REINTENTOS = 4
POR_PAGINA = 1000

# País de LATAM -> variantes (español, inglés, portugués) ya sin tildes y en minúsculas.
PAISES_LATAM = {
    "AR": ["argentina"],
    "BO": ["bolivia"],
    "BR": ["brazil", "brasil"],
    "CL": ["chile"],
    "CO": ["colombia"],
    "CR": ["costa rica"],
    "CU": ["cuba"],
    "DO": ["dominican republic", "republica dominicana"],
    "EC": ["ecuador"],
    "SV": ["el salvador"],
    "GT": ["guatemala"],
    "HN": ["honduras"],
    "HT": ["haiti"],
    "MX": ["mexico"],
    "NI": ["nicaragua"],
    "PA": ["panama"],
    "PE": ["peru"],
    "PR": ["puerto rico"],
    "PY": ["paraguay"],
    "UY": ["uruguay"],
    "VE": ["venezuela"],
}
_VARIANTE_A_ISO = {v: iso for iso, vs in PAISES_LATAM.items() for v in vs}


def _simple(texto: str) -> str:
    """Minúsculas, sin tildes ni puntuación final."""
    s = unicodedata.normalize("NFKD", texto)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip(" .")


def pais_de(location: str | None) -> str | None:
    """Código ISO de un país LATAM según el último tramo de `location`, o None si no es LATAM
    (o no se pudo reconocer)."""
    if not location:
        return None
    ultimo = location.split(",")[-1]
    return _VARIANTE_A_ISO.get(_simple(ultimo))


def _get(ruta: str, params: dict) -> dict:
    params = {**params, "mailto": clave("CONTACTO_EMAIL")}
    for intento in range(REINTENTOS):
        try:
            resp = requests.get(f"{URL}/{ruta}", params=params, timeout=90)
        except (requests.Timeout, requests.ConnectionError):
            time.sleep(2**intento)
            continue
        if resp.status_code in (429, 500, 502, 503):
            time.sleep(2**intento)
            continue
        resp.raise_for_status()
        time.sleep(PAUSA)
        return resp.json()["message"]
    resp.raise_for_status()
    return {}


# Campos de completitud -> filtro de la API de works.
CAMPOS = {
    "referencias": "has-references:true",
    "resumen": "has-abstract:true",
    "orcid": "has-orcid:true",
    "afiliacion": "has-affiliation:true",
    "ror": "has-ror-id:true",
    "financiamiento": "has-funder:true",
    "licencia": "has-license:true",
}


def contar(filtro: str) -> int:
    """Número de works que cumplen un filtro (rows=0: no descarga registros).
    Repetir `member:ID` en el filtro suma miembros (OR)."""
    return _get("works", {"rows": 0, "filter": filtro})["total-results"]


def completitud(miembro_id: int | list[int], anio: int) -> dict:
    """Artículos de revista de un miembro (o suma de varios) en un año y cuántos tienen cada campo.
    Devuelve {'total': n, 'referencias': n, ...}; conteos completos, sin muestreo."""
    ids = [miembro_id] if isinstance(miembro_id, int) else miembro_id
    base = (
        f"{','.join(f'member:{i}' for i in ids)},type:journal-article,"
        f"from-pub-date:{anio}-01-01,until-pub-date:{anio}-12-31"
    )
    res = {"total": contar(base)}
    if res["total"]:
        for campo, f in CAMPOS.items():
            res[campo] = contar(f"{base},{f}")
    else:
        res.update({campo: 0 for campo in CAMPOS})
    return res


def miembros(todo: bool = True, filtro: str | None = None) -> list[dict]:
    """Miembros de Crossref con sus conteos. Con `todo=True` pagina por cursor (~34 mil miembros,
    ~34 solicitudes). Cada elemento trae `id`, `primary-name`, `location`, `counts`,
    `counts-type` y `breakdowns`."""
    params = {"rows": POR_PAGINA, "cursor": "*"}
    if filtro:
        params["filter"] = filtro
    salida: list[dict] = []
    while True:
        msg = _get("members", params)
        items = msg["items"]
        salida.extend(items)
        if not todo or not items:
            return salida
        params["cursor"] = msg["next-cursor"]
        if len(salida) >= msg["total-results"]:
            return salida


def muestra(filtro: str, k: int, intentos: int = 5) -> list[dict]:
    """k registros al azar que cumplen un filtro, sin repetir DOI. Devuelve DOI, miembro y autores.

    `sample` admite hasta 100 por consulta y cada consulta es independiente (puede repetir DOI),
    por eso se pide de nuevo hasta completar k. Crossref no admite semilla: guarda la lista resultante.
    """
    vistos: dict[str, dict] = {}
    for _ in range(intentos):
        faltan = k - len(vistos)
        if faltan <= 0:
            break
        items = _get("works", {"sample": min(faltan, 100), "filter": filtro,
                               "select": "DOI,member,author"})["items"]
        for it in items:
            vistos.setdefault(it["DOI"].lower(), it)
    return list(vistos.values())[:k]
