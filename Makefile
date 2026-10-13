# One entry point for every task (spec 4.4, 9, 10.3). Works on Linux/macOS and Git Bash on Windows.
# Every target is a thin wrapper; the same commands can be typed directly (see README).
#
# DATA     private data directory (default ../audilitics-private/data; build/fixture-data with FIXTURE=1)
# EDITION  public (default) or private, for `make web`
# FIXTURE  1 = synthetic fixture of this repository, real = redacted 13 Oct 2026 fixture of the private repository

PYTHON ?= $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python,$(if $(wildcard .venv/bin/python),.venv/bin/python,python3))
ifeq ($(FIXTURE),1)
DATA ?= build/fixture-data
endif
DATA ?= ../audilitics-private/data
EDITION ?= public
GUARD_DIR ?= data
COLLECT = PYTHONPATH=collector $(PYTHON) -m collector --data-dir $(DATA)
FIXTURE_ARG = $(if $(filter 1,$(FIXTURE)),--fixture synthetic,$(if $(filter real,$(FIXTURE)),--fixture real))

.PHONY: setup setup-deps collect rebuild guard idcheck issues test lint test-py test-web palette e2e-data e2e web serve clean

setup:  ## Python venv + collector (dev extras) + npm ci
	python3 -m venv .venv 2>/dev/null || python -m venv .venv
	$(MAKE) PYTHON=$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python,.venv/bin/python) setup-deps

setup-deps:
	$(PYTHON) -m pip install -q --upgrade pip
	$(PYTHON) -m pip install -q -e "collector[dev]"
	cd web && npm ci

collect:  ## live run into DATA; FROM=<raw.json.gz> replays a file; FIXTURE=1|real; FORCE=1; DATE=YYYY-MM-DD
	$(COLLECT) collect $(if $(FROM),--from $(FROM)) $(FIXTURE_ARG) $(if $(FORCE),--force) $(if $(DATE),--date $(DATE))

rebuild:  ## replay every archived raw file of DATA in date order (after a rules or scoring change)
	$(COLLECT) rebuild

guard:  ## publication guard on a public tree: GUARD_DIR (default data/ of this repository)
	PYTHONPATH=collector $(PYTHON) -m collector guard $(GUARD_DIR)

idcheck:  ## identifier check on any tree (default: DATA)
	PYTHONPATH=collector $(PYTHON) -m collector idcheck $(DATA)

issues:  ## open or update GitHub issues for the last run (private repository job); DRY=1 prints the gh calls
	$(COLLECT) issues $(if $(DRY),--dry-run)

test: lint test-py test-web palette guard  ## all checks except e2e (spec 12.2); needs no private repository

lint:
	cd collector && ../$(PYTHON) -m ruff check . && ../$(PYTHON) -m mypy collector
	cd web && npx tsc --noEmit && npx eslint src e2e

test-py:
	cd collector && PYTHONPATH=. ../$(PYTHON) -m pytest -q

test-web:
	cd web && npx vitest run

palette:  ## dataviz validator on tokens.css, light and dark (spec 8.3)
	cd web && node tools/check_tokens.js

e2e-data:  ## synthetic dataset for Playwright (never published)
	rm -rf web/e2e/.data
	PYTHONPATH=collector $(PYTHON) -m collector --data-dir web/e2e/.data collect --fixture synthetic

e2e: e2e-data  ## Playwright smoke + screenshots of both builds against vite preview
	cd web && npx playwright test

web:  ## Vite dev server: EDITION=public reads data/ of this repository; EDITION=private reads DATA (local only)
	cd web && VITE_EDITION=$(EDITION) VITE_DATA_BASE=$(if $(filter private,$(EDITION)),$(abspath $(DATA)),../data) npx vite

serve:  ## production build of the public edition served locally at http://localhost:4173
	cd web && VITE_EDITION=public npx vite build && VITE_DATA_BASE=../data npx vite preview --port 4173

clean:
	rm -rf web/dist web/dist-e2e-* web/e2e/.data build .run
