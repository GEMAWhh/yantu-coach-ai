.PHONY: governance security api-install api-lint api-test web-install web-lint web-test lint test

governance:
	python scripts/validate_governance.py

security:
	python scripts/check_forbidden_patterns.py .

api-install:
	python -m pip install -e "apps/api[dev]"

api-lint:
	ruff format --check apps/api
	ruff check apps/api
	mypy apps/api/app apps/api/tests

api-test:
	pytest apps/api

web-install:
	cd apps/web && npm ci

web-lint:
	cd apps/web && npm run typecheck && npm run lint

web-test:
	cd apps/web && npm run test:unit && npm run build

lint: governance security api-lint web-lint

test: lint api-test web-test
