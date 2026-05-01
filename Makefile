.PHONY: setup db-start db-init generate-data etl dashboard test lint clean

PYTHON := python
PIP := pip

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; else echo ".env already exists"; fi
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt

db-start:
	docker compose up -d postgres


db-init:
	python scripts/init_db.py

generate-data:
	python -m src.ingestion.generate_data \
		--start-date $${DATA_START_DATE:-2024-01-01} \
		--end-date $${DATA_END_DATE:-2026-01-01} \
		--azure-input-dir $${AZURE_PM_INPUT_DIR:-data/external} \
		--output-dir $${RAW_DATA_DIR:-data/raw} \
		--seed $${RANDOM_SEED:-42}


etl:
	python -m src.transformation.etl_pipeline --raw-dir data/raw

dashboard:
	streamlit run dashboard/app.py

test:
	pytest --cov=src --cov=dashboard --cov-report=term-missing

lint:
	ruff check src dashboard tests
	black --check src dashboard tests

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .coverage
