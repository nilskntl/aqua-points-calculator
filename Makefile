# =============================================================================
# aqua-points-calculator — World Aquatics point-score calculator for swimming.
#
# One self-contained Makefile covering the whole target surface (install / lint /
# format / typecheck / test / test-it / audit), so the same commands drive the
# project locally and in CI.
#
# Two formatters, split by what they own: ruff for the Python sources, Prettier
# for the structured formats around them (Markdown, YAML, JSON) — see the
# Prettier block below.
#
# The `api` extra is installed by `make install`: the HTTP surface is optional
# for a library consumer, but the test suite covers it, so the dev environment
# always has it.
# =============================================================================

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
PACKAGE := aqua_points_calculator
IMAGE := aqua-points-calculator
PORT ?= 8000
COMPOSE_DEV := -f docker-compose.yaml -f docker-compose.dev.yaml

# --- Prettier ---------------------------------------------------------------
# Ruff formats the Python sources; Prettier formats everything else that carries
# structure — Markdown, YAML, JSON.
#
# It is the one tool here that is not a Python package. Rather than drag a
# package.json, a lockfile and node_modules into a Python repo, npx fetches it at
# a PINNED version: local runs and CI then format identically, and npm caches the
# download after the first run. Bump the version in this one place.
PRETTIER := npx --yes prettier@3.9.6
PRETTIER_GLOBS := "**/*.{md,yaml,yml,json}"

.PHONY: help install dev serve build image up up-dev down restart logs ps sh \
        test test-it lint format format-check typecheck audit clean

help:           ## Show this help.
	@awk 'BEGIN {FS=":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ \
	  {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:        ## Install / refresh dependencies (uv sync, with the api extra).
	uv sync --extra api
dev:            ## Print the CLI help, listing every subcommand.
	uv run python -m $(PACKAGE) --help
serve:          ## Run the FastAPI service with auto-reload on $(PORT).
	uv run uvicorn aqua_points_calculator.api:app --host 0.0.0.0 --port $(PORT) --reload
build:          ## Build the sdist and the wheel into dist/ — what the release publishes.
	rm -rf dist
	uv build
image:          ## Build the runtime container image.
	docker build -t $(IMAGE):local .

# --- container stack -------------------------------------------------------
# `up` runs the production image; `up-dev` layers the reload overlay on top.
up:             ## Build and start the stack in the background.
	docker compose up -d --build
up-dev:         ## Start the stack with sources mounted and uvicorn --reload.
	docker compose $(COMPOSE_DEV) up -d --build
down:           ## Stop and remove the stack.
	docker compose $(COMPOSE_DEV) down --remove-orphans
restart:        ## Recreate the stack from a fresh build.
	$(MAKE) down && $(MAKE) up
logs:           ## Follow the service logs.
	docker compose logs -f aqua-points-calculator
ps:             ## Show the stack's containers and health.
	docker compose ps
sh:             ## Open a shell in the running container.
	docker compose exec aqua-points-calculator sh

test:           ## Unit tests only — fast, offline, no coverage gate.
	uv run pytest -m "not integration" --no-cov
test-it:        ## Full test gate: unit + integration tests and the coverage threshold.
	uv run pytest
lint:           ## Ruff check.
	uv run ruff check .
format:         ## Format in place: ruff (imports + Python), prettier (md/yaml/json).
	uv run ruff check --select I --fix .
	uv run ruff format .
	$(PRETTIER) --write --log-level warn $(PRETTIER_GLOBS)
format-check:   ## Verify both formatters without writing — the CI gate.
	uv run ruff check --select I .
	uv run ruff format --check .
	$(PRETTIER) --check --log-level warn $(PRETTIER_GLOBS)
typecheck:      ## mypy static type check.
	uv run mypy $(PACKAGE)
audit:          ## pip-audit.
	uv run pip-audit
clean:          ## Remove caches, build output and the virtualenv.
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist .venv
