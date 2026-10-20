# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/).

## [1.0.1] - 2026-10-20

### Changed
- README describes what the repository contains: the Power BI data model, Power Query scripts, DAX measures, theme and page specification, plus the web dashboard. Removed the placeholder for report screenshots and the empty `dashboard/` entry.
- README preview now shows screenshots of the web dashboard (`assets/web_overview.png`, `assets/web_camps_map.png`).
- Web dashboard: sector status labels and the median label on the reach chart are no longer cut off.

## [1.0.0] - 2026-10-20

### Added
- Python pipeline: real population and wage ingest, synthetic programme data generation, cleaning with a data quality log, and model validation.
- Star-schema model (`data/model/`), Power Query scripts, DAX measure library and Power BI report theme.
- Documentation: schema, data dictionary, dashboard specification, build guide and case study with figures.
- README banner and overview design mock-up generated with Python (`scripts/make_readme_assets.py`).
- GitHub Actions workflow running `make data validate case-study`.
- Citation metadata, contributing guide, issue templates and `.editorconfig`.

### Changed
- `scripts/ingest_population.py` exits 0 with a message and keeps the committed CSVs when the HDX workbook, UNHCR PDF or `pdftotext` is unavailable (paths can be overridden with `HDX_SOURCE` and `UNHCR_PDF`).
