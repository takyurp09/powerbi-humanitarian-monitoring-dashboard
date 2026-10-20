# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/).

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
