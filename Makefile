PYTHON ?= python3
REFERENCE_CONFIG ?= apps/reference-data/config/default.yaml
ROSTER_CONFIG ?= apps/roster-generator/config/default.yaml

.PHONY: install reference-download reference-build roster-generate roster-compare all \
	workbench workbench-build test test-python test-web clean

install:
	$(PYTHON) -m pip install -e '.[dev]'
	npm install

reference-download:
	$(PYTHON) -m reference_data_app --config $(REFERENCE_CONFIG) download

reference-build:
	$(PYTHON) -m reference_data_app --config $(REFERENCE_CONFIG) build

roster-generate:
	$(PYTHON) -m roster_generator --config $(ROSTER_CONFIG) generate

roster-compare:
	$(PYTHON) -m roster_generator --config $(ROSTER_CONFIG) compare

all: reference-build roster-generate roster-compare

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

clean:
	rm -f roster_data/default_roster.json roster_data/players.csv
	rm -f reports/comparison_report.json reports/comparison_table.csv
