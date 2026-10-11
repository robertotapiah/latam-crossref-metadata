# Metadatos de revistas latinoamericanas en Crossref

**La afiliación institucional y el financiamiento casi no se registran (2020–2025)**

Roberto Tapia · ORCID [0009-0007-1660-422X](https://orcid.org/0009-0007-1660-422X)
Paper (preprint): [10.5281/zenodo.23250641](https://doi.org/10.5281/zenodo.23250641)
*English summary: [README.en.md](README.en.md)*

Este repositorio contiene el código y los datos agregados para replicar las cifras del paper. El paper y el póster
están en Zenodo.

## Qué responde

| Pregunta | Respuesta (2025) |
|---|---|
| ¿Qué proporción de los artículos de revista de 15 países latinoamericanos incluye cada metadato y cómo cambió entre 2020 y 2025? | Suben el resumen, la licencia, el ORCID y la bibliografía; la afiliación no mejora (de 9 % a 6 %, en el conjunto de los 15 países). |
| ¿Cómo se compara con el resto del mundo? | En el país típico, el resumen y el ORCID superan al resto del mundo; la afiliación (6 % frente a 32 %) y el financiamiento (menos de 1 % frente a 27 %) quedan muy por debajo. |
| Cuando falta la afiliación en Crossref, ¿la tiene OpenAlex? | En 75 de cada 100 artículos OpenAlex tiene una institución identificada (límite superior: no se midió si es la correcta). |

El método, los resultados completos y las limitaciones están en el paper.

## Contenido

| Carpeta | Qué hay |
|---|---|
| `lcm/` | Conectores a las API de Crossref y OpenAlex, configuración y base local (DuckDB) |
| `scripts/` | Los pasos del análisis, en orden |
| `data/` | Cifras agregadas (CSV) |

**Datos en `data/`** (extraídos el 10 de octubre de 2026, sin cuentas de SciELO):

- `completitud_pais_anio.csv`: por país y año (2020–2025), artículos de revista y cuántos tienen cada metadato.
  Organizaciones editoras con 100 o más artículos.
- `paises.csv`: los 20 países de América Latina con miembros en Crossref y si alcanzan el criterio de inclusión.
- `linea_base_mundial_2025.csv`: el resto del mundo en 2025, con los mismos criterios.
- `sensibilidad_organizacion_mayor.csv`: por país, peso de la organización editora de mayor volumen en 2025 y
  cifras de afiliación y bibliografía con y sin ella.
- `muestra_2025.csv`: la muestra de 1.500 artículos de 2025 (DOI) con sus marcas en Crossref y OpenAlex.

No se publican los datos crudos (se regeneran desde las API), nombres de personas ni el detalle por organización
editora.

## Cómo replicarlo

Requiere Python 3.11 o superior y [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env   # completa CONTACTO_EMAIL y OPENALEX_API_KEY
uv run python scripts/01_miembros.py
```

| Paso | Script | Qué hace | Tiempo aproximado |
|---|---|---|---|
| 1 | `01_miembros.py` | Descarga todos los miembros de Crossref | minutos |
| 2 | `02_carga_miembros.py` | Los carga a la base local y asigna el país desde la dirección | segundos |
| 3 | `03_paises_incluidos.py` | Criterio de inclusión: al menos 10 miembros con 100 o más artículos | segundos |
| 4 | `04_completitud_paises.py` | Conteos por país, año y metadato (reanudable) | ~30 minutos |
| 5 | `05_detalle_miembros.py [PAÍS]` | Detalle por organización editora de un país (por defecto CL) | ~15–20 minutos |
| 6 | `06_linea_base_mundial.py` | Resto del mundo con los mismos criterios | ~15 minutos |
| 7 | `07_sensibilidad_organizacion_mayor.py` | Cifras de cada país sin su organización editora de mayor volumen | ~5 minutos |
| 8 | `08_muestra_openalex.py` | Muestra de 2025 y cruce con OpenAlex | ~5 minutos |
| 9 | `09_cifras_paper.py` | Calcula las tablas y cifras del paper | segundos |
| 10 | `10_exportar_datos.py` | Exporta las cifras agregadas a `data/` | segundos |

Los metadatos de Crossref cambian con el tiempo: una extracción nueva dará cifras cercanas, no idénticas.
Crossref no permite fijar una semilla en sus muestras aleatorias; para repetir el paso 8 con los mismos artículos
del paper, usa la lista publicada:

```bash
uv run python scripts/08_muestra_openalex.py data/muestra_2025.csv
```

## Cómo citar

Tapia, R. (2026). *Metadatos de revistas latinoamericanas en Crossref: la afiliación institucional y el
financiamiento casi no se registran (2020–2025)* [Preprint]. Zenodo. https://doi.org/10.5281/zenodo.23250641

## Uso de inteligencia artificial

Se usó Claude (Anthropic) como apoyo para escribir el código. Las cifras provienen de las API públicas de Crossref y
OpenAlex y se calcularon con este código; el autor las verificó contra las fuentes. Ninguna fue generada ni
modificada por IA.

## Licencias

- Código (`lcm/`, `scripts/`): [MIT](LICENSE).
- Datos agregados (`data/`): [CC BY 4.0](LICENSE-CONTENIDO.md).
- Fuentes: API pública de Crossref (metadatos abiertos) y OpenAlex (CC0).
