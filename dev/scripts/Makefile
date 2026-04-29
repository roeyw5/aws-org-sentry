SHELL := /bin/bash

.PHONY: help lint format test clean package deploy init

help:
	@echo "Available targets:"
	@echo "  lint      - Run flake8 linter"
	@echo "  format    - Format code with black"
	@echo "  test      - Run pytest test suite"
	@echo "  package   - Build Lambda deployment package (lambda-package.zip)"
	@echo "  clean     - Remove build artifacts and cache files"
	@echo "  deploy    - Deploy infrastructure with Terraform"
	@echo "  init      - Initialize development environment"

lint:
	@echo "Running flake8..."
	@source ../../venv/bin/activate && flake8 --config=../config/.flake8 ../tests/ ../../src/

format:
	@echo "Formatting code with black..."
	@source ../../venv/bin/activate && black ../tests/ ../../src/

test:
	@echo "Running pytest..."
	@source ../../venv/bin/activate && cd ../.. && PYTHONPATH=src pytest dev/tests/

package:
	@echo "Building Lambda deployment package..."
	@./package-lambda.sh

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf __pycache__ .pytest_cache htmlcov .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -f lambda-*.zip ../../lambda-package.zip ../../lambda-package

deploy:
	@echo "Deploying with Terraform..."
	@cd terraform && terraform apply

init:
	@echo "Initializing development environment..."
	@cd ../.. && python3 -m venv venv
	@cd ../.. && source venv/bin/activate && pip install --upgrade pip
	@cd ../.. && source venv/bin/activate && pip install -r requirements.txt
	@cd ../.. && source venv/bin/activate && pip install -r dev/config/requirements-dev.txt
	@echo "Environment ready! Activate with: source venv/bin/activate"
