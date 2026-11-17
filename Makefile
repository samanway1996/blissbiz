.PHONY: setup db-up db-stop db-migrate dev-backend dev-frontend check test-mysql test-deployment maintenance-preview
setup:
	./scripts/setup.sh
db-up:
	docker compose up -d --wait db
db-stop:
	docker compose stop db
db-migrate:
	cd backend && .venv/bin/python3 -m alembic upgrade head
dev-backend:
	cd backend && WATCHFILES_FORCE_POLLING=true .venv/bin/python3 -m uvicorn app.main:app --reload --no-proxy-headers --host 127.0.0.1 --port 8000
dev-frontend:
	./scripts/npm.sh --prefix frontend run dev
check:
	cd backend && .venv/bin/python3 -m ruff check . ../scripts/test_deployment.py ../frontend/tests/support && .venv/bin/python3 -m ruff format --check . ../scripts/test_deployment.py ../frontend/tests/support && .venv/bin/python3 -m pytest
	./scripts/npm.sh --prefix frontend test
	./scripts/npm.sh --prefix frontend run build
test-mysql:
	cd backend && BLISSBIZ_TEST_MYSQL=1 .venv/bin/python3 -m pytest
test-deployment:
	./scripts/npm.sh --prefix frontend run build
	backend/.venv/bin/python3 scripts/test_deployment.py
maintenance-preview:
	cd backend && .venv/bin/python3 -m app.maintenance
