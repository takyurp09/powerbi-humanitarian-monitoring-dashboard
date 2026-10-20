# Uses the project virtualenv when present (needs pandas, numpy, openpyxl, matplotlib; pdftotext from poppler).
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: all ci ingest data validate case-study

all: ingest data validate case-study

ci: data validate case-study

# Ingest scripts skip with a message (keeping the committed CSVs) when external inputs are absent
# (the UNHCR PDF is not redistributed; WAGE_SOURCE lives outside the repo). CI uses `make ci`.
ingest:
	$(PY) -I scripts/ingest_population.py
	$(PY) -I scripts/ingest_wages.py

data:
	$(PY) scripts/generate_data.py
	$(PY) scripts/clean_data.py

validate:
	$(PY) scripts/validate_model.py

case-study:
	$(PY) scripts/case_study_metrics.py
	$(PY) scripts/make_readme_assets.py

