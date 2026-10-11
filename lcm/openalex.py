"""Conector de OpenAlex: consultas agregadas (group_by) y descargas filtradas.

Por qué group_by: devuelve conteos ya agregados en una sola solicitud, así se gasta
muy poco del presupuesto diario. Las descargas de trabajos (`trabajos`) son más caras:
úsalas solo cuando necesites registros individuales, y prefiere el snapshot para volúmenes grandes.
"""

from __future__ import annotations

import time
from typing import Iterator

import requests

from lcm.config import clave

URL = "https://api.openalex.org"
PAUSA = 0.2  # segundos entre solicitudes
REINTENTOS = 4


def _get(ruta: str, params: dict) -> dict:
    """GET con clave, correo de contacto y reintentos con espera creciente."""
    params = {**params, "api_key": clave("OPENALEX_API_KEY")}
    correo = clave("CONTACTO_EMAIL", obligatoria=False)
    if correo:
        params["mailto"] = correo
    for intento in range(REINTENTOS):
        resp = requests.get(f"{URL}/{ruta}", params=params, timeout=60)
        if resp.status_code in (429, 500, 502, 503):
            time.sleep(2**intento)
            continue
        resp.raise_for_status()
        time.sleep(PAUSA)
        return resp.json()
    resp.raise_for_status()
    return {}


def agrupar(filtro: str, campo: str, entidad: str = "works", todo: bool = False) -> list[dict]:
    """Conteos agregados: filtro="authorships.countries:CL,publication_year:2019-2025",
    campo="open_access.oa_status". Devuelve [{'clave': ..., 'nombre': ..., 'n': ...}].

    Por defecto trae los primeros 200 grupos. Con todo=True pagina por cursor hasta
    agotarlos (necesario para campos con muchos valores, como la revista).
    """
    grupos, cursor = [], "*"
    while cursor:
        params = {"filter": filtro, "group_by": campo, "per-page": 200}
        if todo:
            params["cursor"] = cursor
        datos = _get(entidad, params)
        grupos += [
            {"clave": g["key"], "nombre": g.get("key_display_name"), "n": g["count"]}
            for g in datos["group_by"]
        ]
        cursor = datos["meta"].get("next_cursor") if todo else None
    return grupos


def fuentes(ids: list[str], lote: int = 50) -> list[dict]:
    """Datos de revistas (ISSN, nombre, tipo) a partir de sus ids de OpenAlex, en lotes de 50."""
    resultado = []
    for i in range(0, len(ids), lote):
        corto = [x.rsplit("/", 1)[-1] for x in ids[i : i + lote]]
        datos = _get(
            "sources",
            {
                "filter": "openalex:" + "|".join(corto),
                "select": "id,display_name,issn_l,issn,type",
                "per-page": lote,
            },
        )
        resultado += datos["results"]
    return resultado


def contar(filtro: str, entidad: str = "works") -> int:
    """Número de registros que cumplen el filtro (una solicitud mínima)."""
    return _get(entidad, {"filter": filtro, "per-page": 1})["meta"]["count"]


def muestra(filtro: str, n: int, semilla: int = 42, seleccion: str | None = None) -> list[dict]:
    """Muestra aleatoria reproducible de n trabajos (misma semilla = misma muestra, máx. 10.000)."""
    params = {"filter": filtro, "sample": n, "seed": semilla, "per-page": min(n, 200)}
    if seleccion:
        params["select"] = seleccion
    resultado, pagina = [], 1
    while len(resultado) < n:
        datos = _get("works", {**params, "page": pagina})
        if not datos["results"]:
            break
        resultado += datos["results"]
        pagina += 1
    return resultado[:n]


def trabajos(filtro: str, seleccion: str | None = None, maximo: int | None = None) -> Iterator[dict]:
    """Recorre los trabajos de un filtro con paginación por cursor.

    `seleccion` limita los campos devueltos (p. ej. "id,doi,open_access") para gastar menos.
    """
    cursor, entregados = "*", 0
    while cursor:
        params = {"filter": filtro, "per-page": 200, "cursor": cursor}
        if seleccion:
            params["select"] = seleccion
        datos = _get("works", params)
        for obra in datos["results"]:
            yield obra
            entregados += 1
            if maximo and entregados >= maximo:
                return
        cursor = datos["meta"].get("next_cursor")
