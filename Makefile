PYTHON ?= python3
REFERENCE_CONFIG ?= apps/reference-data/config/default.yaml
ROSTER_CONFIG ?= apps/roster-generator/config/default.yaml
FORMULA_API_CONFIG ?= apps/formula-workbench/api/config/default.yaml

.PHONY: install reference-download reference-build reference-publish roster-generate all \
	formula-api workbench workbench-build test test-python test-web manifest clean

install:
	$(PYTHON) -m pip install -e '.[dev]'
	npm install

reference-download:
	$(PYTHON) -m reference_data_app --config $(REFERENCE_CONFIG) download

reference-build:
	$(PYTHON) -m reference_data_app --config $(REFERENCE_CONFIG) build

reference-publish:
	$(PYTHON) -m reference_data_app --config $(REFERENCE_CONFIG) publish

roster-generate:
	$(PYTHON) -m roster_generator --config $(ROSTER_CONFIG) generate

formula-api:
	$(PYTHON) -m formula_preview_api --config $(FORMULA_API_CONFIG)

all:
	$(MAKE) reference-publish
	$(MAKE) roster-generate

workbench:
	npm run workbench:dev

workbench-build:
	npm run workbench:build

test: test-python test-web

test-python:
	$(PYTHON) -m pytest
	$(PYTHON) -m ruff check .

test-web:
	npm run workbench:test
	npm run workbench:build

manifest:
	$(PYTHON) scripts/update_file_manifest.py

clean:
	rm -rf build dist coverage .pytest_cache .ruff_cache .mypy_cache *.egg-info
	rm -rf apps/formula-workbench/dist roster_data/packages __pycache__
	find apps/reference-data apps/roster-generator apps/formula-workbench/api packages scripts tests \
		-type d -name __pycache__ \
		-prune -exec rm -rf {} +
