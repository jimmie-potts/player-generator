PYTHON ?= python3
CONFIG ?= config/default.yaml

.PHONY: install download reference generate compare all test clean

install:
	$(PYTHON) -m pip install -e '.[dev]'

download:
	$(PYTHON) -m player_generator --config $(CONFIG) download-reference

reference:
	$(PYTHON) -m player_generator --config $(CONFIG) build-reference

generate:
	$(PYTHON) -m player_generator --config $(CONFIG) generate

compare:
	$(PYTHON) -m player_generator --config $(CONFIG) compare

all:
	$(PYTHON) -m player_generator --config $(CONFIG) all

test:
	$(PYTHON) -m pytest

clean:
	rm -f generated_data/default_roster.json generated_data/fictional_players.csv
	rm -f reports/comparison_report.json reports/comparison_table.csv
