"""Define los países incluidos: al menos 10 miembros con 100 o más artículos de revista cada uno.

Criterio de inclusión explicado en el paper (sección 2.1). Crea
crossref.paises_incluidos con todos los países LATAM y la marca `incluido`; los que no
llegan al umbral se reportan como «sin datos suficientes».
Uso: uv run python scripts/03_paises_incluidos.py
"""

from lcm.db import conectar

MIN_MIEMBROS = 10
MIN_ARTICULOS = 100

con = conectar()
con.execute(
    f"""
    CREATE OR REPLACE TABLE crossref.paises_incluidos AS
    SELECT pais_latam AS pais,
           count(*) FILTER (WHERE articulos >= {MIN_ARTICULOS}) AS miembros_validos,
           sum(articulos) AS articulos,
           count(*) FILTER (WHERE articulos >= {MIN_ARTICULOS}) >= {MIN_MIEMBROS} AS incluido
    FROM crossref.miembros
    WHERE pais_latam IS NOT NULL
    GROUP BY 1
    """
)
print(con.execute("SELECT * FROM crossref.paises_incluidos ORDER BY incluido DESC, articulos DESC").df().to_string(index=False))
con.close()
