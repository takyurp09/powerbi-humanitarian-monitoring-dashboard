# Humanitarian Programme Monitoring Dashboard (Power BI)

A portfolio project that builds an end-to-end monitoring solution for a multi-sector, child-focused programme in a humanitarian response context. Messy partner reports and third-party monitoring (TPM) visit logs are cleaned with Python into a star schema, which feeds a Power BI report covering target achievement by sector, indicator and camp, reporting timeliness, data quality, equity by sex, and the follow-up of issues raised by third-party monitors. The repository contains the data pipeline, Power Query scripts, a documented DAX measure library, a report theme and a full page specification.

**Case study:** [docs/CASE_STUDY.md](docs/CASE_STUDY.md) is an analytical brief that uses the dashboard to answer six monitoring questions after a 2026 funding cut (sector performance, camp coverage, reporting and data quality, TPM follow-up, sex gaps, host-community wages), with recommendations.

## What it demonstrates
- **Data modelling**: a star schema with conformed date, camp, sector, indicator and partner dimensions and two fact tables at different grains.
- **DAX**: a measure library organised in display folders, including mixed-aggregation achievement logic, status thresholds, time intelligence (MoM, YTD, same period last year, rolling three months) and dynamic titles.
- **Data quality**: rule-based cleaning of raw partner reports (name standardisation, date parsing, deduplication) with a cleaning log, plus in-report timeliness and quality scoring.
- **TPM follow-up**: closure rates, days to close and overdue follow-ups by partner, camp and issue category.
- **GIS**: a camp-level map visual with status colouring and drill-through to camp detail.
- **Host-community context**: real BBS agricultural wage series for Cox's Bazar against the national median, shown descriptively next to real camp population.

## Architecture

```mermaid
flowchart LR
    A[Raw CSV<br/>partner reports, TPM logs<br/>data/raw/] --> B[Python cleaning<br/>scripts/clean_data.py]
    B --> C[Star schema CSVs<br/>data/model/]
    B --> L[dq_log.csv]
    C --> D[Power Query<br/>powerquery/*.pq]
    D --> E[Power BI model<br/>relationships + DAX measures]
    E --> F[Report pages<br/>overview, sector, map, DQ, TPM, host context]
```

## Repository structure

```
.
├── assets/            Wireframe and report screenshots
├── dashboard/         HumanitarianMonitoring.pbix (to be added)
├── data/
│   ├── external/      Public source files (HDX, UNHCR) + SOURCES.md
│   ├── raw/           Messy synthetic inputs
│   └── model/         Cleaned star-schema tables
├── dax/measures.dax   DAX measure library
├── docs/
│   ├── SCHEMA.md            Data model contract
│   ├── DATA_DICTIONARY.md   Tables, columns, types
│   ├── DASHBOARD_SPEC.md    Page-by-page report specification
│   ├── CASE_STUDY.md        Analytical brief built on the dashboard
│   ├── case_study_tables/   Figures cited in the case study
│   └── BUILD_GUIDE.md       Steps to assemble the .pbix
├── powerquery/        Power Query (M) script per table
├── scripts/           Population and wage ingest, data generation, cleaning, validation, case-study metrics (Python)
├── theme/report_theme.json  Power BI report theme
├── Makefile
└── LICENSE
```

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # pdftotext (poppler) also required
make all        # ingest real population and wage data, generate synthetic raw data, clean, validate, case-study metrics
```

Then follow [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md) to load the model into Power BI Desktop, import the measures, apply the theme and build the pages.

## Key metrics

| Metric | Definition |
|---|---|
| Achievement % | SUM(achieved) / SUM(target) for count indicators; AVERAGE(achieved) / AVERAGE(target) for rate indicators; equal-weight average across indicators. |
| Status | On track >= 90%; at risk 70-89%; off track < 70%. |
| Reporting timeliness % | Share of result rows submitted by the 10th of the following month. |
| Data quality score % | Share of result rows with no data quality flag. |
| TPM closure rate | Closed follow-ups / visits that flagged at least one issue. |
| Average days to close | Mean days from visit to closure, over closed follow-ups of visits that flagged issues. |
| Coverage % / Reach per 1,000 children | Average monthly children reached relative to real camp children population. |
| Open follow-ups > 30 days | Open follow-ups from visits more than 30 days before the latest visit date. |
| Female share % | Female share of achieved beneficiaries (count indicators). |

Full definitions are in [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) and the comments of [dax/measures.dax](dax/measures.dax).

## Screenshots
To be added after building the report.

| Page | File |
|---|---|
| Executive overview | `assets/overview.png` |
| Sector and indicator performance | `assets/sector.png` |
| Camp map and equity | `assets/camp_map.png` |
| Reporting timeliness and data quality | `assets/timeliness_dq.png` |
| Third-party monitoring follow-up | `assets/tpm.png` |
| Host community context | `assets/host_context.png` |
| Camp detail (drill-through) | `assets/camp_detail.png` |

The planned overview layout is shown in [assets/wireframe.svg](assets/wireframe.svg).

## Data
The model combines real public camp population data with synthetic programme data.

| Component | Real or synthetic | Source | Licence / terms | As of |
|---|---|---|---|---|
| Camp list, upazila, union, coordinates (`dim_camp`, `dim_camp_population_2021`) | Real | HDX / ISCG, RRRC-UNHCR family counting ([dataset](https://data.humdata.org/dataset/site-location-of-rohingya-refugees-in-cox-s-bazar)) | CC0 | 31 Oct 2021 |
| Camp population and families (`dim_camp[population]`, `ref_population_2026`) | Real | Government of Bangladesh - UNHCR Joint Registration, population dashboard ([PDF](https://data.unhcr.org/en/documents/download/123174)) | Public UNHCR document, reused with attribution | 30 Jun 2026 |
| Age/sex demographics, children share (`ref_demographics_2026`, `dim_camp[children_share]`) | Real (national share applied to each camp) | Same UNHCR dashboard | As above | 30 Jun 2026 |
| Host-community agricultural wages, Cox's Bazar and national median (`ref_wages_coxsbazar`) | Real | BBS Agricultural Wage Statistics, public download ([bbs.gov.bd](http://www.bbs.gov.bd/)); derived by the author from his research pipeline (`scripts/ingest_wages.py`) | Public government statistics, reused with attribution | 2017-01 to 2025-12 |
| Programme targets and results (`fact_results`) | Synthetic; count targets scaled to real camp (children) population | `scripts/generate_data.py`, seed 2026 | MIT (this repo) | 2025-01 to 2026-06 |
| Partners, indicators, TPM visits (`dim_partner`, `dim_indicator`, `fact_tpm_visits`) | Synthetic | `scripts/generate_data.py` | MIT (this repo) | 2025-01 to 2026-06 |

Source: Government of Bangladesh – UNHCR Joint Registration, 30 Jun 2026; BBS Agricultural Wage Statistics (derived by the author). Full provenance is in [data/external/SOURCES.md](data/external/SOURCES.md). The synthetic programme data do not represent any organisation's real results.

## Status
- Data pipeline, Power Query scripts, DAX measure library, theme and documentation: complete.
- Power BI report (.pbix): to be assembled; see [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md).

## Authorship and AI assistance
Designed and maintained by Muhammad Taky Tahmid. The data pipeline, DAX measure library and documentation were developed with AI assistance (Claude); the Power BI report is built and maintained by the author.

- GitHub: [takyurp09](https://github.com/takyurp09)

## Licence
Released under the [MIT Licence](LICENSE).
