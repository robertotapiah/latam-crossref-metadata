# Latin American journal metadata in Crossref

**Institutional affiliation and funding are rarely registered (2020–2025)**

Roberto Tapia · ORCID [0009-0007-1660-422X](https://orcid.org/0009-0007-1660-422X)
Paper (preprint, in Spanish, with an English abstract): [10.5281/zenodo.23250641](https://doi.org/10.5281/zenodo.23250641)

This repository holds the code and aggregated data needed to reproduce the figures in the paper.

**Findings (2025, 15 Latin American countries, journal articles registered in Crossref):**

- Abstracts, licenses, ORCID iDs and reference lists increased between 2020 and 2025; author affiliations did not
  (9% to 6%).
- In the median country, abstracts and ORCID iDs exceed the rest of the world, while affiliations (6% vs. 32%) and
  funding information (under 1% vs. 27%) lag far behind.
- When Crossref has no affiliation, OpenAlex has an identified institution for 75 of every 100 articles (an upper
  bound: correctness was not assessed).

**Contents:** `lcm/` (Crossref and OpenAlex API connectors), `scripts/` (analysis steps 01–10, in order; see the
Spanish README for the table), `data/` (aggregated CSV files, extracted on 10 October 2026). Raw data, personal
names and organization-level detail are not published.

**Reproduce:** Python 3.11+ and [uv](https://docs.astral.sh/uv/); run `uv sync`, copy `.env.example` to `.env`
(contact email and OpenAlex API key) and run the scripts in order. Script 08 accepts `data/muestra_2025.csv` to reuse
the paper's sample.

**Cite:** Tapia, R. (2026). *Metadatos de revistas latinoamericanas en Crossref: la afiliación institucional y el
financiamiento casi no se registran (2020–2025)* [Preprint]. Zenodo. https://doi.org/10.5281/zenodo.23250641

**AI use:** Claude (Anthropic) assisted with the code. All figures come from the public Crossref and OpenAlex APIs,
were computed with this code and checked by the author.

**License:** code under [MIT](LICENSE); aggregated data under [CC BY 4.0](LICENSE-CONTENIDO.md).
