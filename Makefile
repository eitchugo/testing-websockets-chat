CURRENT_DATE := $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
APP_VERSION := $(shell python3 -c "from src.testing_websockets_chat import __version__; print(__version__)")

.PHONY: help
help:  ## Show available commands
	@echo "Available commands:"
	@awk -F ':.*?## ' '/^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

.PHONY: clean-pyc
clean-pyc:  ## Removes python cache files
	find . -name \*.pyc -exec rm -f {} +
	find . -name \*.pyo -exec rm -f {} +
	find . -name \*~ -exec rm -f {} +
	find . -type d -name __pycache__ -exec rm -rf {} +

.PHONY: clean-build
clean-build:  ## Removes build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf package/
	find . -type d -name \*.egg-info -exec rm -rf {} +

.PHONY: clean  ## Alias to clean-pyc and clean-build
clean: clean-pyc clean-build  ## Alias to clean-pyc and clean-build

.PHONY: build
build: clean-build  ## Builds a python package on ./package/python
	pip3 install --target ./package/python .

.PHONY: install
install:  ## Installs package for the current user
	pip3 install --user .

.PHONY: install-dev
dev-install:  ## Installs package in development mode
	pip3 install -e .
