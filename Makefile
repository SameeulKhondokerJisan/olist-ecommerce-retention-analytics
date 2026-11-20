PYTHON ?= python

.PHONY: setup data pipeline notebook test all clean

setup:
	$(PYTHON) -m pip install -r requirements.txt

data:
	$(PYTHON) -m src.download_data

pipeline:
	$(PYTHON) -m src.run_pipeline

notebook:
	$(PYTHON) -m src.build_notebook
	$(PYTHON) -m src.run_notebook notebooks/olist_analysis.ipynb

test:
	$(PYTHON) -m pytest -q

all: data pipeline notebook test

clean:
	rm -rf data/processed reports/tables reports/figures reports/results.json
