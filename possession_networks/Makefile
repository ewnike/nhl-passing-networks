SAMPLE = POSSNET_CONFIG=config/sample.yaml

.PHONY: sample setup pull build validate explore networks possessions markov incremental test lint contract app all

setup:
	pip install -r requirements.txt
	pip install -e .

pull:
	python scripts/01_pull_data.py

build:
	python scripts/02_build_canonical.py

validate:
	python scripts/03_validate.py

explore:
	python scripts/04_explore.py

networks:
	python scripts/05_build_networks.py

possessions:
	python scripts/06_build_possessions.py

markov:
	python scripts/08_markov_xt.py

app:
	python scripts/11_build_app_data.py

incremental:
	python scripts/09_incremental_value.py
	python scripts/10_incremental_figures.py

contract:
	python scripts/00_render_contract.py

test:
	pytest

lint:
	ruff check src scripts tests

all: pull build validate explore networks possessions markov incremental

# Run the whole pipeline on a synthetic league (no licensed data needed).
# Outputs land in sample_data/ (git ignored).
sample:
	python scripts/make_synthetic_sample.py
	$(SAMPLE) python scripts/02_build_canonical.py
	$(SAMPLE) python scripts/03_validate.py
	$(SAMPLE) python scripts/05_build_networks.py
	$(SAMPLE) python scripts/06_build_possessions.py
	$(SAMPLE) python scripts/08_markov_xt.py
