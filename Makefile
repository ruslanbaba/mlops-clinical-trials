# MLOps Clinical Trial Analytics Platform Makefile

.PHONY: setup install test lint format clean docker-build docker-push deploy-local deploy-prod

# Variables
PYTHON_VERSION := 3.9
PROJECT_NAME := mlops-clinical-trials
DOCKER_REGISTRY := your-registry.com
VERSION := $(shell git describe --tags --always --dirty)

# Setup development environment
setup:
	@echo "Setting up development environment..."
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install -r requirements-dev.txt
	. venv/bin/activate && pre-commit install

# Install dependencies
install:
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Run tests
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run linting
lint:
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/
	mypy src/

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Clean up generated files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/

# Build Docker images
docker-build:
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-training:$(VERSION) -f docker/Dockerfile.training .
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-serving:$(VERSION) -f docker/Dockerfile.serving .
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-api:$(VERSION) -f docker/Dockerfile.api .

# Push Docker images
docker-push:
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME)-training:$(VERSION)
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME)-serving:$(VERSION)
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME)-api:$(VERSION)

# Deploy to local Kubernetes
deploy-local:
	kubectl apply -f deployments/local/
	kubectl apply -f deployments/monitoring/

# Deploy to production
deploy-prod:
	kubectl apply -f deployments/production/
	kubectl apply -f deployments/istio/

# Run data pipeline
run-pipeline:
	python src/data/pipeline.py --config configs/data_pipeline.yaml

# Train model
train-model:
	python src/training/train_model.py --config configs/breast_cancer.yaml

# Validate model
validate-model:
	python src/validation/validate_model.py --model-path models/latest/

# Start local MLflow server
mlflow-server:
	mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --host 0.0.0.0 --port 5000

# Initialize database
init-db:
	python scripts/init_database.py

# Generate synthetic data for testing
generate-test-data:
	python scripts/generate_test_data.py --samples 10000 --output data/test/

# Run model performance monitoring
monitor:
	python src/monitoring/model_monitor.py

# Help
help:
	@echo "Available commands:"
	@echo "  setup           - Setup development environment"
	@echo "  install         - Install dependencies"
	@echo "  test            - Run tests"
	@echo "  lint            - Run linting"
	@echo "  format          - Format code"
	@echo "  clean           - Clean up generated files"
	@echo "  docker-build    - Build Docker images"
	@echo "  docker-push     - Push Docker images"
	@echo "  deploy-local    - Deploy to local Kubernetes"
	@echo "  deploy-prod     - Deploy to production"
	@echo "  train-model     - Train a model"
	@echo "  validate-model  - Validate a model"
	@echo "  mlflow-server   - Start MLflow server"
	@echo "  help            - Show this help message"
