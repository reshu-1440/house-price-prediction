PYTHON := .venv/Scripts/python.exe

.PHONY: install download-data lint test test-unit test-cov eda split train evaluate mlflow-train pipeline serve

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install --no-build-isolation --no-deps -e .

download-data:
	$(PYTHON) Data/data_download.py

lint:
	$(PYTHON) -m ruff check src tests

test:
	$(PYTHON) -m pytest -v

test-unit:
	$(PYTHON) -m pytest tests/unit -v

test-cov:
	$(PYTHON) -m pytest --cov=src --cov-report=term-missing -v

eda:
	$(PYTHON) notebooks/01_eda.py

split:
	$(PYTHON) -m src.data.split

train:
	$(PYTHON) -m src.models.train

evaluate:
	$(PYTHON) -m src.models.evaluate

mlflow-train:
	$(PYTHON) -m src.models.mlflow_tracking

pipeline:
	$(PYTHON) -m src.pipeline.training_pipeline

serve:
	$(PYTHON) -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
