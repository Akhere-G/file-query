TEST_DATABASE_URL ?= postgresql://test@localhost:5433/filequery_test
PYTHON ?= backend/venv/bin/python

.PHONY: test-db-up test-db-down test-backend test-backend-unit test-rag-eval test-frontend test-e2e lint typecheck test

test-db-up:
	docker compose -f docker-compose.test.yml up -d --wait

test-db-down:
	docker compose -f docker-compose.test.yml down

test-backend:
	cd backend && TEST_DATABASE_URL=$(TEST_DATABASE_URL) venv/bin/python -m pytest -q

# No database needed
test-backend-unit:
	cd backend && venv/bin/python -m pytest -q -m unit

test-rag-eval:
	cd backend && TEST_DATABASE_URL=$(TEST_DATABASE_URL) venv/bin/python -m pytest -q -m rag_eval

test-frontend:
	cd frontend && npm test

test-e2e:
	cd frontend && npm run test:e2e

lint:
	cd backend && venv/bin/ruff check src tests
	cd frontend && npx eslint .

typecheck:
	cd frontend && npm run typecheck

test: test-db-up test-backend test-frontend test-e2e
