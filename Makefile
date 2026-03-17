.PHONY: install dev test lint run seed clean docker-up docker-down benchmark

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

test:
	python -m pytest tests/ -v --tb=short

test-cov:
	python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

run:
	python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

seed:
	python -m src.seed

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

demo: docker-up
	@echo "RedThread is running at http://localhost:8000"
	@echo "Demo data is loaded automatically on first launch."

benchmark:
	python -m benchmarks.run_benchmarks
