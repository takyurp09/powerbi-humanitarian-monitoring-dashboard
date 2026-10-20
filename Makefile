# Uses the project virtualenv when present (needs pandas, numpy, openpyxl, matplotlib; pdftotext from poppler).
PY ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: all ingest data validate case-study

all: ingest data validate case-study

# ingest_wages.py skips with a message (keeping the committed CSV) when WAGE_SOURCE is absent.
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
